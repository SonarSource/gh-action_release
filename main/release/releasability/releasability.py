import uuid
import boto3
import json
from boto3 import Session
from dryable import Dryable

from release.releasability.releasability_check_result import ReleasabilityCheckResult
from release.releasability.releasability_checks_report import ReleasabilityChecksReport
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.version_helper import VersionHelper
from release.vars import releasability_aws_region


class ReleasabilityException(Exception):
    pass


class Releasability:
    SQS_MAX_POLLED_MESSAGES_AT_A_TIME = 10
    SQS_POLL_WAIT_TIME = 5

    ARN_SNS = 'arn:aws:sns'
    ARN_SQS = 'arn:aws:sqs'

    release_request: ReleaseRequest
    session: Session

    def __init__(self, release_request):
        self.release_request = release_request
        self.session = boto3.Session(region_name=releasability_aws_region)
        account_id = self._get_aws_account_id
        self._define_arn_constants(releasability_aws_region, account_id)

    def _get_aws_account_id(self) -> str:
        return boto3.client('sts').get_caller_identity().get('Account')

    def _define_arn_constants(self, aws_region: str, aws_account_id: str):
        self.TRIGGER_TOPIC_ARN = f"{Releasability.ARN_SNS}:{aws_region}:{aws_account_id}:ReleasabilityTriggerTopic"
        self.RESULT_TOPIC_ARN = f"{Releasability.ARN_SNS}:{aws_region}:{aws_account_id}:ReleasabilityResultTopic"
        self.RESULT_QUEUE_ARN = f"{Releasability.ARN_SQS}:{aws_region}:{aws_account_id}:ReleasabilityResultQueue"

    @Dryable(logging_msg='{function}({args}{kwargs})')
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

    """
    This method is responsible to return an SQS queue url based on an arn.
    More details about SQS urls can be found here: 
    https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-message-identifiers.html
    """
    @staticmethod
    def _arn_to_sqs_url(arn):
        parts = arn.split(':')
        service = parts[2]

        if service != "sqs":
            raise ValueError(f"Invalid sqs ARN: {arn}")

        region = parts[3]
        account_number = parts[4]
        queue_name = parts[5]
        return f'https://sqs.{region}.amazonaws.com/{account_number}/{queue_name}'

    def get_releasability_report(self, correlation_id: str) -> ReleasabilityChecksReport:
        report = ReleasabilityChecksReport()

        sqs_queue_url = self._arn_to_sqs_url(self.RESULT_QUEUE_ARN)

        remaining_messages, remaining_time = self._get_checks_count_and_max_timeout()  # TODO: what is that ? looks weird
        while remaining_messages > 0 and remaining_time > 0: # TODO: use a timeout
            messages = self._poll_releasability_queue(sqs_queue_url, Releasability.SQS_MAX_POLLED_MESSAGES_AT_A_TIME, Releasability.SQS_POLL_WAIT_TIME)

            def match_correlation_id(msg): return msg['requestUUID'] == correlation_id
            def not_an_ack_message(msg): return msg['type'] != 'ACK'
            filters = (match_correlation_id, not_an_ack_message)
            filtered_messages = filter(lambda msg: all(f(msg) for f in filters), messages)

            for message_content in filtered_messages:
                remaining_messages -= 1

                report.add_check(
                    ReleasabilityCheckResult(
                        message_content["checkName"],
                        message_content["type"],
                        message_content["message"] or None
                    )
                )

        return report

    def _poll_releasability_queue(self, queue_url: str, max_results: int, wait_time: int) -> list:
        sqs_client = self.session.client('sqs')

        sqs_queue_messages = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_results,
            WaitTimeSeconds=wait_time,
        )

        result = []

        for json_message in sqs_queue_messages['Messages']:
            body = json.loads(json_message['Body'])
            content = json.loads(body['Message'])
            result.append(content)

        return result

    def _get_checks_count_and_max_timeout(self) -> tuple[int, int]:  # TODO: looks weird, is that really the "clean way" of doing that in python ?
        # Get lambdas
        lambda_client = self.session.client('lambda')
        function_response = lambda_client.list_functions()
        functions = function_response['Functions']
        while 'NextMarker' in function_response:
            function_response = lambda_client.list_functions(Marker=function_response['NextMarker'])
            functions += function_response['Functions']

        # Get all subscriptions to the input SNS topic
        sns_client = self.session.client('sns')
        sns_response = sns_client.list_subscriptions_by_topic(TopicArn=self.TRIGGER_TOPIC_ARN)
        subscriptions = sns_response['Subscriptions']
        while 'NextToken' in sns_response:
            sns_response = sns_client.list_subscriptions_by_topic(TopicArn=self.TRIGGER_TOPIC_ARN, NextToken=sns_response['Subscriptions'])
            subscriptions += sns_response['Subscriptions']
        subscriptions_endpoint_arn = [d['Endpoint'] for d in subscriptions]

        # Get all checks that are subscribed to the input SNS topic
        checks = [check for check in functions if check['FunctionArn'] in subscriptions_endpoint_arn]
        checks_count = len(checks)

        # Get the timeout of the lambdas
        functions_timeout = [check['Timeout'] for check in functions]
        max_function_timeout = max(functions_timeout)

        return checks_count, max_function_timeout
