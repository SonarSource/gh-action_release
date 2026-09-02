import os
from unittest.mock import MagicMock, patch

import pytest
import requests

from release.utils.buildinfo import BuildInfo
from release.utils.maven_central import download_artifacts_for_central, finalize, validate_before_promote


@pytest.fixture
def buildinfo():
    return BuildInfo({
        'buildInfo': {
            'statuses': [{'repository': 'sonarsource-public-qa'}],
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-maven:16.1.0.3465',
                'properties': {'artifactsToPublish': 'org.sonarsource.dummy:dummy-maven:jar'}
            }]
        }
    })


def _http_error(status, url=""):
    response = MagicMock(status_code=status, url=url)
    error = requests.HTTPError(response=response)
    return error


class TestDownloadArtifactsForCentral:

    @patch('release.utils.maven_central.shutil.move')
    def test_downloads_main_pom_sources_and_javadoc(self, mock_move, buildinfo, tmp_path):
        artifactory = MagicMock()
        artifactory.download_named.side_effect = (
            lambda repo, gid, aid, version, filename, checksums=None, optional_checksums=None:
            (f"/tmp/{filename}", ["asc"]))

        download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))

        calls = [c.args for c in artifactory.download_named.call_args_list]
        assert ('sonarsource-public-builds', 'org.sonarsource.dummy', 'dummy-maven', '16.1.0.3465',
                'dummy-maven-16.1.0.3465.jar') in calls
        assert ('sonarsource-public-builds', 'org.sonarsource.dummy', 'dummy-maven', '16.1.0.3465',
                'dummy-maven-16.1.0.3465.pom') in calls
        assert ('sonarsource-public-builds', 'org.sonarsource.dummy', 'dummy-maven', '16.1.0.3465',
                'dummy-maven-16.1.0.3465-sources.jar') in calls
        assert ('sonarsource-public-builds', 'org.sonarsource.dummy', 'dummy-maven', '16.1.0.3465',
                'dummy-maven-16.1.0.3465-javadoc.jar') in calls
        for call in artifactory.download_named.call_args_list:
            assert call.kwargs['checksums'] == ["md5", "sha1"]
            assert call.kwargs['optional_checksums'] == ["asc"]
        # 4 artifacts x (main file + md5 + sha1 + asc)
        assert mock_move.call_count == 16

    @patch('release.utils.maven_central.shutil.move')
    def test_places_downloaded_file_under_maven_layout(self, mock_move, buildinfo, tmp_path):
        artifactory = MagicMock()
        artifactory.download_named.return_value = ("/tmp/dummy-maven-16.1.0.3465.jar", ["asc"])

        download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))

        expected_dir = os.path.join(str(tmp_path), "org/sonarsource/dummy", "dummy-maven", "16.1.0.3465")
        assert os.path.isdir(expected_dir)
        moved_to = [c.args[1] for c in mock_move.call_args_list]
        assert all(m.startswith(expected_dir) for m in moved_to)

    def test_skips_missing_companion_files_without_raising(self, buildinfo, tmp_path):
        artifactory = MagicMock()

        def download_named(repo, gid, aid, version, filename, checksums=None, optional_checksums=None):
            if "sources" in filename or "javadoc" in filename:
                raise _http_error(404, url=f"https://repox/{filename}")
            return "/tmp/main.jar", []

        artifactory.download_named.side_effect = download_named
        with patch('release.utils.maven_central.shutil.move'):
            download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))  # must not raise

    def test_reraises_when_required_checksum_missing_but_main_file_exists(self, buildinfo, tmp_path):
        # The main jar exists in Repox but a required checksum 404s: must fail loudly rather than
        # silently drop the artifact from the Central bundle while it stays present in Repox.
        artifactory = MagicMock()
        artifactory.download_named.side_effect = _http_error(
            404, url="https://repox/dummy-maven-16.1.0.3465.jar.md5")

        with pytest.raises(requests.HTTPError):
            download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))

    def test_reraises_non_404_http_error(self, buildinfo, tmp_path):
        artifactory = MagicMock()
        artifactory.download_named.side_effect = _http_error(500, url="https://repox/dummy-maven-16.1.0.3465.jar")

        with pytest.raises(requests.HTTPError):
            download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))

    def test_no_artifacts_to_publish_is_a_noop(self, tmp_path):
        artifactory = MagicMock()
        empty_buildinfo = BuildInfo({'buildInfo': {'properties': {}, 'modules': [{}]}})

        download_artifacts_for_central(artifactory, empty_buildinfo, str(tmp_path))

        artifactory.download_named.assert_not_called()

    @patch('release.utils.maven_central.shutil.move')
    def test_excludes_artifact_matching_pattern(self, mock_move, tmp_path):
        # e.g. sonar-enterprise excludes its shaded scanner-engine jar from the Central sync.
        buildinfo = BuildInfo({
            'buildInfo': {
                'statuses': [{'repository': 'sonarsource-public-qa'}],
                'modules': [{
                    'id': 'org.sonarsource.dummy:dummy-maven:16.1.0.3465',
                    'properties': {
                        'artifactsToPublish':
                            'org.sonarsource.dummy:dummy-maven:jar,org.sonarsource.dummy:dummy-shaded:jar'
                    }
                }]
            }
        })
        artifactory = MagicMock()
        artifactory.download_named.return_value = ("/tmp/x", [])

        download_artifacts_for_central(artifactory, buildinfo, str(tmp_path), exclusions="*shaded*")

        aids_downloaded = {c.args[2] for c in artifactory.download_named.call_args_list}
        assert aids_downloaded == {"dummy-maven"}

    @patch('release.utils.maven_central.shutil.move')
    def test_excludes_using_semicolon_separated_path_pattern(self, mock_move, tmp_path):
        # JFrog-style ";"-separated patterns matched against the full Maven path must keep working.
        buildinfo = BuildInfo({
            'buildInfo': {
                'statuses': [{'repository': 'sonarsource-public-qa'}],
                'modules': [{
                    'id': 'org.sonarsource.dummy:dummy-maven:16.1.0.3465',
                    'properties': {
                        'artifactsToPublish':
                            'org.sonarsource.dummy:dummy-maven:jar,org.sonarsource.dummy:dummy-tool:nupkg'
                    }
                }]
            }
        })
        artifactory = MagicMock()
        artifactory.download_named.return_value = ("/tmp/x", [])

        download_artifacts_for_central(artifactory, buildinfo, str(tmp_path), exclusions="*.nupkg;*.snupkg")

        aids_downloaded = {c.args[2] for c in artifactory.download_named.call_args_list}
        assert aids_downloaded == {"dummy-maven"}

    def test_skips_non_public_group_ids(self, tmp_path):
        # com.sonarsource.* is commercial/private and must never reach a Central bundle.
        buildinfo = BuildInfo({
            'buildInfo': {
                'statuses': [{'repository': 'sonarsource-public-qa'}],
                'modules': [{
                    'id': 'org.sonarsource.dummy:dummy-maven:16.1.0.3465',
                    'properties': {
                        'artifactsToPublish':
                            'org.sonarsource.dummy:dummy-maven:jar,com.sonarsource.dummy:dummy-enterprise:jar'
                    }
                }]
            }
        })
        artifactory = MagicMock()
        artifactory.download_named.return_value = ("/tmp/x", [])

        with patch('release.utils.maven_central.shutil.move'):
            download_artifacts_for_central(artifactory, buildinfo, str(tmp_path))

        aids_downloaded = {c.args[2] for c in artifactory.download_named.call_args_list}
        assert aids_downloaded == {"dummy-maven"}

    @patch('release.utils.maven_central.shutil.move')
    def test_falls_back_to_public_builds_repo_when_no_statuses(self, mock_move, tmp_path):
        # multiRepoPromote builds (sonar-enterprise / slang-enterprise) have no statuses[0].repository.
        multirepo_buildinfo = BuildInfo({
            'buildInfo': {
                'modules': [{
                    'id': 'org.sonarsource.dummy:dummy-maven:16.1.0.3465',
                    'properties': {'artifactsToPublish': 'org.sonarsource.dummy:dummy-maven:jar'}
                }]
            }
        })
        artifactory = MagicMock()
        artifactory.download_named.return_value = ("/tmp/dummy-maven-16.1.0.3465.jar", [])

        download_artifacts_for_central(artifactory, multirepo_buildinfo, str(tmp_path))

        repos_used = {c.args[0] for c in artifactory.download_named.call_args_list}
        assert repos_used == {"sonarsource-public-builds"}


class TestValidateBeforePromote:

    @patch('release.utils.maven_central.subprocess.run')
    def test_success_returns_deployment_id(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        github_output = tmp_path / "output"
        github_output.write_text("deployment-id=abc-123\n")

        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(github_output)}):
            deployment_id = validate_before_promote("/repo", "https://central.example", "token", "name")

        assert deployment_id == "abc-123"
        args = mock_run.call_args.args[0]
        assert args[1:] == ["/repo", "https://central.example", "validate", ""]
        assert mock_run.call_args.kwargs['env']['CENTRAL_TOKEN'] == "token"
        assert mock_run.call_args.kwargs['env']['DEPLOYMENT_NAME'] == "name"

    @patch('release.utils.maven_central.subprocess.run')
    def test_failure_raises(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=1)
        github_output = tmp_path / "output"
        github_output.write_text("deployment-id=abc-123\n")

        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(github_output)}):
            with pytest.raises(RuntimeError):
                validate_before_promote("/repo", "https://central.example", "token", "name")

    @patch('release.utils.maven_central.subprocess.run')
    def test_success_without_deployment_id_raises(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        github_output = tmp_path / "output"
        github_output.write_text("")

        with patch.dict(os.environ, {'GITHUB_OUTPUT': str(github_output)}):
            with pytest.raises(RuntimeError):
                validate_before_promote("/repo", "https://central.example", "token", "name")


class TestFinalize:

    @patch('release.utils.maven_central.subprocess.run')
    def test_calls_script_in_finalize_mode(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        finalize("abc-123", "https://central.example", "token")

        args = mock_run.call_args.args[0]
        assert args[1:] == ["", "https://central.example", "finalize", "abc-123"]
        assert mock_run.call_args.kwargs['env']['CENTRAL_TOKEN'] == "token"

    @patch('release.utils.maven_central.subprocess.run')
    def test_failure_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)

        with pytest.raises(RuntimeError):
            finalize("abc-123", "https://central.example", "token")
