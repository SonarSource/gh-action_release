class BuildInfo:
    json = None

    def __init__(self, json):
        self.json = json

    def get_property(self, property_name, default=""):
        try:
            return self.json['buildInfo']['properties'][property_name]
        except BaseException:
            return default

    def get_module_property(self, property_name):
        return self.json['buildInfo']['modules'][0]['properties'][property_name]

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
        artifacts = None
        try:
            artifacts = self.get_module_property('artifactsToPublish')
        except:
            try:
                artifacts = self.get_property('buildInfo.env.ARTIFACTS_TO_PUBLISH')
            except:
                print("no artifacts to publish")
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
