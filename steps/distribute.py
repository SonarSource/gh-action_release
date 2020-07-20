from utils import ReleaseRequest
from utils.artifactory import Artifactory


def distribute_release(artifactory: Artifactory, release_request: ReleaseRequest):
  buildinfo = artifactory.receive_build_info(release_request)
  try:
    if check_public(buildinfo):
      artifactory.distribute_build(release_request.project, release_request.buildnumber)
  except Exception as e:
    print(f"Could not get repository for {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e


def check_public(buildinfo):
  artifacts = buildinfo.get_artifacts_to_publish()
  if artifacts:
    return "org.sonarsource" in artifacts
  else:
    return False
