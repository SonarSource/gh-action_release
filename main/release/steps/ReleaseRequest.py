class ReleaseRequest:
    def __init__(self, org, project, buildnumber, branch, sha):
        self.org = org
        self.project = project
        self.buildnumber = buildnumber
        self.branch = branch
        self.sha = sha
