class ReleaseRequest:
    def __init__(self, org, project, version, buildnumber, branch, sha, artifactory_build_name=None):
        self.org = org
        self.project = project
        self.version = version
        self.buildnumber = buildnumber
        self.branch = branch
        self.sha = sha
        # Override for Artifactory build-info lookup; defaults to the GitHub repository name.
        self.artifactory_build_name = artifactory_build_name if artifactory_build_name else project
