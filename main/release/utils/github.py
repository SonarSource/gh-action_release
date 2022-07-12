import json
import os
import re
import requests

from release.steps.ReleaseRequest import ReleaseRequest


class GitHubException(Exception):
    pass


class GitHub:
    token: str
    event: {}

    def __init__(self):
        self.token = os.environ.get('GITHUB_TOKEN')
        if os.environ.get('GITHUB_EVENT_NAME') != 'release':
            raise GitHubException('The action was not triggered on release event')
        with open(os.environ.get('GITHUB_EVENT_PATH')) as file:
            self.event = json.load(file)

    def get_release_request(self) -> ReleaseRequest:
        repo = self._get_repository()["full_name"]
        organisation, project = repo.split("/")
        version = self._get_release()['tag_name']
        # tag shall be like X.X.X.BUILD_NUMBER or X.X.X-MX.BUILD_NUMBER or X.X.X+BUILD_NUMBER (SEMVER)
        version_pattern = re.compile(r'^\d+\.\d+\.\d+(?:-M\d+)?[.+](\d+)$')
        version_match = version_pattern.match(version)
        if version_match is None:
            raise GitHubException('The tag must follow this pattern: X.X.X.BUILD_NUMBER or X.X.X-MX.BUILD_NUMBER or X.X.X+BUILD_NUMBER')
        branch_name = self._get_release()['target_commitish']
        if re.compile("^([a-f0-9]{40})$").match(branch_name):
            branch_name = 'master'
        return ReleaseRequest(organisation, project,
                              version, version_match.groups()[0],
                              branch_name, os.environ.get('GITHUB_SHA'))

    def revoke_release(self) -> None:
        tag_name = self._get_release()["tag_name"]
        headers = {'Authorization': f'token {self.token}'}
        payload = {'draft': True, 'tag_name': tag_name}
        requests.patch(self._get_release()['url'], json=payload, headers=headers)
        # Delete tag
        requests.delete(self._get_repository().get("git_refs_url").replace("{/sha}", f'/tags/{tag_name}'), headers=headers)

    @staticmethod
    def is_publish_to_binaries():
        return os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true"

    def _get_release(self) -> {}:
        return self.event["release"]

    def _get_repository(self) -> {}:
        return self.event["repository"]
