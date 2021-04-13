class ReleaseRequest:
  def __init__(self, org, project, buildnumber):
    self.org = org
    self.project = project
    self.buildnumber = buildnumber

  def is_sonarqube(self):
    return self.project == 'sonar-enterprise'
