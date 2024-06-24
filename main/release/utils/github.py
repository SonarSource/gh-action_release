import json
import os
import re
import requests
import logging

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

            # Attempt to get the version number. Depending on the event type, it
            # can be the release tag or an user provided input.
            release = self._get_release()
            version = self.event['inputs']['version'] if release is None else release['tag_name']

            # This is an explicit requirement for project SLVSCODE
            # see https://sonarsource.atlassian.net/browse/BUILD-4915
            version_pattern = re.compile(
                r'^(?:[a-zA-Z]+-)?'   # Optional ProjectName- prefix (required by sonar-scanner-azdo; see https://sonarsource.atlassian.net/browse/BUILD-5293)
                r'\d+\.\d+\.\d+'      # Major.Minor.Patch version
                r'(?:-M\d+)?'         # Optional -Mx suffix
                r'[.+]'               # Separator (+ is required by sonarlint-vscode; see https://sonarsource.atlassian.net/browse/BUILD-4915)
                r'(\d+)$'             # Build number in a captured group
            )
            version_match = version_pattern.match(version)
            if version_match is None:
                raise GitHubException(
                    'The tag must follow this pattern: [ProjectName-]Major.Minor.Patch[-Mx][.+]BuildNumber\n'
                    'Where:\n'
                    '- "ProjectName-" is an optional prefix (any sequence of letters followed by a dash).\n'
                    '- "Major.Minor.Patch" is the version number (three numbers separated by dots).\n'
                    '- "-Mx" is an optional suffix (a dash followed by "M" and a number).\n'
                    '- "[.+]" is a separator, either a dot or a plus sign.\n'
                    '- "BuildNumber" is the build number (a number at the end of the string).'
                )
            DEFAULT_BRANCH = self.event.get('repository', {}).get('default_branch', 'master')
            if release is None:
                branch_name = DEFAULT_BRANCH
            else:
                branch_name = release['target_commitish']
                if re.compile("^([a-f0-9]{40})$").match(branch_name):
                    branch_name = DEFAULT_BRANCH

            return ReleaseRequest(organisation, project,
                                  version, version_match.groups()[0],
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
        tag_name = release["tag_name"]
        headers = {'Authorization': f'token {self.token}'}
        payload = {'draft': True, 'tag_name': tag_name}
        requests.patch(release['url'], json=payload, headers=headers)
        # Delete tag
        requests.delete(self._get_repository().get("git_refs_url").replace("{/sha}", f'/tags/{tag_name}'), headers=headers)

    @staticmethod
    def is_publish_to_binaries():
        return os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true"

    def _get_release(self) -> dict | None:
        return self.event.get("release", None)

    def _get_repository(self) -> {}:
        return self.event["repository"]
