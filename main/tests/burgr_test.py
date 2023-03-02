import os

from unittest.mock import patch, ANY
from pytest import fixture

from release.releasability_check import do_releasability_checks
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.burgr import Burgr
from release.utils.github import GitHub
from unittest.mock import mock_open

@fixture
def release_request():
    return ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')


class BurgrResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = '{ "message" : "done" }'


def test_notify(release_request):
    with patch('release.utils.burgr.requests.post', return_value=BurgrResponse(200)) as request:
        Burgr('url', 'user', 'password', release_request).notify('status')
        request.assert_called_once_with(
            'url/api/stage',
            json={
               'repository': 'org/project',
               'pipeline': 'buildnumber',
               'name': 'RELEASE',
               'system': 'github',
               'type': 'release',
               'number': 'buildnumber',
               'branch': 'branch',
               'sha1': 'sha',
               'url': 'https://github.com/org/project/releases',
               'status': 'status',
               'metadata': '',
               'started_at': ANY,
               'finished_at': ANY
            },
            auth=ANY
        )


def test_releasability_checks(release_request):
    with patch('release.utils.burgr.requests.post', return_value=BurgrResponse(200)) as request:
        Burgr('url', 'user', 'password', release_request).start_releasability_checks()
        request.assert_called_once_with(
            'url/api/project/SonarSource/project/releasability/start/version',
            auth=ANY
        )


@patch.dict(os.environ, {"GITHUB_EVENT_NAME": "release"}, clear=True)
@patch("release.utils.github.json.load")
@patch.object(Burgr, "start_releasability_checks")
@patch.object(Burgr, "get_releasability_status")
def test_releasability_checks_script(
    burgr_get_releasability_status, burgr_start_releasability_checks, github_event
):
    with patch("release.utils.github.open", mock_open()) as open_mock:
        release_request = ReleaseRequest(
            "org", "project", "version", "buildnumber", "branch", "sha"
        )
        with patch.object(
            GitHub, "get_release_request", return_value=release_request
        ) as github_release_request:
            do_releasability_checks()
            open_mock.assert_called_once()
            github_event.assert_called_once()
            github_release_request.assert_called_once()
            burgr_start_releasability_checks.assert_called_once()
            burgr_get_releasability_status.assert_called_once()
