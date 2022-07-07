from unittest.mock import patch, ANY
from pytest import fixture

from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.burgr import Burgr


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
