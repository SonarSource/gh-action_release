import os
import tempfile

from dryable import Dryable
from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.buildinfo import BuildInfo
from release.utils.dryrun import DryRunHelper
from release.utils.github import GitHub
from release.utils.maven_central import download_artifacts_for_central, finalize, validate_before_promote
from release.utils.release import publish_all_artifacts_to_binaries, revoke_release, set_output
from release.utils.slack import notify_slack
from release.vars import binaries_bucket_name

CENTRAL_URL = "https://central.sonatype.com"

MANDATORY_ENV_VARIABLES = [
    "ARTIFACTORY_ACCESS_TOKEN"
]


@Dryable(logging_msg='{function}()')
def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    print("::error::Release failed. JFrog/S3 artifacts are being revoked. "
          "The GitHub release and tag are preserved (immutability-safe mode since v6.8.1) — "
          "retry via workflow_dispatch with the same version and releaseId, no rebuild needed.")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    set_output("release", f"{rr.project}:{rr.buildnumber} aborted")


def is_maven_central_sync_enabled():
    # Central Vault secrets aren't fetched in dry runs, so this must stay disabled too.
    return (os.environ.get('INPUT_MAVEN_CENTRAL_SYNC', 'false').lower() == "true"
            and not DryRunHelper.is_dry_run_enabled())


def check_params(buildinfo=BuildInfo({})):
    """A function that prevent further execution when input and output gh-action parameters are not valid
    :param buildinfo: Artifactory Build Info
    """

    print("Checking gh-action_release input/output parameters ...")

    errors = []
    for mandatory_env in MANDATORY_ENV_VARIABLES:
        if os.environ.get(mandatory_env) is None:
            errors.append(f"env {mandatory_env} is empty")

    if os.environ.get('INPUT_SLACK_CHANNEL') is not None and os.environ.get('SLACK_API_TOKEN') is None:
        errors.append('env SLACK_API_TOKEN is empty but required as INPUT_SLACK_CHANNEL is defined')

    if os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true":
        if os.environ.get('BINARIES_AWS_DEPLOY') is None:
            errors.append('env BINARIES_AWS_DEPLOY is empty but required as INPUT_PUBLISH_TO_BINARIES is true')
        if not DryRunHelper.is_dry_run_enabled() and not buildinfo.get_property('buildInfo.env.ARTIFACTORY_DEPLOY_REPO'):
            errors.append('buildInfo.env.ARTIFACTORY_DEPLOY_REPO is required as INPUT_PUBLISH_TO_BINARIES is true')

    if is_maven_central_sync_enabled() and not os.environ.get('CENTRAL_TOKEN'):
        errors.append('env CENTRAL_TOKEN is empty but required as INPUT_MAVEN_CENTRAL_SYNC is true')

    if errors:
        new_line = "\n"
        raise InvalidInputParametersException(f'The execution were aborted due to the following error(s):\n'
                                              f'{new_line.join(errors)}\n'
                                              f'If needed, please contact the Engineering Experience squad.'
                                              )


def main():
    DryRunHelper.init()
    github = GitHub()
    release_request = github.get_release_request()
    artifactory = Artifactory(os.environ.get('ARTIFACTORY_ACCESS_TOKEN'))
    buildinfo = artifactory.receive_build_info(release_request)
    check_params(buildinfo)
    binaries = None
    # Set the project name output for use by dependent workflows
    set_output("project_name", release_request.project)
    try:
        deployment_id = None
        if is_maven_central_sync_enabled():
            with tempfile.TemporaryDirectory() as local_repo_dir:
                exclusions = os.environ.get('INPUT_MAVEN_CENTRAL_SYNC_EXCLUSIONS', '-')
                download_artifacts_for_central(artifactory, buildinfo, local_repo_dir, exclusions)
                deployment_name = f"{release_request.project}-{release_request.buildnumber}"
                deployment_id = validate_before_promote(
                    local_repo_dir, CENTRAL_URL, os.environ.get('CENTRAL_TOKEN'), deployment_name)

        artifactory.promote(release_request, buildinfo)
        set_output("promote", 'done')  # There is no value to do it except to not break existing workflows

        if deployment_id:
            try:
                finalize(deployment_id, CENTRAL_URL, os.environ.get('CENTRAL_TOKEN'))
                set_output("maven_central_deployment_id", deployment_id)
            except Exception as e:
                # Never revoke here: Repox is already promoted and Central may already be publishing.
                message = (f"Released {release_request.project}:{release_request.version} to Repox, "
                           f"but Maven Central publish of deployment {deployment_id} failed ({e}). "
                           f"Check {CENTRAL_URL} and publish/drop it manually. Do NOT re-run the release.")
                print(f"::error::{message}")
                notify_slack(message)
                raise SystemExit(1) from e

        if github.is_publish_to_binaries():
            binaries = Binaries(binaries_bucket_name)
            publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo)
            set_output("publish_to_binaries", "done")  # There is no value to do it except to not break existing workflows
        notify_slack(f"Successfully released {release_request.project}:{release_request.version}")
    except Exception as e:
        notify_slack(
            f"Failed to release {release_request.project}:{release_request.version}. "
            f"GitHub release and tag are preserved — retry via workflow_dispatch, no rebuild needed."
        )
        abort_release(github, artifactory, binaries, release_request)
        raise e


if __name__ == "__main__":
    main()
