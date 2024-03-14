from boto3 import Session


class AwsSsmParameterNotFound(Exception):
    pass


class AwsSsmParameterHelper:

    @staticmethod
    def get_ssm_parameter_value(aws_session: Session, parameter_name: str) -> str:
        parameter = aws_session.client('ssm').get_parameter(Name=parameter_name)

        if parameter['Name'] == parameter_name:
            value = parameter['Value']
            return value
        else:
            raise AwsSsmParameterNotFound('Could not retrieve ssm parameter value for parameter name={}'.format(parameter_name))
