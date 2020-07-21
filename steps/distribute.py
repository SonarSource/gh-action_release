from utils import ReleaseRequest
from utils.artifactory import Artifactory
from utils.bintray import Bintray

def distribute_release(artifactory: Artifactory, bintray: Bintray, release_request: ReleaseRequest, version):
  buildinfo = artifactory.receive_build_info(release_request)
  package=get_package(buildinfo)
  try:
    if check_public(buildinfo):
      artifactory.distribute_build(release_request.project, release_request.buildnumber)
      bintray.sync_to_central(release_request.project,package,version)
  except Exception as e:
    print(f"Could not get repository for {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e


def check_public(buildinfo):
  artifacts = buildinfo.get_artifacts_to_publish()
  if artifacts:
    return "org.sonarsource" in artifacts
  else:
    return False

def get_package(buildinfo):
  allartifacts = buildinfo.get_artifacts_to_publish()
  artifacts = allartifacts.split(",")
  artifacts_count = len(artifacts)
  if artifacts_count > 0:
    artifact = artifacts[0].split(":")
    return artifact[0]
  return None
