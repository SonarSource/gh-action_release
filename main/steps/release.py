from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from vars import github_attach


revoke = True

def revoke_release(artifactory: Artifactory, binaries, release_request: ReleaseRequest):
  buildinfo = artifactory.receive_build_info(release_request)
  try:
    artifactory.promote(release_request, buildinfo, True)
  except Exception as e:
    print(f"Error could not unpromote {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e
  try:
    if binaries is not None:
      publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo, revoke)
  except Exception as e:
    print(f"Error could not delete {release_request.project} {release_request.buildnumber} {str(e)}")
    raise e

def get_action(revoke):
  if revoke:
    return "deleting"
  else:
    return "publishing"

def publish_all_artifacts_to_binaries(artifactory, binaries, github, release_request, buildinfo, revoke=False):
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
      return publish_artifact(artifactory, binaries, github, artifacts[0], version, repo, revoke)
    print(f"{artifacts_count} artifacts")
    for i in range(0, artifacts_count):
      print(f"artifact {artifacts[i]}")
      release_url = publish_artifact(artifactory, binaries, github, artifacts[i], version, repo, revoke)
  return release_url


def publish_artifact(artifactory, binaries, github, artifact_to_publish, version, repo, revoke=False):
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
    tempfile = artifactory.download(artifactory_repo, gid, aid, qual, ext, version, binaries.upload_checksums)
    #if github_attach:
      #github.attach_asset_to_release(tempfile,filename)
    return binaries.upload(tempfile, filename, gid, aid, version)
