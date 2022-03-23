import os
import re
import sys
import coloredlogs
import logging

from steps.release import revoke_release, publish_all_artifacts_to_binaries
from utils.ReleaseRequest import ReleaseRequest
from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.github import GitHub
from slack.errors import SlackApiError

from utils.releasability import Releasability
from vars import githup_api_url, github_token, github_event_path, releasability_access_key_id, releasability_secret_access_key, \
    artifactory_apikey, repo, ref, publish_to_binaries, slack_client, slack_channel, \
    binaries_bucket_name, binaries_access_key_id, binaries_secret_access_key, binaries_region


logger = logging.getLogger(__name__)
coloredlogs.install(level='INFO')


def notify_slack(msg):
    if slack_channel is not None:
        try:
            return slack_client.chat_postMessage(
                channel=slack_channel,
                text=msg)
        except SlackApiError as e:
            logger.error(f"Could not notify slack: {e.response['error']}")


def abort_release(github: GitHub, artifactory: Artifactory, binaries: Binaries, rr: ReleaseRequest):
    logger.error('Aborting release')
    github.revoke_release()
    revoke_release(artifactory, binaries, rr)
    sys.exit(1)


def main():
    organisation, project = repo.split("/")
    version = ref.replace('refs/tags/', '', 1)

    # tag shall be like X.X.X.BUILD_NUMBER or X.X.X-MX.BUILD_NUMBER or X.X.X+BUILD_NUMBER (SEMVER)
    version_pattern = re.compile(r'^\d+\.\d+\.\d+(?:-M\d+)?[.+](\d+)$')
    version_match = version_pattern.match(version)
    if version_match is None:
        logger.error(f"Found wrong version: {version}")
        sys.exit(1)

    build_number = version_match.groups()[0]

    github = GitHub(githup_api_url, github_token, github_event_path)

    release_info = github.release_info(version)
    if not release_info:
        logger.error(f"No release info found")
        sys.exit(1)

    rr = ReleaseRequest(organisation, project, build_number)
    releasability = Releasability(
        releasability_access_key_id, releasability_secret_access_key, os.environ.get('RELEASABILITY_ENV_TYPE', 'Prod'), rr
    )

    try:
        logger.info(f'Checking releasability of version {version} on branch {github.current_branch()}')
        releasability.check(version, github.current_branch(), os.environ.get('GITHUB_SHA'))
        logger.info(f'Releasability passed')
    except Exception as e:
        error = str(e)
        logger.error(error)
        notify_slack(error)
        github.revoke_release()
        sys.exit(1)

    artifactory = Artifactory(artifactory_apikey)
    binaries = None

    try:
        buildinfo = artifactory.receive_build_info(rr)
        artifactory.promote(rr, buildinfo)

        if publish_to_binaries:
            binaries = Binaries(binaries_bucket_name, binaries_access_key_id, binaries_secret_access_key, binaries_region)
            publish_all_artifacts_to_binaries(artifactory, binaries, rr, buildinfo)
        else:
            logger.info('Artifacts are not published')

    except Exception as e:
        error = f"Release {repo}:{version} did not complete correctly: {str(e)}"
        logger.error(error)
        notify_slack(error)
        abort_release(github, artifactory, binaries, rr)
        sys.exit(1)


if __name__ == "__main__":
    main()
