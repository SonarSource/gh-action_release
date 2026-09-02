import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, ANY, call

import pytest
from parameterized import parameterized

from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.main import (
    abort_release, check_params, is_maven_central_sync_enabled, main, set_output, MANDATORY_ENV_VARIABLES)
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.buildinfo import BuildInfo
from release.utils.github import GitHub


def test_set_output():
    with tempfile.NamedTemporaryFile(suffix="", prefix=os.path.basename(__file__)) as temp_file:
        os.environ['GITHUB_OUTPUT'] = temp_file.name

        set_output('function', 'output')

        assert temp_file.read().decode("utf-8").strip() == "function=output"


@patch('release.main.revoke_release')
@patch('release.main.set_output')
@patch.object(GitHub, 'revoke_release')
def test_abort_release_logs_error_and_revokes_artifacts(mock_github_revoke, mock_set_output, mock_revoke_release):
    """abort_release must print the immutability-safe error, call github.revoke_release,
    revoke JFrog/S3 artifacts, and set the 'release' output."""
    release_request = ReleaseRequest('org', 'project', 'version', '42', 'branch', 'sha')
    github = GitHub.__new__(GitHub)
    artifactory = Artifactory.__new__(Artifactory)
    binaries = Binaries.__new__(Binaries)

    abort_release(github, artifactory, binaries, release_request)

    mock_github_revoke.assert_called_once()
    mock_revoke_release.assert_called_once_with(artifactory, binaries, release_request)
    mock_set_output.assert_called_once_with("release", "project:42 aborted")


class MainTest(unittest.TestCase):

    @patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
    @patch('release.main.check_params')
    @patch('release.utils.github.json.load')
    @patch('release.main.notify_slack')
    @patch.object(GitHub, 'revoke_release')
    @patch.object(sys, 'exit')
    def test_releasability_failure(self,
                                   sys_exit,
                                   github_revoke_release,
                                   notify_slack,
                                   check_params,
                                   github_event):
        with patch('release.utils.github.open', mock_open()) as open_mock:
            release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
            with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
                with pytest.raises(Exception):
                    main()
                    check_params.assert_called_once()
                    open_mock.assert_called_once()
                    github_event.assert_called_once()
                    github_release_request.assert_called_once()
                    notify_slack.assert_called_once_with('"Released project:version failed')
                    github_revoke_release.assert_called_once()

    @patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'release'}, clear=True)
    @patch('release.main.check_params')
    @patch('release.utils.github.json.load')
    @patch('release.main.notify_slack')
    @patch.object(GitHub, 'revoke_release')
    @patch.object(sys, 'exit')
    def test_releasability_failure(self,
                                   sys_exit,
                                   github_revoke_release,
                                   notify_slack,
                                   check_params,
                                   github_event):
        with patch('release.utils.github.open', mock_open()) as open_mock:
            release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
            with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
                with pytest.raises(Exception):
                    main()
                    check_params.assert_called_once()
                    open_mock.assert_called_once()
                    github_event.assert_called_once()
                    github_release_request.assert_called_once()
                    notify_slack.assert_called_once_with('"Released project:version failed')
                    github_revoke_release.assert_called_once()

    @patch.dict(os.environ, {
        'GITHUB_EVENT_NAME': 'release',
        'ARTIFACTORY_ACCESS_TOKEN': 'mockAccessTokenValue',
    }, clear=True)
    @patch('release.utils.github.json.load')
    @patch.object(Artifactory, 'receive_build_info')
    @patch.object(Artifactory, 'promote')
    @patch.object(GitHub, 'is_publish_to_binaries', return_value=True)
    @patch.object(GitHub, 'revoke_release')
    @patch('release.main.notify_slack')
    @patch('release.main.set_output')
    @patch('release.main.check_params')
    @patch.object(sys, 'exit')
    def test_main_happy_path(self,
                             sys_exit,
                             check_params,
                             set_output,
                             notify_slack,
                             github_revoke_release,
                             github_is_publish_to_binaries,
                             artifactory_promote,
                             artifactory_receive_build_info,
                             github_event):
        with patch('release.utils.github.open', mock_open()) as open_mock:
            release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
            with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
                main()
                check_params.assert_called_once()
                open_mock.assert_called_once()
                github_event.assert_called_once()
                github_release_request.assert_called_once()
                artifactory_receive_build_info.assert_called_once_with(release_request)
                artifactory_promote.assert_called_once_with(release_request, ANY)
                github_is_publish_to_binaries.assert_called_once()
                notify_slack.assert_called_once_with('Successfully released project:version')
                set_output.assert_has_calls([call('promote', 'done'), call('publish_to_binaries', 'done')])

    @patch.dict(os.environ, {
        'GITHUB_EVENT_NAME': 'release',
        'ARTIFACTORY_ACCESS_TOKEN': 'mockArtifactoryAccessToken'
    }, clear=True)
    @patch('release.main.check_params')
    @patch('release.utils.github.json.load')
    @patch.object(Artifactory, 'receive_build_info')
    @patch.object(Artifactory, 'promote', side_effect=Exception('exception'))
    @patch('release.main.notify_slack')
    @patch('release.main.abort_release')
    def test_promotion_failure(self,
                               abort_release,
                               notify_slack,
                               check_params,
                               artifactory_promote,
                               artifactory_receive_build_info,
                               github_event):
        with patch('release.utils.github.open', mock_open()) as open_mock:
            release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
            with patch.object(GitHub, 'get_release_request', return_value=release_request) as github_release_request:
                with pytest.raises(Exception):
                    main()
                    check_params.assert_called_once()
                    open_mock.assert_called_once()
                    github_event.assert_called_once()
                    github_release_request.assert_called_once()
                    artifactory_receive_build_info.assert_called_once_with(release_request)
                    artifactory_promote.assert_called_once_with(release_request, ANY)
                    notify_slack.assert_called_once_with('"Released project:version failed')
                    abort_release(ANY, ANY, ANY, release_request)

    @parameterized.expand([
        "ARTIFACTORY_ACCESS_TOKEN"
    ])
    def test_check_params_should_raise_an_exception_given_a_mandatory_env_variable_is_not_provided(self, parameter_not_provided):
        for variable_name in MANDATORY_ENV_VARIABLES:
            os.environ[variable_name] = "some value"
        del os.environ[parameter_not_provided]
        with self.assertRaises(InvalidInputParametersException):
            check_params()

    def test_check_params_should_raise_an_exception_given_slack_channel_is_provided_and_slack_token_is_not(self):
        for variable_name in MANDATORY_ENV_VARIABLES:
            os.environ[variable_name] = "some value"
        os.environ["INPUT_SLACK_CHANNEL"] = "some channel"
        # ensure slack api token is not provided:
        os.environ["SLACK_API_TOKEN"] = ""
        del os.environ["SLACK_API_TOKEN"]
        with self.assertRaises(InvalidInputParametersException):
            check_params()

    def test_check_params_should_raise_an_exception_given_publish_to_binaries_is_true_and_missing_params(self):
        for variable_name in MANDATORY_ENV_VARIABLES:
            os.environ[variable_name] = "some value"
        os.environ["INPUT_PUBLISH_TO_BINARIES"] = "true"
        # ensure binaries_aws_deploy is not provided:
        os.environ["BINARIES_AWS_DEPLOY"] = ""
        del os.environ["BINARIES_AWS_DEPLOY"]
        with self.assertRaises(InvalidInputParametersException) as context:
            check_params()
        self.assertEqual(str(context.exception), """The execution were aborted due to the following error(s):
env BINARIES_AWS_DEPLOY is empty but required as INPUT_PUBLISH_TO_BINARIES is true
buildInfo.env.ARTIFACTORY_DEPLOY_REPO is required as INPUT_PUBLISH_TO_BINARIES is true
If needed, please contact the Engineering Experience squad.""")

    @patch.dict(os.environ, {'INPUT_MAVEN_CENTRAL_SYNC': 'true', 'INPUT_DRY_RUN': 'true'}, clear=True)
    def test_is_maven_central_sync_enabled_false_in_dry_run(self):
        # A dry run never fetches CENTRAL_TOKEN (main.yaml gates that Vault step on dryRun != true),
        # so this must stay disabled even when the input flag is true.
        assert is_maven_central_sync_enabled() is False

    @patch.dict(os.environ, {'INPUT_MAVEN_CENTRAL_SYNC': 'true'}, clear=True)
    def test_is_maven_central_sync_enabled_true_outside_dry_run(self):
        assert is_maven_central_sync_enabled() is True

    @patch.dict(os.environ, {
        'GITHUB_EVENT_NAME': 'release',
        'ARTIFACTORY_ACCESS_TOKEN': 'mockArtifactoryAccessToken',
        'INPUT_MAVEN_CENTRAL_SYNC': 'true',
        'CENTRAL_TOKEN': 'mockCentralToken',
    }, clear=True)
    @patch('release.main.check_params')
    @patch('release.utils.github.json.load')
    @patch.object(Artifactory, 'receive_build_info')
    @patch.object(Artifactory, 'promote')
    @patch.object(GitHub, 'is_publish_to_binaries', return_value=False)
    @patch('release.main.download_artifacts_for_central')
    @patch('release.main.validate_before_promote', return_value='deployment-123')
    @patch('release.main.finalize', side_effect=RuntimeError('publish failed'))
    @patch('release.main.notify_slack')
    @patch('release.main.abort_release')
    @patch('release.main.set_output')
    def test_finalize_failure_after_promotion_does_not_revoke(self,
                                                               set_output,
                                                               abort_release_mock,
                                                               notify_slack,
                                                               finalize_mock,
                                                               validate_before_promote_mock,
                                                               download_artifacts_mock,
                                                               github_is_publish_to_binaries,
                                                               artifactory_promote,
                                                               artifactory_receive_build_info,
                                                               github_event,
                                                               check_params):
        """A finalize() failure after Repox promotion must exit without calling abort_release —
        un-promoting Repox at that point would fight an already-irreversible Central publish."""
        with patch('release.utils.github.open', mock_open()):
            release_request = ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')
            with patch.object(GitHub, 'get_release_request', return_value=release_request):
                with pytest.raises(SystemExit):
                    main()

        artifactory_promote.assert_called_once()
        finalize_mock.assert_called_once_with('deployment-123', ANY, 'mockCentralToken')
        abort_release_mock.assert_not_called()
        assert call('maven_central_deployment_id', ANY) not in set_output.call_args_list

    def test_check_params_should_not_raise_an_exception_given_valid_inputs(self):
        for variable_name in MANDATORY_ENV_VARIABLES:
            os.environ[variable_name] = "some value"
        os.environ["INPUT_SLACK_CHANNEL"] = "some channel"
        os.environ["SLACK_API_TOKEN"] = "some channel"
        os.environ["INPUT_PUBLISH_TO_BINARIES"] = "true"
        os.environ["BINARIES_AWS_DEPLOY"] = "bin"
        try:
            check_params(BuildInfo({
                'buildInfo': {
                    'properties': {'buildInfo.env.ARTIFACTORY_DEPLOY_REPO': 'deploy-repo-qa'},
                    'modules': [{}]
                }
            }))
        except InvalidInputParametersException:
            self.fail("check_params() raised an Exception")
