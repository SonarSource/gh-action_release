import re
import sys

from steps.release import revoke_release, publish_all_artifacts_to_binaries
from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.bintray import Bintray
from utils.burgr import Burgr
from utils.cirrus import rules_cov
from utils.github import GitHub
from vars import githup_api_url, github_token, github_event_path, burgrx_url, burgrx_user, burgrx_password, \
  artifactory_apikey, distribute_target, bintray_api_url, bintray_user, bintray_apikey, central_user, central_password, \
  binaries_ssh_key, binaries_host, binaries_ssh_user, run_rules_cov, distribute, repo, ref


def set_releasability_output(output):
  print(f"::set-output name=releasability::{output}")


def set_release_output(function, output):
  print(f"::set-output name={function}::{output}")

def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest ):
  print(f"::error  Aborting release")
  #github.revoke_release()
  revoke_release(artifactory,binaries, rr)
  set_release_output("release", f"{rr.project}:{rr.buildnumber} revoked")
  sys.exit(1)

def main():
  organisation, project = repo.split("/")
  version = ref.replace('refs/tags/', '', 1)
  # tag shall be like X.X.X.BUILD_NUMBER
  if re.compile('\d+\.\d+\.\d+\.\d+').match(version) is None:
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
    print(f"::error relesability did not complete correctly. " + str(e))
    sys.exit(1)

  artifactory = Artifactory(artifactory_apikey, distribute_target)
  buildinfo = artifactory.receive_build_info(rr)
  binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key)

  try:
    artifactory.promote(rr, buildinfo)
    set_release_output("promote", f"{repo}:{version} promote DONE")

    publish_all_artifacts_to_binaries(artifactory, binaries, rr, buildinfo)
    set_release_output("publish_to_binaries", f"{repo}:{version} publish_to_binaries DONE")

    if run_rules_cov:
      rules_cov(rr, buildinfo)
      set_release_output("rules_cov", f"{repo}:{version} rules_cov DONE")

    if (distribute and buildinfo.is_public()) or distribute_target is not None:
      artifactory.distribute_to_bintray(rr, buildinfo)
      set_release_output("distribute_to_bintray", f"{repo}:{version} distribute_to_bintray DONE")

    if distribute and buildinfo.is_public():
      bintray = Bintray(bintray_api_url, bintray_user, bintray_apikey, central_user, central_password)
      bintray.sync_to_central(rr.project, buildinfo.get_package(), version)
      set_release_output("sync_to_central", f"{repo}:{version} sync_to_central DONE")

    burgr.notify(buildinfo, 'passed')

  except Exception as e:
    print(f"::error release did not complete correctly." + str(e))
    abort_release(github, artifactory, binaries, rr)
    sys.exit(1)

if __name__ == "__main__":
  main()
