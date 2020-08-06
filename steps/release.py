from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.burgr import notify_burgr
from utils.cirrus import rules_cov

revoke = True

def release(artifactory: Artifactory, binaries, release_request: ReleaseRequest, attach_to_github_release: bool, run_rules_cov: bool):
  if attach_to_github_release:
    print("Attaching artifacts to github release")
  else:
    print("No attachement to github release")

  buildinfo = artifactory.receive_build_info(release_request)
  try:
    artifactory.promote(release_request, buildinfo)
    publish_all_artifacts(artifactory, binaries, release_request, buildinfo)
    notify_burgr(release_request, buildinfo, 'passed')
    if run_rules_cov:
      rules_cov(release_request, buildinfo)
  except Exception as e:
    notify_burgr(release_request, buildinfo, 'failed')
    print(f"Error during the release for {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e

def revoke_release(artifactory: Artifactory, binaries, release_request: ReleaseRequest):
  buildinfo = artifactory.receive_build_info(release_request)
  try:
    artifactory.promote(release_request, buildinfo, True)
  except Exception as e:
    print(f"Error could not unpromote {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e
  try:
    publish_all_artifacts(artifactory, binaries, release_request, buildinfo, revoke)
  except Exception as e:
    print(f"Error could not delete {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e

def get_action(revoke):
  if revoke:
    return "deleting"
  else:
    return "publishing"

def publish_all_artifacts(artifactory, binaries, release_request, buildinfo, revoke=False):
  print(f"{get_action(revoke)} artifacts for {release_request.project}#{release_request.buildnumber}")
  release_url = ""
  repo = buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace('qa', 'builds')
  version = buildinfo.get_version()
  allartifacts = buildinfo.get_artifacts_to_publish()
  if allartifacts:
    print(f"{get_action(revoke)}: {allartifacts}")
    artifacts = allartifacts.split(",")
    artifacts_count = len(artifacts)
    if artifacts_count == 1:
      print("only 1")
      return publish_artifact(artifactory, binaries, artifacts[0], version, repo, revoke)
    print(f"{artifacts_count} artifacts")
    for i in range(0, artifacts_count):
      print(f"artifact {artifacts[i]}")
      release_url = publish_artifact(artifactory, binaries, artifacts[i], version, repo, revoke)
  return release_url


def publish_artifact(artifactory, binaries, artifact_to_publish, version, repo, revoke=False):
  print(f"{get_action(revoke)} {artifact_to_publish}#{version}")
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
  if revoke:
    binaries.delete(filename, gid, aid, version)
  else: 
    tempfile = artifactory.download(artifactory_repo, gid, aid, qual, ext, version)
    return binaries.upload(tempfile, filename, gid, aid, version)
