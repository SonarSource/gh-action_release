class ReleaseRequest:
    def __init__(self, org, project, version, buildnumber, branch, sha):
        self.org = org
        self.project = project
        self.version = version
        self.buildnumber = buildnumber
        self.branch = branch
        self.sha = sha
