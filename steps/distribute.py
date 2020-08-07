from utils import ReleaseRequest
from utils.artifactory import Artifactory
from utils.bintray import Bintray

def distribute_release(artifactory: Artifactory, bintray: Bintray, release_request: ReleaseRequest, version):
  buildinfo = artifactory.receive_build_info(release_request)
  try:
    if buildinfo.is_public():
      artifactory.distribute_build(release_request.project, release_request.buildnumber)
      bintray.sync_to_central(release_request.project,buildinfo.get_package(),version)
  except Exception as e:
    print(f"Could not get repository for {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e
