import os
import polling
import requests
from flask import make_response
import urllib.parse
from utils.slack import alert_slack

class Bintray:
  bintray_api_url=None
  bintray_user=None
  bintray_apikey=None
  central_user=None
  central_password=None  
  headers = {'content-type': 'application/json'}
  maven_central_sync_timeout=60*15

  def __init__(self, bintray_api_url, bintray_user, bintray_apikey, central_user, central_password):
    self.bintray_api_url = bintray_api_url
    self.bintray_user = bintray_user
    self.bintray_apikey = bintray_apikey
    self.central_user = central_user
    self.central_password = central_password 

  def await_package_ready(self, package, version):
    try:
      polling.poll(
        lambda: self.package_latest_version(package) == version,
        step=60,
        timeout=60*30
      )
    except polling.TimeoutException as te:
      alert_slack(f"{package} {version} was not published to BinTray within 30 mins: {str(te)}", "#build")
      raise te

  def package_latest_version(self, package) -> str:
    url = f"{self.bintray_api_url}/packages/sonarsource/SonarQube/{package}"
    r = requests.get(url, headers=self.headers,
                      auth=requests.auth.HTTPBasicAuth(self.bintray_user, self.bintray_apikey))
    print(f"Polling package version for {package}")
    return r.json()["latest_version"]

  def sync_to_central(self, project, package, version):
    print(f"Syncing {project}#{version} to central")
    payload = {
      "username": self.central_user,
      "password": self.central_password,
      "close": "1"  
    }
    url=f"{self.bintray_api_url}/maven_central_sync/sonarsource/SonarQube/{package}/versions/{version}"
    try:
      r = requests.post(url,
                        json=payload,
                        headers=self.headers,
                        uth=requests.auth.HTTPBasicAuth(self.bintray_user, self.bintray_apikey),
                        timeout=self.maven_central_sync_timeout)
      result=r.json()
      print(f"status:{result['status']} messages:{result['messages']}")
      r.raise_for_status()
      if r.status_code == 200:
        print(f"{project}#{version} synced to central")
    except requests.exceptions.Timeout as err:
      alert_slack(f"Sync of {project}#{version} did not finished in {self.maven_central_sync_timeout} seconds: ","#build")
    except requests.exceptions.HTTPError as err:
      alert_slack(f"Failed to sync {project}#{version} {err}","#build")

  