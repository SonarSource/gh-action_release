import os

from dryable import Dryable
from release.steps import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.burgr import Burgr
from release.utils.github import GitHub
from release.utils.slack import notify_slack

REVOKE = True


def revoke_release(artifactory: Artifactory, binaries, release_request: ReleaseRequest):
    buildinfo = artifactory.receive_build_info(release_request)
    try:
        artifactory.promote(release_request, buildinfo, True)
    except Exception as e:
        print(f"Error could not unpromote {release_request.project} {release_request.buildnumber} {str(e)}")
        raise e
    try:
        if binaries is not None:
            publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo, REVOKE)
    except Exception as e:
        print(f"Error could not delete {release_request.project} {release_request.buildnumber} {str(e)}")
        raise e


def get_action(revoke):
    if revoke:
        return "deleting"
    else:
        return "publishing"


@Dryable(logging_msg='{function}({args})')
def publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo, revoke=False):
    print(f"{get_action(revoke)} artifacts for {release_request.project}#{release_request.buildnumber}")
    repo = buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO').replace('qa', 'builds')
    version = buildinfo.get_version()
    allartifacts = buildinfo.get_artifacts_to_publish()
    if allartifacts:
        print(f"{get_action(revoke)}: {allartifacts}")
        artifacts = allartifacts.split(",")
        artifacts_count = len(artifacts)
        print(f"{artifacts_count} artifacts")
        for i in range(0, artifacts_count):
            print(f"artifact {artifacts[i]}")
            publish_artifact(artifactory, binaries, artifacts[i], version, repo, revoke)


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

    if aid == "sonar-application":
        filename = f"sonarqube-{version}.zip"
        s3_aid = "sonarqube"
    else:
        s3_aid = aid

    if revoke:
        binaries.s3_delete(filename, gid, s3_aid, version)
    else:
        artifact_file = artifactory.download(artifactory_repo, gid, aid, qual, ext, version, binaries.upload_checksums)
        binaries.s3_upload(artifact_file, filename, gid, s3_aid, version)


def set_output(output_name, value):
    """Sets the GitHub Action output.

    Keyword arguments:
    output_name - The name of the output
    value - The value of the output
    """
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as output_stream:
            print(f"{output_name}={value}", file=output_stream)


def releasability_checks(github: GitHub, burgr: Burgr, release_request: ReleaseRequest.ReleaseRequest):
    try:
        burgr.start_releasability_checks()
        burgr.get_releasability_status()
        set_output("releasability", "done")  # There is no value to do it expect to not break existing workflows
    except Exception as e:
        notify_slack(f"Released {release_request.project}:{release_request.version} failed")
        github.revoke_release()
        raise e
