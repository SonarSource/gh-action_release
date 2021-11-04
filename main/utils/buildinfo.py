class BuildInfo:
    json = None

    def __init__(self, json):
        self.json = json

    def get_property(self, property, default=""):
        try:
            return self.json['buildInfo']['properties'][property]
        except BaseException:
            return default

    def get_module_property(self, property):
        return self.json['buildInfo']['modules'][0]['properties'][property]

    def get_version(self):
        return self.json['buildInfo']['modules'][0]['id'].split(":")[-1]

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

    def is_multi(self):
        allartifacts = self.get_artifacts_to_publish()
        if allartifacts:
            artifacts = allartifacts.split(",")
            artifacts_count = len(artifacts)
            if artifacts_count == 1:
                return False
            ref = artifacts[0][0:3]
            for i in range(0, artifacts_count):
                current = artifacts[i - 1][0:3]
                if current != ref:
                    return True
        return False

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
