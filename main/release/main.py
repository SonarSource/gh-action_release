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


if __name__ == "__main__":
    main()
