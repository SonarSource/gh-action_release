import os
from unittest.mock import patch, mock_open

from release.utils.github import GitHub


@patch.dict(os.environ, {'GITHUB_SHA': '42'}, clear=True)
@patch('release.utils.github.json.load', return_value={})
def test_get_sha(mock_json_load):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        assert GitHub('github_api_url', 'github_token', 'github_event_path').get_sha() == '42'
        open_mock.assert_called_once()
        mock_json_load.assert_called_once()


@patch.dict(os.environ, {'GITHUB_REPOSITORY': 'github_repo'}, clear=True)
@patch('release.utils.github.json.load', return_value={})
def test_get_repo(mock_json_load):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        assert GitHub('github_api_url', 'github_token', 'github_event_path').get_repo() == 'github_repo'
        open_mock.assert_called_once()
        mock_json_load.assert_called_once()


@patch.dict(os.environ, {'GITHUB_REF': 'github_ref'}, clear=True)
@patch('release.utils.github.json.load', return_value={})
def test_get_ref(mock_json_load):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        assert GitHub('github_api_url', 'github_token', 'github_event_path').get_ref() == 'github_ref'
        open_mock.assert_called_once()
        mock_json_load.assert_called_once()
