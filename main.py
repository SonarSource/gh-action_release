import sys
import os
import requests

githup_api_url="https://api.github.com"
github_token=os.environ.get('GITHUB_TOKEN','no github token in env')
attach=os.environ.get('INPUT_ATTACH_ARTIFACTS_TO_GITHUB_RELEASE')
distribute = os.environ.get('INPUT_DISTRIBUTE')
run_rules_cov = os.environ.get('INPUT_RUN_RULES_COV')

def set_releasability_output(output):
  print(f"::set-output name=releasability::{output}")

def set_release_output(function, output):
  print(f"::set-output name={function}::{output}")

def get_release_info(repo, version):
  url=f"{githup_api_url}/repos/{repo}/releases"  
  headers={'Authorization': f"token {github_token}"}
  r=requests.get(url, headers=headers)
  releases=r.json()
  for release in releases:
      if not isinstance(release, str) and release.get('tag_name') == version:
          return release
  print(f"::error No release info found for tag '{version}'.\nReleases: {releases}")
  return None

def revoke_release(repo, version):
  release_info=get_release_info(repo,version)
  if not release_info or not release_info.get('id'):
      return None
  url=f"{githup_api_url}/repos/{repo}/releases/{release_info.get('id')}"  
  headers = {'Authorization': f"token {github_token}"}
  payload = {'draft': True, 'tag_name': version}
  r=requests.patch(url, json=payload, headers=headers)
  #delete tag
  url=f"{githup_api_url}/repos/{repo}/git/refs/tags/{version}"
  requests.delete(url, headers=headers)
  return r.json()
  
def do_release(repo, build_number, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    url=f"{function_url}/{repo}/{build_number}"    
    separator='?'
    if attach == "true":
      url=url+f"{separator}attach=true"
      separator='%'
    if run_rules_cov == 'true':
      url=url+f"{separator}run_rules_cov=true"
    return requests.get(url, headers=headers)

def do_distribute(repo, build_number, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/distribute_release"
    url=f"{function_url}/{repo}/{build_number}"
    return requests.get(url, headers=headers)

def check_releasability(repo, version, headers):
    function_url="https://us-central1-language-team.cloudfunctions.net/releasability_check"
    url=f"{function_url}/{repo}/{version}"    
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

def abort_release(repo, version):
    print(f"::error  Aborting release")
    revoke_release(repo, version)
    sys.exit(1)

def validate_gcf_call(response, repo, version, function):
    if response.status_code == 200:
        set_release_output(function, f"{repo}:{version} {function} DONE")
    else:
        print(
            f"::error Unexpected exception occurred while calling {function} cloud function. Status '{response.status_code}': '{response.text}'")
        abort_release(repo, version)

def main():
    repo=os.environ["GITHUB_REPOSITORY"]
    tag=os.environ["GITHUB_REF"]
    version=tag.replace('refs/tags/', '', 1)
    #tag shall be like X.X.X.BUILD_NUMBER
    build_number=version.split(".")[-1]
    headers={'Authorization': f"token {github_token}"}
    release_info=get_release_info(repo,version)

    if not release_info:
        print(f"::error  No release info found")
        return

    r=check_releasability(repo, version, headers)
    if releasability_passed(r):
        r=do_release(repo, build_number, headers)
        validate_gcf_call(r, repo, version, "release ...")
        if distribute == 'true':
            r=do_distribute(repo, build_number, headers)
            validate_gcf_call(r, repo, version, "distribute_release")        
    else:
        print(f"::error  RELEASABILITY did not complete correctly. Status '{r.status_code}': '{r.text}'")
        abort_release(repo, version)

if __name__ == "__main__":
    main()

