import uuid
import boto3
from boto3 import Session
from dryable import Dryable
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.aws_ssm_parameter_helper import AwsSsmParameterHelper
from release.utils.version_helper import VersionHelper
from release.vars import releasability_aws_region, releasability_env_type

RELEASABILITY_SSM_PARAMETER_NAME_PREFIX = "/Burgr/Releasability/"
RELEASABILITY_SSM_PARAMETER_NAME_TRIGGER_TOPIC_SUFFIX = "/ReleasabilityTriggerArn"
RELEASABILITY_SSM_PARAMETER_NAME_RESULT_TOPIC_SUFFIX = "/ReleasabilityResultArn"
RELEASABILITY_SSM_PARAMETER_NAME_RESULT_QUEUE_SUFFIX = "/ReleasabilityResultQueueArn"


class Releasability:
    release_request: ReleaseRequest
    session: Session

    def __init__(self, release_request):
        self.release_request = release_request
        self.session = boto3.Session(region_name=releasability_aws_region)

        self.TRIGGER_TOPIC_ARN = self._get_trigger_topic_arn(releasability_env_type)
        self.RESULT_TOPIC_ARN = self._get_result_topic_arn(releasability_env_type)
        self.RESULT_QUEUE_ARN = self._get_result_queue_arn(releasability_env_type)

    @Dryable(logging_msg="{function}()")
    def _get_trigger_topic_arn(self, env_type: str):
        sns_input_arn_parameter_name = f"{RELEASABILITY_SSM_PARAMETER_NAME_PREFIX}{env_type}{RELEASABILITY_SSM_PARAMETER_NAME_TRIGGER_TOPIC_SUFFIX}"
        return AwsSsmParameterHelper.get_ssm_parameter_value(
            self.session, sns_input_arn_parameter_name
        )

    @Dryable(logging_msg="{function}()")
    def _get_result_topic_arn(self, env_type: str):
        sns_output_arn_parameter_name = f"{RELEASABILITY_SSM_PARAMETER_NAME_PREFIX}{env_type}{RELEASABILITY_SSM_PARAMETER_NAME_RESULT_TOPIC_SUFFIX}"
        return AwsSsmParameterHelper.get_ssm_parameter_value(
            self.session, sns_output_arn_parameter_name
        )

    @Dryable(logging_msg="{function}()")
    def _get_result_queue_arn(self, env_type: str):
        sns_output_arn_parameter_name = f"{RELEASABILITY_SSM_PARAMETER_NAME_PREFIX}{env_type}{RELEASABILITY_SSM_PARAMETER_NAME_RESULT_QUEUE_SUFFIX}"
        return AwsSsmParameterHelper.get_ssm_parameter_value(
            self.session, sns_output_arn_parameter_name
        )
    def start_releasability_checks(self):
        standardized_version = VersionHelper.as_standardized_version(self.release_request)

        print(f"Starting releasability check: {self.release_request.project}#{standardized_version}")

        correlation_id = str(uuid.uuid4())
        sns_request = self._build_sns_request(
            correlation_id=correlation_id,
            organization=self.release_request.org,
            project_name=self.release_request.project,
            branch_name=self.release_request.branch,
            version=standardized_version,
            revision=self.release_request.sha,
            build_number=int(self.release_request.buildnumber)
        )

        response = self.session.client("sns").publish(
            TopicArn=self.TRIGGER_TOPIC_ARN,
            Message=str(sns_request),
        )
        print(f"Issued SNS message {response['MessageId']}; the request identifier is {correlation_id}")
        return correlation_id

    def _build_sns_request(self,
                           correlation_id: str,
                           organization: str,
                           project_name: str,
                           branch_name: str,
                           revision: str,
                           version: str,
                           build_number: int):
        sns_request = {
            'uuid': correlation_id,
            'responseToARN': self.RESULT_TOPIC_ARN,
            'repoSlug': f'{organization}/{project_name}',
            'version': version,
            'vcsRevision': revision,
            'artifactoryBuildNumber': build_number,
            'branchName': branch_name
        }
        return sns_request
