from release.utils.release import revoke_release, publish_all_artifacts_to_binaries
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.burgr import Burgr
from release.utils.github import GitHub
from slack_sdk.errors import SlackApiError
from release.vars import burgrx_url, burgrx_user, burgrx_password, artifactory_apikey, slack_client, slack_channel, binaries_bucket_name


def set_output(function, output):
    print(f"::set-output name={function}::{function} {output}")


def notify_slack(msg):
    if slack_channel is not None:
        try:
            return slack_client.chat_postMessage(
                    channel=slack_channel,
                    text=msg)
        except SlackApiError as e:
            print(f"Could not notify slack: {e.response['error']}")


def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    print(f"::error Aborting release")
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    set_output("release", f"{rr.project}:{rr.buildnumber} revoked")


def main():
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

    artifactory = Artifactory(artifactory_apikey)
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
