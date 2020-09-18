import json
import urllib
import requests
import tempfile

from utils.buildinfo import BuildInfo

class Artifactory:

  url = 'https://repox.jfrog.io/repox'
  api_key = None
  headers = {'content-type': 'application/json'}
  default_bintray_target_repo = "SonarQube-bintray"
  bintray_target_repo = default_bintray_target_repo

  def __init__(self, api_key: str, custom_bintray_target_repo = None):
    self.api_key = api_key
    self.headers['X-JFrog-Art-Api'] = api_key
    if custom_bintray_target_repo is not None:
      self.bintray_target_repo = custom_bintray_target_repo

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

  def distribute_to_bintray(self, release_request, buildinfo):
    print(f"Distributing {release_request.project}#{release_request.buildnumber} to bintray")

    source_repo = "sonarsource-public-releases"
    if self.bintray_target_repo != self.default_bintray_target_repo:
      source_repo = buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace("qa", "releases")

    payload = {
      "targetRepo": self.bintray_target_repo,
      "sourceRepos": [source_repo],
      "async": "true"
    }
    print(f"payload: {payload}")
    url = f"{self.url}/api/build/distribute/{release_request.project}/{release_request.buildnumber}"
    try:
      r = requests.post(url, json=payload, headers=self.headers)
      r.raise_for_status()
      if r.status_code == 200:
        print(f"{release_request.project}#{release_request.buildnumber} pushed to bintray ({self.bintray_target_repo}) ready to sync to central")
    except requests.exceptions.HTTPError as err:
      print(f"Failed to distribute {release_request.project}#{release_request.buildnumber} {err}")

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
      params = {
        'buildName': release_request.project,
        'buildNumber': release_request.buildnumber,
        'status': status
      }
      moreparams=None
      if revoke:
        moreparams = {
          'src1': 'sonarsource-private-releases',
          'target1': 'sonarsource-private-builds',
          'src2': 'sonarsource-public-releases',
          'target2': 'sonarsource-public-builds',
        }
      else:
        moreparams = {
          'src1': 'sonarsource-private-builds',
          'target1': 'sonarsource-private-releases',
          'src2': 'sonarsource-public-builds',
          'target2': 'sonarsource-public-releases',
        }
      params.update(moreparams)

      print(f"Promoting multi repositories: {moreparams}")
      
      url = f"{self.url}/api/plugins/execute/multiRepoPromote?params=" + ";".join(
        "{!s}={!s}".format(key, val) for (key, val) in params.items())
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
    temp_file = f"{tempfile.gettempdir()}/{filename}"
    urllib.request.urlretrieve(url, temp_file)
    print(f'downloaded {temp_file}')
    for checksum in (checksums or []):
      urllib.request.urlretrieve(f"{url}.{checksum}", f"{temp_file}.{checksum}")
      print(f'downloaded {temp_file}.{checksum}')
    return temp_file
