import json
import urllib
import requests


class Artifactory:

  url = 'https://repox.jfrog.io/repox'
  api_key = None
  headers = {'content-type': 'application/json'}
  bintray_target_repo = "SonarQube-bintray"

  def __init__(self, api_key: str):
    self.api_key = api_key
    self.headers['X-JFrog-Art-Api'] = api_key

  def receive_build_info(self, release_request):
    url = f"{self.url}/api/build/{release_request.project}/{release_request.buildnumber}"
    r = requests.get(url, headers=self.headers)
    buildinfo = r.json()
    if r.status_code == 200:
      return BuildInfo(buildinfo)
    else:
      print(r.status_code)
      print(r.content)
      raise Exception('unknown build')

  def distribute_build(self, project, buildnumber):
    print(f"Distributing {project}#{buildnumber} to bintray")
    payload = {
      "targetRepo": self.bintray_target_repo,
      "sourceRepos": ["sonarsource-public-releases"],
      "async": "true"  # maybe?
    }
    url = f"{self.url}/api/build/distribute/{project}/{buildnumber}"
    try:
      r = requests.post(url, json=payload, headers=self.headers)
      r.raise_for_status()
      if r.status_code == 200:
        print(f"{project}#{buildnumber} pushed to bintray ready to sync to central")
    except requests.exceptions.HTTPError as err:
      print(f"Failed to distribute {project}#{buildnumber} {err}")

  def promote(self, release_request, buildinfo, revoke=False):
    status = 'released'

    repo = buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
    if revoke:
      sourcerepo = repo.replace('qa', 'releases')
      targetrepo = repo.replace('qa', 'builds')
      status="it-passed"
    else:
      sourcerepo = repo.replace('qa', 'builds')
      targetrepo = repo.replace('qa', 'releases')

    print(f"Promoting build {release_request.project}#{release_request.buildnumber} from {sourcerepo} to {targetrepo}")

    if buildinfo.is_multi():
      print(f"Promoting multi repositories")
      params = {
        'buildName': release_request.project,
        'buildNumber': release_request.buildnumber,
        'status': status
      }
      moreparams=None
      if revoke:
        moreparams = {
          'src1': 'sonarsource-private-builds',
          'target1': 'sonarsource-private-releases',
          'src2': 'sonarsource-public-builds',
          'target2': 'sonarsource-public-releases',
        }
      else:
        moreparams = {
          'src1': 'sonarsource-private-releases',
          'target1': 'sonarsource-private-builds',
          'src2': 'sonarsource-public-releases',
          'target2': 'sonarsource-public-builds',
        }
      params.update(moreparams)
      
      url = f"{self.url}/api/plugins/execute/multiRepoPromote?params=" + ";".join(
        "{!s}={!r}".format(key, val) for (key, val) in params.items())
      r = requests.get(url, headers=self.headers)
    else:
      url = f"{self.url}/api/build/promote/{release_request.project}/{release_request.buildnumber}"
      json_payload = {
        "status": f"{status}",
        "sourceRepo": f"{sourcerepo}",
        "targetRepo": f"{targetrepo}"
      }
      r = requests.post(url, data=json.dumps(json_payload), headers=self.headers)
    if not r.ok:
      raise Exception(f"Promotion failed with code: {r.status_code}. Response was: {r.text}")

  def download(self, artifactory_repo, gid, aid, qual, ext, version, checksums = None):
    gid_path = gid.replace(".", "/")
    if gid.startswith('com.'):
      artifactory_repo = artifactory_repo.replace('public', 'private')
    artifactory = self.url + "/" + artifactory_repo

    filename = f"{aid}-{version}.{ext}"
    if qual:
      filename = f"{aid}-{version}-{qual}.{ext}"
    url = f"{artifactory}/{gid_path}/{aid}/{version}/{filename}"
    print(url)
    opener = urllib.request.build_opener()
    opener.addheaders = [('X-JFrog-Art-Api', self.api_key)]
    urllib.request.install_opener(opener)
    # for sonarqube rename artifact from sonar-application.zip to sonarqube.zip
    if aid == "sonar-application":
      filename = f"sonarqube-{version}.zip"
      aid = "sonarqube"
    tempfile = f"/tmp/{filename}"
    urllib.request.urlretrieve(url, tempfile)
    for checksum in (checksums or []):
      urllib.request.urlretrieve(f"{url}.{checksum}", f"{tempfile}.{checksum}")
    print(f'downloaded {tempfile}')
    return tempfile


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
