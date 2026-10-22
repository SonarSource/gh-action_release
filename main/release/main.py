import os
import shlex
import tempfile

from dryable import Dryable
from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.buildinfo import BuildInfo
from release.utils.dryrun import DryRunHelper
from release.utils.github import GitHub
from release.utils.maven_central import (
    download_artifacts_for_central, drop_validated, finalize, parse_exclusions, parse_placeholder_javadoc,
    validate_before_promote)
from release.utils.release import publish_all_artifacts_to_binaries, revoke_release, set_output
from release.utils.slack import notify_slack
from release.vars import binaries_bucket_name

CENTRAL_URL = "https://central.sonatype.com"

# Release inputs that the manual re-sync script must be given to rebuild the same Central bundle
MANUAL_SYNC_SETTINGS = (
    ('INPUT_MAVEN_CENTRAL_SYNC_EXCLUSIONS', 'CENTRAL_EXCLUSIONS'),
    ('INPUT_MAVEN_CENTRAL_SYNC_EXCLUDE', 'CENTRAL_EXCLUDE'),
    ('INPUT_MAVEN_CENTRAL_SYNC_PLACEHOLDER_JAVADOC', 'CENTRAL_PLACEHOLDER_JAVADOC'),
)

MANDATORY_ENV_VARIABLES = [
    "ARTIFACTORY_ACCESS_TOKEN"
]


@Dryable(logging_msg='{function}()')
def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest,
                  promoted: bool):
    print("::error::Release failed. JFrog/S3 artifacts are being revoked. "
          "The GitHub release and tag are preserved (immutability-safe mode since v6.8.1) — "
          "retry via workflow_dispatch with the same version and releaseId, no rebuild needed.")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr, unpromote=promoted)
    set_output("release", f"{rr.project}:{rr.buildnumber} aborted")


def is_maven_central_sync_enabled():
    # Central Vault secrets aren't fetched in dry runs, so this must stay disabled too.
    return (os.environ.get('INPUT_MAVEN_CENTRAL_SYNC', 'false').lower() == "true"
            and not DryRunHelper.is_dry_run_enabled())


def is_maven_central_sync_required():
    return os.environ.get('INPUT_MAVEN_CENTRAL_SYNC_REQUIRED', 'false').lower() == "true"


def _maven_central_input_errors():
    if not is_maven_central_sync_enabled():
        return []
    errors = []
    if not os.environ.get('CENTRAL_TOKEN'):
        errors.append('env CENTRAL_TOKEN is empty but required as INPUT_MAVEN_CENTRAL_SYNC is true')
    for name, parse in (('INPUT_MAVEN_CENTRAL_SYNC_EXCLUDE', parse_exclusions),
                        ('INPUT_MAVEN_CENTRAL_SYNC_PLACEHOLDER_JAVADOC', parse_placeholder_javadoc)):
        try:
            parse(os.environ.get(name, '-'))
        except ValueError as e:
            errors.append(f'{name} is invalid: {e}')
    return errors


def _warn_if_deprecated_exclusions(exclusions):
    if exclusions not in ('', '-'):
        print("::warning::maven_central_sync_exclusions is deprecated, use maven_central_sync_exclude instead "
              "(':my-artifact' drops every file of an artifact; '::@nupkg' drops only the .nupkg files and keeps their pom)")


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

    errors.extend(_maven_central_input_errors())

    if errors:
        new_line = "\n"
        raise InvalidInputParametersException(f'The execution were aborted due to the following error(s):\n'
                                              f'{new_line.join(errors)}\n'
                                              f'If needed, please contact the Engineering Experience squad.'
                                              )


def _validate_on_central(artifactory, buildinfo, release_request):
    """Build the Central bundle and validate it. Returns (deployment_id, error).

    A bundle that cannot be built always raises. A validation failure raises only when Central is required;
    otherwise it is returned as the error so that the release can complete without Central.
    """
    with tempfile.TemporaryDirectory() as local_repo_dir:
        exclusions = os.environ.get('INPUT_MAVEN_CENTRAL_SYNC_EXCLUSIONS', '-')
        _warn_if_deprecated_exclusions(exclusions)
        download_artifacts_for_central(
            artifactory, buildinfo, local_repo_dir, exclusions,
            os.environ.get('INPUT_MAVEN_CENTRAL_SYNC_EXCLUDE', '-'),
            os.environ.get('INPUT_MAVEN_CENTRAL_SYNC_PLACEHOLDER_JAVADOC', '-'))
        deployment_name = f"{release_request.project}-{release_request.buildnumber}"
        try:
            return validate_before_promote(
                local_repo_dir, CENTRAL_URL, os.environ.get('CENTRAL_TOKEN'), deployment_name), None
        except Exception as e:
            if is_maven_central_sync_required():
                raise
            print(f"::error::Maven Central validation failed, the release continues on Repox only: {e}")
            return None, e


def _finalize_on_central(release_request, deployment_id):
    dummy = os.environ.get('INPUT_IS_DUMMY_PROJECT', 'false').lower() == "true"
    try:
        central_token = os.environ.get('CENTRAL_TOKEN')
        if dummy:
            drop_validated(deployment_id, CENTRAL_URL, central_token)
        else:
            finalize(deployment_id, CENTRAL_URL, central_token)
        set_output("maven_central_deployment_id", deployment_id)
    except Exception as e:
        # Never revoke here: Repox is already promoted and Central may already be publishing.
        action = "drop" if dummy else "publish"
        message = (f"Released {release_request.project}:{release_request.version} to Repox, "
                   f"but Maven Central {action} of deployment {deployment_id} failed ({e}). "
                   f"Check {CENTRAL_URL} and publish/drop it manually. Do NOT re-run the release.")
        print(f"::error::{message}")
        notify_slack(message)
        raise SystemExit(1) from e


def _report_pending_central_sync(release_request, binaries, central_error):
    settings = [f"{variable}={shlex.quote(os.environ[name])}" for name, variable in MANUAL_SYNC_SETTINGS
                if os.environ.get(name, '-') not in ('', '-')]
    command = " ".join([*settings, "scripts/manual-maven-central-sync.sh",
                        release_request.project, release_request.buildnumber])
    message = (f"Released {release_request.project}:{release_request.version} to Repox"
               f"{' and binaries' if binaries else ''}, but NOT to Maven Central ({central_error}). "
               f"Once the cause is solved, publish it with: {command}. Do NOT re-run the release.")
    print(f"::error::{message}")
    try:
        notify_slack(message)
    except Exception as slack_error:
        print(f"::warning::Could not notify Slack: {slack_error}")
    set_output("maven_central_sync_pending", "true")
    raise SystemExit(1) from central_error


def main():
    DryRunHelper.init()
    github = GitHub()
    release_request = github.get_release_request()
    artifactory = Artifactory(os.environ.get('ARTIFACTORY_ACCESS_TOKEN'))
    buildinfo = artifactory.receive_build_info(release_request)
    check_params(buildinfo)
    binaries = None
    promoted = False
    # Set the project name output for use by dependent workflows
    set_output("project_name", release_request.project)
    try:
        deployment_id, central_error = None, None
        if is_maven_central_sync_enabled():
            deployment_id, central_error = _validate_on_central(artifactory, buildinfo, release_request)

        artifactory.promote(release_request, buildinfo)
        promoted = True
        set_output("promote", 'done')  # There is no value to do it except to not break existing workflows

        if deployment_id:
            _finalize_on_central(release_request, deployment_id)

        if github.is_publish_to_binaries():
            binaries = Binaries(binaries_bucket_name)
            publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo)
            set_output("publish_to_binaries", "done")  # There is no value to do it except to not break existing workflows
        if central_error:
            _report_pending_central_sync(release_request, binaries, central_error)
        notify_slack(f"Successfully released {release_request.project}:{release_request.version}")
    except Exception as e:
        notify_slack(
            f"Failed to release {release_request.project}:{release_request.version}. "
            f"GitHub release and tag are preserved — retry via workflow_dispatch, no rebuild needed."
        )
        abort_release(github, artifactory, binaries, release_request, promoted)
        raise e


if __name__ == "__main__":
    main()
