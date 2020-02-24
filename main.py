import sys
import os
import requests

githup_api_url="https://api.github.com"

def set_releasability_output(output):
  print(f"::set-output name=releasability::{output}")

def set_release_output(output):
  print(f"::set-output name=release::{output}")

def get_release_info(repo,tag):
  tag=tag.replace('refs/tags/', '', 1)
  url=f"{githup_api_url}/repos/{repo}/releases"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers={'Authorization': f"token {GITHUB_TOKEN}"}
  r=requests.get(url, headers=headers)
  releases=r.json()
  for release in releases:
      if not isinstance(release, str) and release.get('tag_name') == tag:
          return release
  print(f"::error No release info found for tag '{tag}'.\nReleases: {releases}")
  return None

def revoke_release(repo):
  tag=os.environ["GITHUB_REF"]
  release_info=get_release_info(repo,tag)
  if not release_info or not release_info.get('id'):
      return None
  url=f"{githup_api_url}/repos/{repo}/releases/{release_info.get('id')}"
  GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
  headers = {'Authorization': f"token {GITHUB_TOKEN}"}
  payload = {'draft': True, 'tag_name': tag}
  r=requests.patch(url, json=payload, headers=headers)
  return r.json()
  
def do_release(repo, build_number, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    url=f"{function_url}/{repo}/{build_number}"
    return requests.get(url, headers=headers)

def check_releasability(repo, build_number, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/releasability_check"
    url=f"{function_url}/{repo}/{build_number}"
    print(f"::debug '{url}'")
    return requests.get(url, headers=headers)

def print_releasability_details(data):
    message = f"RELEASABILITY: {data.get('state')}\n"
    checks=data.get('checks', [])
    for check in checks:
        msg=check.get('message', '')
        if msg:
            msg=f": {msg}"
        message+=f"{check.get('name')} - {check.get('state')}{msg}\n"
    set_releasability_output(message)

def releasability_passed(response):
    if response.status_code == 200:
        data=response.json()
        print_releasability_details(data)
        return data.get('state') == 'PASSED'
    return False

def abort_release(repo):
    print(f"::error  Aborting release")
    revoke_release(repo)
    sys.exit(1)

def main():    
    repo=os.environ["GITHUB_REPOSITORY"]
    github_token=os.environ["GITHUB_TOKEN"]
    tag=os.environ["GITHUB_REF"]
    #tag shall be like X.X.X.BUILD_NUMBER
    build_number=tag.path.split(".")[-1]
    headers={'Authorization': f"token {github_token}"}
    release_info=get_release_info(repo,tag)

    if not release_info:
        print(f"::error  No release info found")
        return

    branch=release_info.get('target_commitish')
    r=check_releasability(repo, build_number, headers)
    if releasability_passed(r):
        r=do_release(repo, build_number, headers)
        if r.status_code == 200:
            set_release_output(f"{repo}:{sha1} RELEASED")
        else:
            print(f"::error Unexpected exception occurred while calling release cloud function")
            abort_release(repo)
    else:
        print(f"::error  RELEASABILITY did not complete correctly")
        abort_release(repo)
    

if __name__ == "__main__":
    main()

  