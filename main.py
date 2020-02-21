import sys
import os
import requests

githup_api_url="https://api.github.com"

def show_output(output):
  print(f"::set-output name=myOutput::{output}")

def get_release_id(repo,tag):
  url=f"{githup_api_url}/repos/{repo}/releases"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers={'Authorization': f"token {GITHUB_TOKEN}"}
  r=requests.get(url, headers=headers)
  releases=r.json()
  if len(releases) == 0:
      show_output(f"No release found for repo: '{repo}'")
      return None

  for release in releases:
      show_output(f"release: '{release}'")
      if release.get('tag_name') == tag:
              return release.get('id')
  show_output(f"No release info found for tag '{tag}'")
  return None

def revoke_release(repo):
  tag=os.environ["GITHUB_REF"]
  release_id=get_release_id(repo,tag)
  if not release_id:
      return None
  url=f"{githup_api_url}/repos/{repo}/releases/{release_id}"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers = {'Authorization': f"token {GITHUB_TOKEN}"}
  payload = {'draft': True, 'tag_name': tag}
  r=requests.patch(url, json=payload, headers=headers)
  return r.json()
  
def do_release(repo, sha1, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    url=f"{function_url}/{repo}/{sha1}/"
    return requests.get(url, headers=headers)

def check_releasability(repo, sha1, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/releasability_check"
    url=f"{function_url}/{repo}/{sha1}/"
    return requests.get(url, headers=headers)

def print_releasability_details(data):
    show_output(f"RELEASABILITY: {data.get('state')}")
    checks=data.get('checks', [])
    for check in checks:
        msg=check.get('message', '')
        if msg:
            msg=f": {msg}"
        show_output(f"{check.get('name')} - {check.get('state')}{msg}")

def releasability_passed(response):
    if response.status_code == 200:
        data=response.json()
        print_releasability_details(data)
        return data.get('state') == 'PASSED'
    return False

def abort_release(repo):
    show_output("Aborting release")
    revoke_release(repo)
    sys.exit(1)

def main():
    sha1=os.environ["GITHUB_SHA"]
    repo=os.environ["GITHUB_REPOSITORY"]
    github_token=os.environ["GITHUB_TOKEN"]
    headers={'Authorization': f"token {github_token}"}

    r=check_releasability(repo, sha1, headers)
    if releasability_passed(r):
        r=do_release(repo, sha1, headers)
        if r.status_code == 200:
            show_output(f"{repo}:{sha1} RELEASED")
        else:
            show_output("Unexpected exception occurred while calling release cloud function")
            abort_release(repo)
    else:
        abort_release(repo)
    

if __name__ == "__main__":
    main()

  