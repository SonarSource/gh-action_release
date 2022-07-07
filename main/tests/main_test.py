import os
from unittest.mock import patch, mock_open, ANY, call, Mock, MagicMock

import pytest

from release.main import main, set_output, abort_release
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.burgr import Burgr
from release.utils.github import GitHub


def test_set_output(capfd):
    set_output('function', 'output')
    out, err = capfd.readouterr()
    assert out == "::set-output name=function::function output\n"
    assert not err


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
@patch('release.utils.github.json.load')
@patch.object(Burgr, 'start_releasability_checks', side_effect=Exception('exception'))
@patch('release.main.notify_slack')
@patch.object(GitHub, 'revoke_release')
def test_releasability_failure(github_revoke_release, notify_slack,
                               burgr_start_releasability_checks,
                               github_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
        with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
            with pytest.raises(Exception, match='exception'):
                main()
                open_mock.assert_called_once()
                github_event.assert_called_once()
                github_release_request.assert_called_once()
                burgr_start_releasability_checks.assert_called_once()
                notify_slack.assert_called_once_with('"Released project:version failed')
                github_revoke_release.assert_called_once()


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
@patch('release.utils.github.json.load')
@patch.object(Burgr, 'start_releasability_checks')
@patch.object(Burgr, 'get_releasability_status')
@patch.object(Artifactory, 'receive_build_info')
@patch.object(Artifactory, 'promote', side_effect=Exception('exception'))
@patch('release.main.notify_slack')
@patch('release.main.abort_release')
def test_promotion_failure(abort_release, notify_slack,
                           artifactory_promote, artifactory_receive_build_info,
                           burgr_start_releasability_checks, burgr_get_releasability_status,
                           github_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
        with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
            with pytest.raises(Exception, match='exception'):
                main()
                open_mock.assert_called_once()
                github_event.assert_called_once()
                github_release_request.assert_called_once()
                burgr_start_releasability_checks.assert_called_once()
                burgr_get_releasability_status.assert_called_once()
                artifactory_receive_build_info.assert_called_once_with(release_request)
                artifactory_promote.assert_called_once_with(release_request, ANY)
                notify_slack.assert_called_once_with('"Released project:version failed')
                abort_release(ANY, ANY, ANY, release_request)


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
@patch('release.utils.github.json.load')
@patch.object(Burgr, 'start_releasability_checks')
@patch.object(Burgr, 'get_releasability_status')
@patch.object(Artifactory, 'receive_build_info')
@patch.object(Artifactory, 'promote')
@patch.object(GitHub, 'is_publish_to_binaries', return_value=True)
@patch.object(Burgr, 'notify')
@patch('release.main.notify_slack')
@patch('release.main.set_output')
def test_main_happy_path(set_output, notify_slack,
                         burgr_notify,
                         github_is_publish_to_binaries,
                         artifactory_promote, artifactory_receive_build_info,
                         burgr_start_releasability_checks, burgr_get_releasability_status,
                         github_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
        with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
            main()
            open_mock.assert_called_once()
            github_event.assert_called_once()
            github_release_request.assert_called_once()
            burgr_start_releasability_checks.assert_called_once()
            burgr_get_releasability_status.assert_called_once()
            artifactory_receive_build_info.assert_called_once_with(release_request)
            artifactory_promote.assert_called_once_with(release_request, ANY)
            github_is_publish_to_binaries.assert_called_once()
            burgr_notify.assert_called_once_with('passed')
            notify_slack.assert_called_once_with('Successfully released project:version')
            assert set_output.call_count == 3
            set_output.assert_has_calls([call('releasability', 'done'), call('promote', 'done'), call('publish_to_binaries', 'done')])
