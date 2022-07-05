from unittest.mock import patch, mock_open

from release.main import main
from release.utils.artifactory import Artifactory
from release.utils.burgr import Burgr
from release.utils.github import GitHub


@patch('release.utils.github.json.load', return_value={})
@patch.object(GitHub, 'get_repo', return_value='org/project')
@patch.object(GitHub, 'get_ref', return_value='refs/tags/1.0.0.42')
@patch.object(GitHub, 'release_info')
@patch.object(GitHub, 'current_branch', return_value='branch')
@patch.object(Burgr, 'start_releasability_checks')
@patch.object(Burgr, 'get_releasability_status')
@patch.object(Artifactory, 'receive_build_info')
@patch.object(Artifactory, 'promote')
@patch.object(Burgr, 'notify')
@patch('release.main.notify_slack')
def test_main(notify_slack,
              burgr_notify,
              artifactory_promote, artifactory_receive_build_info,
              burgr_start_releasability_checks, burgr_get_releasability_status,
              github_current_branch, github_release_info, github_get_ref, github_get_repo, test_json_load):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        main()
        open_mock.assert_called_once()
        test_json_load.assert_called_once()
        github_get_repo.assert_called_once()
        github_get_ref.assert_called_once()
        github_release_info.assert_called_once_with('1.0.0.42')
        github_current_branch.assert_called_once()
        burgr_start_releasability_checks.assert_called_once_with('1.0.0.42')
        burgr_get_releasability_status.assert_called_once_with('1.0.0.42')
        artifactory_receive_build_info.assert_called_once()
        artifactory_promote.assert_called_once()
        burgr_notify.assert_called_once_with('passed')
        notify_slack.assert_called_once_with('Successfully released org/project:1.0.0.42')
