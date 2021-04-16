import re
import sys

from steps.release import revoke_release, publish_all_artifacts_to_binaries
from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.burgr import Burgr
from utils.cirrus import rules_cov
from utils.github import GitHub
from slack.errors import SlackApiError
from vars import githup_api_url, github_token, github_event_path, github_attach, burgrx_url, burgrx_user, burgrx_password, \
  artifactory_apikey, binaries_ssh_key, binaries_host, binaries_ssh_user, binaries_path_prefix, run_rules_cov, repo, \
  ref, actor, publish_to_binaries, slack_client,slack_channel


def set_output(function, output):
  print(f"::set-output name={function}::{output}")

def notify_slack(msg):
  if slack_channel is not None:
    try:
      return slack_client.chat_postMessage(
        channel=slack_channel,
        text=msg)
    except SlackApiError as e:
      print(f"Could not notify slack: {e.response['error']}")

def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest ):
  print(f"::error  Aborting release")
  github.revoke_release()
  revoke_release(artifactory,binaries, rr)
  set_output("release", f"{rr.project}:{rr.buildnumber} revoked")
  sys.exit(1)

def main():
  organisation, project = repo.split("/")
  version = ref.replace('refs/tags/', '', 1)
  
  # tag shall be like X.X.X.BUILD_NUMBER or X.X.X-MX.BUILD_NUMBER
  if re.compile('\d+\.\d+\.\d+(?:-M\d+)?\.\d+').match(version) is None:                
    print(f"::error Found wrong version: {version}")
    sys.exit(1)

  build_number = version.split(".")[-1]

  github = GitHub(githup_api_url, github_token, github_event_path)

  release_info = github.release_info(version)
  if not release_info:
    print(f"::error  No release info found")
    sys.exit(1)

  rr = ReleaseRequest(organisation, project, build_number)
  burgr = Burgr(burgrx_url, burgrx_user, burgrx_password, rr)

  try:
    burgr.releasability_checks(version, github.current_branch())
  except Exception as e:
    print(f"::error releasability did not complete correctly. " + str(e))
    github.revoke_release()
    sys.exit(1)
  set_output("releasability", f"{repo}:{version} releasability DONE")

  artifactory = Artifactory(artifactory_apikey)
  buildinfo = artifactory.receive_build_info(rr)
  binaries = None

  try:
    artifactory.promote(rr, buildinfo)
    set_output("promote", f"{repo}:{version} promote DONE")

    if publish_to_binaries:
      binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key, binaries_path_prefix)
      publish_all_artifacts_to_binaries(artifactory, binaries, github, rr, buildinfo)
      set_output("publish_to_binaries", f"{repo}:{version} publish_to_binaries DONE")

    if run_rules_cov:
      rules_cov(rr, buildinfo)
      set_output("rules_cov", f"{repo}:{version} rules_cov DONE")

    burgr.notify(buildinfo, 'passed')
    notify_slack(f"Successfully released {repo}:{version} by {actor}")

  except Exception as e:
    error=f"::error release {repo}:{version} did not complete correctly." + str(e)
    print(error)
    notify_slack(error)
    abort_release(github, artifactory, binaries, rr)
    sys.exit(1)

if __name__ == "__main__":
  main()
