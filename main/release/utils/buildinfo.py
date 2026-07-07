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
