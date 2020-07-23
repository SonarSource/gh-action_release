import os
import sys

from steps.distribute import distribute_release
from steps.release import release, revoke_release
from steps.relesability import releasability_checks
from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.bintray import Bintray
from utils.github import GitHub

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')
github_attach = os.environ.get('INPUT_ATTACH_ARTIFACTS_TO_GITHUB_RELEASE')

distribute = os.environ.get('INPUT_DISTRIBUTE')
run_rules_cov = os.environ.get('INPUT_RUN_RULES_COV')

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')

bintray_api_url='https://api.bintray.com'
bintray_user=os.environ.get('BINTRAY_USER','no bintray api user in env')  
bintray_apikey=os.environ.get('BINTRAY_TOKEN','no bintray api key in env')  
central_user=os.environ.get('CENTRAL_USER','no central user in env')  
central_password=os.environ.get('CENTRAL_PASSWORD','no central password in env')  

binaries_host = 'binaries.sonarsource.com'
binaries_ssh_user=os.environ.get('RELEASE_SSH_USER','no ssh user in env')
binaries_ssh_key=os.environ.get('RELEASE_SSH_KEY','no ssh key in env')

def set_releasability_output(output):
  print(f"::set-output name=releasability::{output}")


def set_release_output(function, output):
  print(f"::set-output name={function}::{output}")

def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest ):
  print(f"::error  Aborting release")
  #github.revoke_release()
  revoke_release(artifactory,binaries, rr)
  set_release_output("release", f"{rr.project}:{rr.build_number} revoked")
  sys.exit(1)

  artifactory = Artifactory(artifactory_apikey)
  bintray = Bintray(bintray_api_url,bintray_user,bintray_apikey,central_user,central_password)
  binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key)
  rr = ReleaseRequest(organisation, project, build_number)

  try:
    release(artifactory, binaries, rr, github_attach, run_rules_cov)
    set_release_output("release", f"{repo}:{version} release DONE")
    if distribute == 'true':
      distribute_release(artifactory, bintray, rr, version)
      set_release_output("distribute_release", f"{repo}:{version} distribute_release DONE")
  except Exception as e:
    print(f"::error release did not complete correctly." + str(e))
    abort_release(github)
    sys.exit(1)

def main():
  repo = os.environ["GITHUB_REPOSITORY"]
  organisation, project = repo.split("/")
  tag = os.environ["GITHUB_REF"]
  version = tag.replace('refs/tags/', '', 1)
  # tag shall be like X.X.X.BUILD_NUMBER
  build_number = version.split(".")[-1]

  github = GitHub(githup_api_url, github_token, github_event_path)

  release_info = github.release_info(version)
  if not release_info:
    print(f"::error  No release info found")
    return

  try:
    releasability_checks(project, version, github.current_branch())
  except Exception as e:
    print(f"::error relesability did not complete correctly. " + str(e))
    sys.exit(1)

  artifactory = Artifactory(artifactory_apikey)
  bintray = Bintray(bintray_api_url,bintray_user,bintray_apikey,central_user,central_password)
  binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key)
  rr = ReleaseRequest(organisation, project, build_number)

  try:
    release(artifactory, binaries, rr, github_attach, run_rules_cov)
    set_release_output("release", f"{repo}:{version} release DONE")
    if distribute == 'true':
      distribute_release(artifactory, bintray, rr, version)
      set_release_output("distribute_release", f"{repo}:{version} distribute_release DONE")
  except Exception as e:
    print(f"::error release did not complete correctly." + str(e))
    abort_release(github, artifactory, binaries, rr)
    sys.exit(1)

if __name__ == "__main__":
  main()
