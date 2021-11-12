import json
import requests

class GitHub:

  github_api_url: str
  github_token: str
  github_event: {}

  def __init__(self, github_api_url, github_token, github_event_path):
    with open(github_event_path) as file:
      self.github_event = json.load(file)
    self.github_token = github_token
    self.github_api_url = github_api_url


  def release_info(self, version = None) -> {}:
      if version is None:
        return self.github_event["release"]
      elif self.github_event["release"].get('tag_name') == version:
        return self.github_event["release"]
      else:
        return None

  def repository_full_name(self) -> str:
    return self.github_event["repository"]["full_name"]

  def repository_info(self):
    return self.github_event["repository"]

  def current_branch(self):
    return self.release_info()['target_commitish']

  def attach_asset_to_release(self, file_path, filename):
    files = {'upload_file': open(file_path, 'rb')}
    upload_url = self.release_info().get('upload_url').replace('{?name,label}', f"?name={filename}")
    print(upload_url)
    headers = {'Authorization': f"token {self.github_token}"}
    r = requests.post(upload_url, files=files, headers=headers)
    return r

  def revoke_release(self):
    if not self.release_info().get('id'):
      return None
    version = self.release_info()["tag_name"]
    url = self.repository_info().get("releases_url").replace("{/id}", self.release_info().get('id'))
    headers = {'Authorization': f"token {self.github_token}"}
    payload = {'draft': True, 'tag_name': version}
    r = requests.patch(url, json=payload, headers=headers)
    # delete tag
    url = f"{self.github_api_url}/repos/{self.repository_full_name()}/git/refs/tags/{version}"
    requests.delete(url, headers=headers)
    return r.json()
