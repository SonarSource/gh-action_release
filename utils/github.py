import os
import json
import requests

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')
attach_to_github_release = None
run_rules_cov = None


def get_release_info(repo: str, version):
  with open(github_event_path) as file:
    data = json.load(file)
    if data["release"].get('tag_name') == version:
      return data["release"]
    else:
      return None


def attach_asset_to_github_release(release_info, file_path, filename):
  files = {'upload_file': open(file_path, 'rb')}
  upload_url = release_info.get('upload_url').replace('{?name,label}', f"?name={filename}")
  print(upload_url)
  headers = {'Authorization': f"token {github_token}"}
  r = requests.post(upload_url, files=files, headers=headers)
  return r


def revoke_release(repo, version):
  release_info = get_release_info(repo, version)
  if not release_info or not release_info.get('id'):
    return None
  url = f"{githup_api_url}/repos/{repo}/releases/{release_info.get('id')}"
  headers = {'Authorization': f"token {github_token}"}
  payload = {'draft': True, 'tag_name': version}
  r = requests.patch(url, json=payload, headers=headers)
  # delete tag
  url = f"{githup_api_url}/repos/{repo}/git/refs/tags/{version}"
  requests.delete(url, headers=headers)
  return r.json()


def current_branch():
  with open(github_event_path) as file:
    data = json.load(file)
    if 'release' not in data:
      print(f"::error Could not get release object of github event")
      return None
    if 'target_commitish' not in data['release']:
      print(f"::error Could not get the branch name of github event")
      return None
    return data['release']['target_commitish']