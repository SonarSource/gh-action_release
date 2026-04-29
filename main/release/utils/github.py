import json
import os
import re
import logging
import requests

from release.utils.dryrun import DryRunHelper
from release.steps.ReleaseRequest import ReleaseRequest
from dryable import Dryable


ALLOWED_GITHUB_ACTIONS = set(['release', 'workflow_dispatch'])


class GitHubException(Exception):
    pass


class GitHub:
    token: str
    event: {}
    logger: logging.Logger

    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        self.logger = logging.getLogger('gh-action')
        github_event = os.environ.get('GITHUB_EVENT_NAME')
        if github_event in ALLOWED_GITHUB_ACTIONS or DryRunHelper.is_dry_run_enabled():
            with open(os.environ.get('GITHUB_EVENT_PATH')) as file:
                self.event = json.load(file)
        else:
            raise GitHubException(f"The action was neither triggered on {ALLOWED_GITHUB_ACTIONS} events (is: '{github_event}'), neither with dry_run=true")

    def get_release_request(self) -> ReleaseRequest:
        if DryRunHelper.is_dry_run_enabled():
            return self.__fake_release_request()
        else:
            repo = self._get_repository()["full_name"]
            organisation, project = repo.split("/")

            # Attempt to get the version number. Depending on the event type, it can be the release tag or a user provided input.
            release = self._get_release()
            version = self.event['inputs']['version'] if release is None else release['tag_name']

            # This is an explicit requirement for project SLVSCODE
            # see https://sonarsource.atlassian.net/browse/BUILD-4915
            version_pattern = re.compile(
                r'^(?P<prefix>[a-zA-Z]+-)?'   # Optional ProjectName- prefix (required by sonar-scanner-azdo; see https://sonarsource.atlassian.net/browse/BUILD-5293)
                r'\d+\.\d+\.\d+'              # Major.Minor.Patch version
                r'(?:-M\d+)?'                 # Optional -Mx suffix
                r'[-.+]'                       # Separator (+ is required by sonarlint-vscode; see https://sonarsource.atlassian.net/browse/BUILD-4915)
                r'(?P<build>\d+)$'            # Build number in a captured group
            )
            version_match = version_pattern.match(version)
            if version_match is None:
                raise GitHubException(
                    'The tag must follow this pattern: [ProjectName-]Major.Minor.Patch[-Mx][.+]BuildNumber\n'
                    'Where:\n'
                    '- "ProjectName-" is an optional prefix (any sequence of letters followed by a dash).\n'
                    '- "Major.Minor.Patch" is the version number (three numbers separated by dots).\n'
                    '- "-Mx" is an optional suffix (a dash followed by "M" and a number).\n'
                    '- "[-.+]" is a separator, either a dot, a dash or a plus sign.\n'
                    '- "BuildNumber" is the build number (a number at the end of the string).'
                )
            DEFAULT_BRANCH = self.event.get('repository', {}).get('default_branch', 'master')
            if release is None:
                branch_name = DEFAULT_BRANCH
            else:
                branch_name = release['target_commitish']
                if re.compile("^([a-f0-9]{40})$").match(branch_name):
                    branch_name = DEFAULT_BRANCH

            prefix = version_match.group("prefix")
            if prefix:
                # Required for sonar-scanner-azdo to support two artifacts in repox
                # https://sonarsource.atlassian.net/browse/BUILD-5506
                project = f'{project}-{prefix[:-1]}'

            return ReleaseRequest(organisation, project,
                                  version, version_match.group("build"),
                                  branch_name, os.environ.get('GITHUB_SHA'))

    def __fake_release_request(self) -> ReleaseRequest:
        """Provide a dummy release request object"""
        repo = self._get_repository()["full_name"]
        organisation, project = repo.split("/")
        version = '?.?.?.????'
        branch_name = 'master'
        if re.compile("^([a-f0-9]{40})$").match(branch_name):
            branch_name = 'master'
        return ReleaseRequest(organisation, project,
                              version, "????",
                              branch_name, os.environ.get('GITHUB_SHA'))

    @Dryable(logging_msg='{function}()')
    def revoke_release(self) -> None:
        release = self._get_release()
        if release is None:
            return
        tag_name = release.get("tag_name", "unknown")
        self.logger.warning(
            "revoke_release: GitHub release '%s' is NOT being unpublished or deleted "
            "(immutability-safe mode since v6.8.1). The tag and version are preserved so "
            "the release can be retried via workflow_dispatch without triggering a new build. "
            "JFrog/S3 artifacts have already been revoked by the caller.",
            tag_name,
        )

    @staticmethod
    def is_publish_to_binaries():
        return os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true"

    def _get_release(self) -> dict | None:
        # Retro-compat: the legacy `release:published` event embeds the full release object
        # directly in the event payload, so no API call is needed. v7 uses `workflow_dispatch`
        # which has no release in the payload — we fetch it by tag via the API instead.
        if self.event.get("release") is not None:
            return self.event["release"]
        # workflow_dispatch path: fetch the draft (or published) release by tag via API
        tag = os.environ.get("INPUT_VERSION")
        if not tag:
            return None
        repo = self.event["repository"]["full_name"]
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
            headers={"Authorization": f"token {self.token}"},
        )
        return resp.json() if resp.ok else None

    def _get_repository(self) -> {}:
        return self.event["repository"]
