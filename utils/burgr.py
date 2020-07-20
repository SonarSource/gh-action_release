import os
from datetime import datetime, timezone

import requests
from requests.auth import HTTPBasicAuth

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')


# This will only work for a branch build, not a PR build
# because a PR build notification needs `"pr_number": NUMBER` instead of `'branch': NAME`
def notify_burgr(release_request, buildinfo, status):
  branch = buildinfo.get_property('buildInfo.env.GITHUB_BRANCH', "master")
  sha1 = buildinfo.get_property('buildInfo.env.GIT_SHA1')
  payload = {
    'repository': f"{release_request.org}/{release_request.project}",
    'pipeline': release_request.buildnumber,
    'name': 'RELEASE',
    'system': 'github',
    'type': 'release',
    'number': release_request.buildnumber,
    'branch': branch,
    'sha1': sha1,
    'url': f"https://github.com/{release_request.org}/{release_request.project}/releases",
    'status': status,
    'metadata': '',
    'started_at': datetime.now(timezone.utc).astimezone().isoformat(),
    'finished_at': datetime.now(timezone.utc).astimezone().isoformat()
  }
  print(f"burgr payload:{payload}")
  url = f"{burgrx_url}/api/stage"
  r = requests.post(url, json=payload, auth=HTTPBasicAuth(burgrx_user, burgrx_password))
  if r.status_code != 201:
    print(f"burgr notification failed code:{r.status_code}")
