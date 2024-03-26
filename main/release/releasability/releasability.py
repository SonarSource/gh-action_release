import uuid
import time

import boto3
import json
from boto3 import Session
from dryable import Dryable

from release.releasability.releasability_check_result import ReleasabilityCheckResult
from release.releasability.releasability_checks_report import ReleasabilityChecksReport
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.timeout import has_exceeded_timeout
from release.utils.version_helper import VersionHelper
from release.vars import releasability_aws_region


class ReleasabilityException(Exception):
    pass


class CouldNotRetrieveReleasabilityCheckResultsException(ReleasabilityException):
    pass


class Releasability:
    SQS_MAX_POLLED_MESSAGES_AT_A_TIME = 10
    SQS_POLL_WAIT_TIME = 10
    FETCH_CHECK_RESULT_TIMEOUT_SECONDS = 60 * 5
    FETCH_SLEEP_TIME_SECONDS = 2

    ARN_SNS = 'arn:aws:sns'
    ARN_SQS = 'arn:aws:sqs'

    release_request: ReleaseRequest
    session: Session

    def __init__(self, release_request):
        self.release_request = release_request
        self.session = boto3.Session(region_name=releasability_aws_region)
        account_id = self._get_aws_account_id()
        self._define_arn_constants(releasability_aws_region, account_id)

    @Dryable(logging_msg='{function}({args}{kwargs})')
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

        check_results = self._get_check_results(correlation_id)
        return ReleasabilityChecksReport(check_results)

    def _get_check_results(self, correlation_id: str):
        filters = self._build_filters(correlation_id)

        expected_message_count = self._get_checks_count()
        received_message_count = 0
        received_check_results = list[ReleasabilityCheckResult]()

        now = time.time()
        while (received_message_count < expected_message_count
               and not has_exceeded_timeout(now, Releasability.FETCH_CHECK_RESULT_TIMEOUT_SECONDS)):
            filtered_messages = self._fetch_filtered_check_results(filters)

            for message_payload in filtered_messages:
                received_message_count += 1

                received_check_results.append(
                    ReleasabilityCheckResult(
                        message_payload["checkName"],
                        message_payload["type"],
                        message_payload["message"] if "message" in message_payload else None
                    )
                )

            time.sleep(Releasability.FETCH_SLEEP_TIME_SECONDS)

        if expected_message_count == received_message_count:
            return received_check_results
        else:
            raise CouldNotRetrieveReleasabilityCheckResultsException(
                f'Received {received_message_count}/{expected_message_count} check result messages within '
                f'allowed time ({Releasability.FETCH_CHECK_RESULT_TIMEOUT_SECONDS} seconds)')

    @staticmethod
    def _build_filters(correlation_id: str) -> []:
        def match_correlation_id(msg):
            return msg['requestUUID'] == correlation_id

        def not_an_ack_message(msg):
            return msg['type'] != 'ACK'

        return [lambda x: match_correlation_id(x), lambda x: not_an_ack_message(x)]

    def _fetch_filtered_check_results(self, filters: []) -> list:
        unfiltered_messages = self._fetch_check_results()
        return list(filter(lambda msg: all(f(msg) for f in filters), unfiltered_messages))

    def _fetch_check_results(self) -> list:

        sqs_client = self.session.client('sqs')
        sqs_queue_url = self._arn_to_sqs_url(self.RESULT_QUEUE_ARN)

        sqs_queue_messages = sqs_client.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=Releasability.SQS_MAX_POLLED_MESSAGES_AT_A_TIME,
            WaitTimeSeconds=Releasability.SQS_POLL_WAIT_TIME,
        )

        result = []

        for json_message in sqs_queue_messages['Messages']:
            body = json.loads(json_message['Body'])
            content = json.loads(body['Message'])
            result.append(content)

        return result

    def _get_checks(self) -> list[str]:
        sns_client = self.session.client('sns')
        sns_response = sns_client.list_subscriptions_by_topic(TopicArn=self.TRIGGER_TOPIC_ARN)
        subscriptions = sns_response['Subscriptions'] # Caveat: maximum number of subscriptions returned by AWS in a single call is 100

        checks = [subscription['Endpoint'].split(':')[-1] for subscription in subscriptions]

        return checks

    def _get_checks_count(self):
        return len(self._get_checks())
