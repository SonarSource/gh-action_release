import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, ANY, call

import pytest
from parameterized import parameterized

from release.exceptions.invalid_input_parameters_exception import InvalidInputParametersException
from release.main import main, set_output, check_params, MANDATORY_ENV_VARIABLES
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.buildinfo import BuildInfo
from release.utils.github import GitHub


def test_set_output():
    with tempfile.NamedTemporaryFile(suffix="", prefix=os.path.basename(__file__)) as temp_file:
        os.environ['GITHUB_OUTPUT'] = temp_file.name

        set_output('function', 'output')

        assert temp_file.read().decode("utf-8").strip() == "function=output"


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
