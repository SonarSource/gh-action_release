import sys
import os
import requests
import json

githup_api_url="https://api.github.com"

def show_output(output):
  print(f"::set-output name=myOutput::{output}")

def get_release_info(repo):
  tag=os.environ["GITHUB_REF"]
  url=f"{githup_api_url}/repos/{repo}/releases/tags/{tag}"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers = {'Authorization': f"token {GITHUB_TOKEN}"}
  r = requests.get(url, headers=headers)  
  return r.json()

def revoke_release(repo):
  release_info=get_release_info(repo)
  release_id=release_info['id']
  url=f"{githup_api_url}/repos/{repo}/releases/{release_id}"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers = {'Authorization': f"token {GITHUB_TOKEN}"}
  payload = {'draft': True}
  r=requests.patch(url, json=payload, headers=headers)
  return r.json()
  
def main():
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    sha1=os.environ["GITHUB_SHA"]
    repo=os.environ["GITHUB_REPOSITORY"]
    url = f"{function_url}/{repo}/{sha1}/"
    GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
    headers = {'Authorization': f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:      
      show_output(url)
    else:
      revoke_release(repo)

    

if __name__ == "__main__":
    main()

  