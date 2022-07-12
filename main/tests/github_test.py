import os
from unittest.mock import patch, mock_open
import pytest

from release.utils.github import GitHub, GitHubException


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'push'}, clear=True)
def test_must_fail_on_non_release_event():
    with pytest.raises(GitHubException, match='The action was not triggered on release event'):
        GitHub()


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
@patch('release.utils.github.json.load',
       return_value={
           'repository': {'full_name': 'org/project'},
           'release': {'tag_name': 'bad version'},
       })
def test_must_fail_if_tag_not_following_version_pattern(mock_release_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        with pytest.raises(GitHubException, match='The tag must follow this pattern: '):
            GitHub().get_release_request()
        open_mock.assert_called_once()
        mock_release_event.assert_called_once()


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release', 'GITHUB_SHA': 'sha'}, clear=True)
@patch('release.utils.github.json.load',
       return_value={
           'repository': {
               'full_name': 'org/project'
           },
           'release': {
               'tag_name': '1.0.0.42',
               'target_commitish': 'branch'
           },
       })
def test_must_succeed_with_correct_tag(mock_release_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:

        release_request = GitHub().get_release_request()
        assert release_request.org == 'org'
        assert release_request.project == 'project'
        assert release_request.version == '1.0.0.42'
        assert release_request.buildnumber == '42'
        assert release_request.branch == 'branch'
        assert release_request.sha == 'sha'
        open_mock.assert_called_once()
        mock_release_event.assert_called_once()


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release', 'GITHUB_SHA': 'sha'}, clear=True)
@patch('release.utils.github.json.load',
       return_value={
           'repository': {
               'full_name': 'org/project'
           },
           'release': {
               'tag_name': '1.0.0.42',
               'target_commitish': 'c747bee7bf5cfc8c0ad5fbc126d516c0a1aa42ef'
           },
       })
def test_must_succeed_with_target_commitish_containing_a_commit(mock_release_event):
    with patch('release.utils.github.open', mock_open()) as open_mock:

        release_request = GitHub().get_release_request()
        assert release_request.org == 'org'
        assert release_request.project == 'project'
        assert release_request.version == '1.0.0.42'
        assert release_request.buildnumber == '42'
        assert release_request.branch == 'master'
        assert release_request.sha == 'sha'
        open_mock.assert_called_once()
        mock_release_event.assert_called_once()


@patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release', 'GITHUB_SHA': 'sha', 'GITHUB_TOKEN': 'token'}, clear=True)
@patch('requests.delete')
@patch('requests.patch')
@patch('release.utils.github.json.load',
       return_value={
           'repository': {
               'git_refs_url': 'git_refs_url{/sha}'
           },
           'release': {
               'tag_name': '1.0.0.42',
               'url': 'release_url'
           },
       })
def test_revoke_release(mock_release_event, mock_update_release, mock_delete_tag):
    with patch('release.utils.github.open', mock_open()) as open_mock:
        GitHub().revoke_release()
        open_mock.assert_called_once()
        mock_release_event.assert_called_once()
        mock_update_release.assert_called_once_with(
            'release_url',
            json={'draft': True, 'tag_name': '1.0.0.42'},
            headers={'Authorization': f'token token'}
        )
        mock_delete_tag.assert_called_once_with(
            'git_refs_url/tags/1.0.0.42',
            headers={'Authorization': f'token token'}
        )


@patch.dict(os.environ, {'INPUT_PUBLISH_TO_BINARIES': 'true'}, clear=True)
def test_do_publish_to_binaries():
    assert GitHub.is_publish_to_binaries()


def test_do_not_publish_to_binaries():
    assert not GitHub.is_publish_to_binaries()
