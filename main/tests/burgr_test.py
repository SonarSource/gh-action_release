import json
import os

from unittest.mock import patch, ANY
from pytest import fixture

from release.releasability_check import do_releasability_checks
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.burgr import Burgr
from unittest.mock import mock_open

@fixture
def release_request():
    return ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')


class BurgrResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = json.dumps({'message': 'done'})
        self.raise_for_status = lambda: None


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


@patch.dict(os.environ, {"GITHUB_EVENT_NAME": "workflow_dispatch"}, clear=True)
@patch(
    "release.utils.github.json.load",
    return_value={
        "inputs": {"version": "1.0.0.0"},
        "repository": {"default_branch": "master", "full_name": "org/project"},
    },
)
@patch.object(Burgr, "start_releasability_checks")
@patch.object(Burgr, "get_releasability_status")
def test_releasability_checks_script(
    json_load_mock, burgr_start_releasability_checks, burgr_get_releasability_status
):
    with patch("release.utils.github.open", mock_open()) as open_mock:
        do_releasability_checks()
        open_mock.assert_called_once()
        json_load_mock.assert_called_once()
        burgr_start_releasability_checks.assert_called_once()
        burgr_get_releasability_status.assert_called_once()
