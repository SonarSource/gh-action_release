import ast
import unittest

from unittest.mock import patch, MagicMock

from release.steps.ReleaseRequest import ReleaseRequest
from release.releasability.releasability import Releasability


class ReleasabilityTest(unittest.TestCase):

    def test_build_sns_request_should_assign_correctly_properties(self):
        session = MagicMock()
        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            uuid = "42f23-3232-3232-32232"

            request = releasability._build_sns_request(
                correlation_id=uuid,
                organization=organization,
                project_name=project_name,
                branch_name=branch_name,
                version=version,
                revision=sha,
                build_number=build_number
            )

            assert request['uuid'] == uuid
            assert request['responseToARN'] is not None
            assert request['repoSlug'] == "sonar/sonar-dummy"
            assert request['version'] == version
            assert request['vcsRevision'] == sha
            assert request['artifactoryBuildNumber'] == build_number
            assert request['branchName'] == branch_name

    def test_start_releasability_checks_should_invoke_publish(self):
        session = MagicMock()
        mocked_sns_client = MagicMock()
        session.client.return_value = mocked_sns_client

        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            releasability.start_releasability_checks()

            assert mocked_sns_client.publish.call_count == 1
            sns_query_content = ast.literal_eval(mocked_sns_client.publish.call_args[1]['Message'])
            assert sns_query_content['responseToARN'] is not None
            assert sns_query_content['vcsRevision'] == sha

    def test_start_releasability_checks_should_return_a_correlation_id_after_invokation(self):
        session = MagicMock()
        mocked_sns_client = MagicMock()
        session.client.return_value = mocked_sns_client

        with patch('boto3.Session', return_value=session):
            organization = "sonar"
            project_name = "sonar-dummy"
            version = "5.4.3"
            sha = "434343443efdcaaa123232"
            build_number = 42
            branch_name = "feat/some"

            release_request = ReleaseRequest(organization, project_name, version, build_number, branch_name, sha)
            releasability = Releasability(release_request)

            correlation_id = releasability.start_releasability_checks()

            assert correlation_id is not None

    def test_arn_to_sqs_url_should_return_expected_url_given_a_valid_sqs_arn(self):
        region = "us-east-1"
        account_number = "123456789012"
        queue_name = "great-project/great"
        arn = f"arn:aws:sqs:{region}:{account_number}:{queue_name}"

        sqs_url = Releasability._arn_to_sqs_url(arn)

        self.assertEquals(sqs_url, f"https://sqs.{region}.amazonaws.com/{account_number}/{queue_name}")

    def test_arn_to_sqs_url_should_return_expected_url_given_an_invalid_arn(self):
        region = "us-east-1"
        account_number = "123456789012"
        queue_name = "great-project/great"
        arn = f"arn:aws:invalid:{region}:{account_number}:{queue_name}"

        self.assertRaises(ValueError, lambda: Releasability._arn_to_sqs_url(arn))
