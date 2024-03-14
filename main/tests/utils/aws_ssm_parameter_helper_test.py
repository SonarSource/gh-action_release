import unittest
from unittest.mock import MagicMock, patch

from release.utils.aws_ssm_parameter_helper import AwsSsmParameterHelper, AwsSsmParameterNotFound


class AwsSsmParameterHelperTest(unittest.TestCase):

    def test_get_ssm_parameter_value_should_return_arn_given_it_receives_a_valid_result(self):
        parameter_name = "some param"
        parameter_value = "arn:aws:ssm:us-east-1:whatever"

        session = MagicMock()
        session.client("ssm").get_parameter.return_value = {
                    "Name": parameter_name,
                    "Value": parameter_value
        }
        with patch('boto3.session', return_value=session):
            result = AwsSsmParameterHelper.get_ssm_parameter_value(session, parameter_name)

            assert result == parameter_value

    def test_get_ssm_parameter_value_should_throw_an_exception_given_it_could_not_find_it(self):
        parameter_name = "some param"

        session = MagicMock()
        session.client("ssm").get_parameters.return_value = {
            "Parameters": []
        }
        with ((patch('boto3.session', return_value=session))):
            self.assertRaises(AwsSsmParameterNotFound,
                              AwsSsmParameterHelper.get_ssm_parameter_value,
                              session,
                              parameter_name
                              )
