class BuildInfo:
    json = None

    def __init__(self, json):
        self.json = json

    def get_property(self, property_name, default=None):
        try:
            return self.json['buildInfo']['properties'][property_name]
        except KeyError:
            return default

    def get_module_property(self, property_name, default=None):
        try:
            return self.json['buildInfo']['modules'][0]['properties'][property_name]
        except KeyError:
            return default

    def get_version(self):
        return self.json['buildInfo']['modules'][0]['id'].split(":")[-1]

    def get_source_and_target_repos(self, revoke):
        repo = self.json['buildInfo']['statuses'][0]['repository']
        repo_type = repo.split('-')[-1]
        if revoke:
            sourcerepo = repo.replace(repo_type, 'releases')
            targetrepo = repo.replace(repo_type, 'builds')
        else:
            sourcerepo = repo.replace(repo_type, 'builds')
            targetrepo = repo.replace(repo_type, 'releases')
        return sourcerepo, targetrepo

    def get_artifacts_to_publish(self):
        modules = self.json.get('buildInfo', {}).get('modules', [])
        combined = ','.join(m.get('properties', {}).get('artifactsToPublish', '') for m in modules)
        all_artifacts = list(dict.fromkeys(a for a in combined.split(',') if a))
        if all_artifacts:
            return ','.join(all_artifacts)
        artifacts = self.get_property('buildInfo.env.ARTIFACTS_TO_PUBLISH')
        if not artifacts:
            print("No artifacts to publish")
        return artifacts

    def get_public_module_artifacts(self):
        """Every module of this build, as 'groupId:artifactId:ext[:qualifier]' strings, deduplicated.

        Reads each module's own declared artifacts (falling back to a plain 'jar' guess when that
        list is absent) so a module whose main artifact isn't a jar, or that attaches extra
        classified files, is still represented correctly. A module's sources/javadoc companions
        are only dropped here when it also has a genuine jar-typed entry, which is the only case
        the Central download loop re-fetches them on its own; otherwise (e.g. a zip-packaged
        module that still attaches sources/javadoc jars) they're kept as explicit entries.

        Deliberately independent of artifactsToPublish, which governs a different, narrower
        selection (what reaches binaries.sonarsource.com) and is often scoped to just the
        customer-facing plugin jar even for a build that produces other public modules (e.g. a
        language frontend or checks jar).
        """
        modules = self.json.get('buildInfo', {}).get('modules', [])
        gavs = []
        for module in modules:
            parts = module.get('id', '').split(':')
            if len(parts) < 2:
                continue
            gavs.extend(self._module_gavs(parts[0], parts[1], parts[-1], module.get('artifacts')))
        return list(dict.fromkeys(gavs))

    @staticmethod
    def _module_gavs(gid, aid, version, artifacts):
        """One module's own artifacts as 'groupId:artifactId:ext[:qualifier]' strings; falls back
        to a plain jar guess when the module declares none of its own.

        Extension and qualifier are parsed from each artifact's filename, not its buildInfo
        'type' - JFrog's extractors write a mangled string there for jar artifacts (e.g.
        'test-jar', 'javadoc-jar'), not a plain extension.
        """
        prefix = f"{aid}-{version}"
        artifacts = artifacts or [{'name': f"{prefix}.jar"}]
        parsed = [p for p in (BuildInfo._parse_artifact_name(prefix, a.get('name', '')) for a in artifacts) if p]
        has_plain_jar = any(ext == 'jar' and qualifier not in ('sources', 'javadoc') for ext, qualifier in parsed)
        gavs = []
        for ext, qualifier in parsed:
            if ext == 'pom' or (has_plain_jar and qualifier in ('sources', 'javadoc')):
                continue
            gavs.append(f"{gid}:{aid}:{ext}:{qualifier}" if qualifier else f"{gid}:{aid}:{ext}")
        if not gavs and any(ext == 'pom' for ext, _ in parsed):
            # A pom-packaged module (e.g. a BOM) with no jar/zip/... sibling: the loop above
            # skips its only artifact as a would-be companion, so emit it directly or it's
            # dropped from the bundle unless some other module happens to <parent> it.
            gavs.append(f"{gid}:{aid}:pom")
        return gavs

    @staticmethod
    def _parse_artifact_name(prefix, name):
        """Split a '<prefix>[-qualifier].ext' filename into (ext, qualifier), or None if name
        doesn't start with prefix or has no extension.
        """
        rest = name[len(prefix):] if name.startswith(prefix) else ''
        if '.' not in rest:
            return None
        if rest.startswith('-'):
            qualifier, _, ext = rest[1:].rpartition('.')
            return ext, qualifier
        return rest[1:], ''

    def is_public(self):
        artifacts = self.get_artifacts_to_publish()
        if artifacts:
            return "org.sonarsource" in artifacts
        else:
            return False

    def get_package(self):
        allartifacts = self.get_artifacts_to_publish()
        artifacts = allartifacts.split(",")
        artifacts_count = len(artifacts)
        if artifacts_count > 0:
            artifact = artifacts[0].split(":")
            return artifact[0]
        return None
