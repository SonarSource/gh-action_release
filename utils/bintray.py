import os
import requests
from flask import make_response
import urllib.parse

class Bintray:
  bintray_api_url=None
  bintray_user=None
  bintray_apikey=None
  central_user=None
  central_password=None
  headers = {'content-type': 'application/json'}

  def __init__(self, bintray_api_url, bintray_user, bintray_apikey, central_user, central_password):
    self.bintray_api_url = bintray_api_url
    self.bintray_user = bintray_user
    self.bintray_apikey = bintray_apikey
    self.central_user = central_user
    self.central_password = central_password 
    

  def sync_to_central(self, project, package, version):
    print(f"Syncing {project}#{version} to central")
    payload = {
      "username": self.central_user,
      "password": self.central_password,
      "close": "1"  
    }
    url=f"{self.bintray_api_url}/maven_central_sync/sonarsource/SonarQube/{package}/versions/{version}"
    try:
      r = requests.post(url, json=payload, headers=self.headers, auth=requests.auth.HTTPBasicAuth(self.bintray_user, self.bintray_apikey))  
      result=r.json()
      print(f"status:{result['status']} messages:{result['messages']}")
      r.raise_for_status()
      if r.status_code == 200:
        print(f"{project}#{version} synced to central")
    except requests.exceptions.HTTPError as err:
      print(f"Failed to sync {project}#{version} {err}")