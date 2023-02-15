import os

from dryable import Dryable
from slack_sdk.errors import SlackApiError

from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.burgr import Burgr
from release.utils.dryrun import DryRunHelper
from release.utils.github import GitHub
from release.utils.release import revoke_release, publish_all_artifacts_to_binaries
from release.vars import burgrx_url, burgrx_user, burgrx_password, slack_client, slack_channel, binaries_bucket_name, project_name

mandatory_env_variables = [
    "BURGRX_USER",
    "BURGRX_PASSWORD",
    "ARTIFACTORY_ACCESS_TOKEN",
    "BINARIES_AWS_DEPLOY"
]


def set_output(function, output):
    print(f"::set-output name={function}::{function} {output}")


@Dryable(logging_msg='{function}({args}{kwargs})')
def notify_slack(msg):
    if slack_channel is not None:
        try:
            return slack_client.chat_postMessage(
                channel=slack_channel,
                text=msg)
        except SlackApiError as e:
            print(f"Could not notify slack: {e.response['error']}")


@Dryable(logging_msg='{function}()')
def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    print("::error Aborting release")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    set_output("release", f"{rr.project}:{rr.buildnumber} revoked")


def check_params():
    """A function that prevent further execution when input and output gh-action parameters are not valid"""

    print(f"Checking {project_name} input/output parameters ...")

    errors = []
    for mandatory_env in mandatory_env_variables:
        if os.environ.get(mandatory_env) is None:
            errors.append(f"env {mandatory_env} is empty")

    if os.environ.get('INPUT_SLACK_CHANNEL') is not None and os.environ.get('SLACK_API_TOKEN') is None:
        errors.append('env SLACK_API_TOKEN is empty but required as INPUT_SLACK_CHANNEL is defined')

    if errors:
        new_line = "\n"
        raise InvalidInputParametersException(f'The execution of {project_name} is aborted due to the following error(s):\n'
                                              f'{new_line.join(errors)}\n\n'
                                              f'If you are using {project_name} and get this message,\n'
                                              f' it probably means that the RE-team has to edit the vault policy of the current '
                                              f'repository to provide access to these secrets. \n\n'
                                              f'Please get in touch with us so we can help you: #ask-release-engineering.'
                                              )


def main():
    check_params()
    DryRunHelper.init()

    github = GitHub()
    release_request = github.get_release_request()

    burgr = Burgr(burgrx_url, burgrx_user, burgrx_password, release_request)
    try:
        burgr.start_releasability_checks()
        burgr.get_releasability_status()
        set_output("releasability", "done")  # There is no value to do it expect to not break existing workflows
    except Exception as e:
        notify_slack(f"Released {release_request.project}:{release_request.version} failed")
        github.revoke_release()
        raise e

    artifactory = Artifactory(os.environ.get('ARTIFACTORY_ACCESS_TOKEN'))
    buildinfo = artifactory.receive_build_info(release_request)
    binaries = None
    try:
        artifactory.promote(release_request, buildinfo)
        set_output("promote", 'done')  # There is no value to do it expect to not break existing workflows

        if github.is_publish_to_binaries():
            binaries = Binaries(binaries_bucket_name)
            publish_all_artifacts_to_binaries(artifactory, binaries, release_request, buildinfo)
            set_output("publish_to_binaries", "done")  # There is no value to do it expect to not break existing workflows

        burgr.notify('passed')
        notify_slack(f"Successfully released {release_request.project}:{release_request.version}")
    except Exception as e:
        notify_slack(f"Released {release_request.project}:{release_request.version} failed")
        abort_release(github, artifactory, binaries, release_request)
        raise e


if __name__ == "__main__":
    main()
