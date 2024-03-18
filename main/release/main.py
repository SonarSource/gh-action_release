import os

from dryable import Dryable
from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.burgr import Burgr
from release.utils.dryrun import DryRunHelper
from release.utils.github import GitHub
from release.utils.release import publish_all_artifacts_to_binaries, releasability_checks, revoke_release, set_output
from release.utils.slack import notify_slack
from release.vars import binaries_bucket_name, burgrx_password, burgrx_url, burgrx_user

MANDATORY_ENV_VARIABLES = [
    "BURGRX_USER",
    "BURGRX_PASSWORD",
    "ARTIFACTORY_ACCESS_TOKEN"
]


@Dryable(logging_msg='{function}()')
def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    print("::error Aborting release")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    set_output("release", f"{rr.project}:{rr.buildnumber} revoked")


def check_params():
    """A function that prevent further execution when input and output gh-action parameters are not valid"""

    print("Checking gh-action_release input/output parameters ...")

    errors = []
    for mandatory_env in MANDATORY_ENV_VARIABLES:
        if os.environ.get(mandatory_env) is None:
            errors.append(f"env {mandatory_env} is empty")

    if os.environ.get('INPUT_SLACK_CHANNEL') is not None and os.environ.get('SLACK_API_TOKEN') is None:
        errors.append('env SLACK_API_TOKEN is empty but required as INPUT_SLACK_CHANNEL is defined')

    if os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true" and os.environ.get('BINARIES_AWS_DEPLOY') is None:
        errors.append('env BINARIES_AWS_DEPLOY is empty but required as INPUT_PUBLISH_TO_BINARIES is true')

    if errors:
        new_line = "\n"
        raise InvalidInputParametersException(f'The execution were aborted due to the following error(s):\n'
                                              f'{new_line.join(errors)}\n\n'
                                              f'It is likely that the RE-team has to edit the vault policy of the current '
                                              f'repository to provide access to these secrets. \n\n'
                                              f'Please contact #ask-release-engineering or release.engineers@sonarsource.com.'
                                              )


def main():
    check_params()
    DryRunHelper.init()

    github = GitHub()
    release_request = github.get_release_request()

    burgr = Burgr(burgrx_url, burgrx_user, burgrx_password, release_request)

    # Allow skipping releasability checks in exceptional cases
    # Eg: when the releasability checks are not implemented for a specific language
    if os.environ.get('SKIP_RELEASABILITY_CHECKS') == "true":
        set_output("releasability", "done")
    else:
        releasability_checks(github, burgr, release_request)

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
