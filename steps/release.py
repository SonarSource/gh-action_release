from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.binaries import upload
from utils.burgr import notify_burgr
from utils.cirrus import rules_cov


def release(artifactory: Artifactory, release_request: ReleaseRequest, attach_to_github_release, run_rules_cov):
  if attach_to_github_release:
    print("Attaching artifacts to github release")
  else:
    print("No attachement to github release")

  buildinfo = artifactory.receive_build_info(release_request)
  try:
    artifactory.promote(release_request, buildinfo)
    publish_all_artifacts(artifactory, release_request, buildinfo)
    notify_burgr(release_request, buildinfo, 'passed')
    if run_rules_cov:
      rules_cov(release_request, buildinfo)
  except Exception as e:
    notify_burgr(release_request, buildinfo, 'failed')
    print(f"Error during the release for {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e

def revoke(artifactory: Artifactory, release_request: ReleaseRequest):
  buildinfo = artifactory.receive_build_info(release_request)
  try:
    artifactory.promote(release_request, buildinfo, True)
  except Exception as e:
    print(f"Error could not unpromote {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e


def publish_all_artifacts(artifactory, release_request, buildinfo):
  print(f"publishing artifacts for {release_request.project}#{release_request.buildnumber}")
  release_url = ""
  repo = buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace('qa', 'builds')
  version = buildinfo.get_version()
  allartifacts = buildinfo.get_artifacts_to_publish()
  if allartifacts:
    print(f"publishing: {allartifacts}")
    artifacts = allartifacts.split(",")
    artifacts_count = len(artifacts)
    if artifacts_count == 1:
      print("only 1")
      return publish_artifact(artifactory, artifacts[0], version, repo)
    print(f"{artifacts_count} artifacts")
    for i in range(0, artifacts_count):
      print(f"artifact {artifacts[i]}")
      release_url = publish_artifact(artifactory, artifacts[i], version, repo)
  return release_url


def publish_artifact(artifactory, artifact_to_publish, version, repo):
  print(f"publishing {artifact_to_publish}#{version}")
  artifact = artifact_to_publish.split(":")
  gid = artifact[0]
  aid = artifact[1]
  ext = artifact[2]
  qual = ''
  if len(artifact) > 3:
    qual = artifact[3]
  artifactory_repo = repo.replace('builds', 'releases')
  print(f"{gid} {aid} {ext} {qual}")

  filename = f"{aid}-{version}.{ext}"
  if qual:
    filename = f"{aid}-{version}-{qual}.{ext}"
  tempfile = artifactory.download(artifactory_repo, gid, aid, qual, ext, version)
  return upload(tempfile, filename, gid, aid, version)
