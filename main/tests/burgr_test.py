import json
import re

from unittest.mock import patch, ANY, MagicMock

import pytest

from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.burgr import Burgr, ReleasabilityFailure


class BurgrResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = json.dumps({'message': 'done'})
        self.raise_for_status = lambda: None


def test_notify():
    release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
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


@pytest.mark.parametrize(
    'project, version, is_success, expected_version',
    [
        ('sonarlint-vscode', '1.2.3+4', True, '1.2.3'),
        ('sonar-java', '1.2.3.4', False, '1.2.3.4')
    ]
)
def test_start_releasability_checks(project, version, is_success: bool, expected_version):
    release_request = ReleaseRequest('SonarSource', project, version, 'buildnumber',  'branch', 'sha1')
    if is_success:
        with patch('release.utils.burgr.requests.post', return_value=BurgrResponse(200)) as request:
            Burgr('url', 'user', 'password', release_request).start_releasability_checks()
    else:
        with patch('release.utils.burgr.requests.post', return_value=BurgrResponse(404)) as request:
            with pytest.raises(Exception, match="Releasability checks failed to start: 'done'"):
                Burgr('url', 'user', 'password', release_request).start_releasability_checks()
    request.assert_called_once_with(
        f'url/api/project/SonarSource/{project}/releasability/start/{expected_version}',
        auth=ANY
    )


@pytest.mark.parametrize(
    'is_success', [True, False]
)
def test_get_releasability_status(is_success: bool):
    release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
    if is_success:
        with patch('release.utils.burgr.polling.poll', return_value={'status': 'passed'}) as polling:
            Burgr('url', 'user', 'password', release_request).get_releasability_status()
    else:
        result = {
            'status': 'failed',
            'metadata': "{\"state\":\"ERRORED\",\"checks\":[{\"name\":\"QA\",\"state\":\"FAILED\"}]}"
        }
        with patch('release.utils.burgr.polling.poll', return_value=result) as polling:
            with pytest.raises(ReleasabilityFailure):
                Burgr('url', 'user', 'password', release_request).get_releasability_status()
    polling.assert_called_once()


@pytest.mark.parametrize(
    'response, error', [
        (
            MagicMock(**{'text': 'text','status_code': 404}),
            re.escape("Error occurred while trying to retrieve current releasability status: (404) text")
        ),
        (
            MagicMock(**{'json.return_value': [], 'status_code': 200}),
            'No commit information found in burgrx for this branch'
        ),
        (
            MagicMock(**{'json.return_value': [{'pipelines': []}], 'status_code': 200}),
            "No pipeline info found for version 'version'"
        ),
        (
            MagicMock(**{'json.return_value': [{'pipelines': [{'version': 'version', 'releasable': False}]}], 'status_code': 200}),
            "Pipeline '{'version': 'version', 'releasable': False}' is not releasable"
        )
    ]
)
def test_get_latest_releasability_stage_exception(response, error):
    burgr = Burgr('url', 'user', 'password', ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha'))
    with pytest.raises(Exception, match=error):
        burgr._get_latest_releasability_stage(response)


@pytest.mark.parametrize(
    'response, result', [
        (
            MagicMock(**
                {
                    'json.return_value': [
                        {'pipelines': [{'version': 'bad_version'}]},
                        {'pipelines': [{'version': 'version', 'releasable': True, 'stages': [{'type': 'releasability', 'status': 'passed'}]}]}
                    ],
                    'status_code': 200
                }
            ),
            {'type': 'releasability', 'status': 'passed'}
        ),
        (
            MagicMock(**
                {
                    'json.return_value': [
                        {'pipelines': [{'version': 'version', 'releasable': True}]}
                    ],
                    'status_code': 200
                }
            ),
            False
        )
    ]
)
def test_get_latest_releasability_stage(response, result):
    burgr = Burgr('url', 'user', 'password', ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha'))
    assert result == burgr._get_latest_releasability_stage(response)
