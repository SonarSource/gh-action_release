from boto3 import Session


class AwsSsmParameterNotFound(Exception):
    pass


class AwsSsmParameterHelper:

    @staticmethod
    def get_ssm_parameter_value(aws_session: Session, parameter_name: str) -> str:
        return aws_session.client('ssm').get_parameter(Name=parameter_name)['Parameter']['Value']

