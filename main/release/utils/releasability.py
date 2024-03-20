import uuid
import boto3
import json
from boto3 import Session
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.version_helper import VersionHelper
from release.vars import releasability_aws_region


class ReleasabilityException(Exception):
    pass


class CheckResult:
    check_name: str
    check_state: str
    error_message: str

    def __init__(self, check_name: str, check_state: str, error_message: str = None):
        self.check_name = check_name
        self.check_state = check_state
        self.error_message = error_message


class CheckResults:
    EMOJI_CHECK = "\u2713"
    EMOJI_SUCCESS = "\u2705"
    EMOJI_FAILURE = "\u274c"

    def __init__(self):
        self.results = []
        self.status = True

    def add_result(self, check_name: str, check_state: str, error_message: str = None):
        self.results.append(CheckResult(check_name, check_state, error_message))

    def process_result(self, result: CheckResult) -> tuple[bool, str, str]:
        if result.check_state == 'PASSED':
            return True, self.EMOJI_SUCCESS, None
        if result.check_state == 'NOT_RELEVANT':
            return True, self.EMOJI_CHECK, None
        return False, self.EMOJI_FAILURE, result.error_message

    def get_formatted_results(self) -> str:
        formatted_result = []
        for r in self.results:
            check_status, emoji, error_message = self.process_result(r)
            if not check_status:
                self.status = False
            check_result = f'{emoji} {r.check_name}'
            check_result += f' - {error_message}' if error_message else ''
            formatted_result.append(check_result)
        return '\n'.join(formatted_result)


class Releasability:
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
        self.TRIGGER_TOPIC_ARN = f"arn:aws:sns:{aws_region}:{aws_account_id}:ReleasabilityTriggerTopic"
        self.RESULT_TOPIC_ARN = f"arn:aws:sns:{aws_region}:{aws_account_id}:ReleasabilityResultTopic"
        self.RESULT_QUEUE_ARN = f"arn:aws:sqs:{aws_region}:{aws_account_id}:ReleasabilityResultQueue"

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

    def _arn_to_url(self, arn):
        parts = arn.split(':')
        return 'https://sqs.' + parts[3] + '.amazonaws.com/' + parts[4] + '/' + parts[5]

    def get_releasability_status(self, correlation_id: str):
        results = CheckResults()
        remaining_messages, remaining_time = self._get_checks_count_and_max_timeout()
        sqs = self.session.client('sqs')
        queue_url = self._arn_to_url(self.RESULT_QUEUE_ARN)
        while remaining_messages > 0 and remaining_time > 0:
            remaining_time -= 1
            messages = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=1,
            )
            if 'Messages' in messages:
                for message in messages['Messages']:
                    body = json.loads(message['Body'])
                    content = json.loads(body['Message'])
                    # Filter relevant messages to this correlation_id
                    if content["requestUUID"] == correlation_id:
                        check_result = content["type"]
                        # Skip check acknowledgement messages
                        if check_result != "ACK":
                            remaining_messages -= 1
                            error_message = ""
                            if "message" in content:
                                results.status = False
                                error_message = content["message"]
                            results.add_result(content["checkName"], check_result, error_message)
        print(results.get_formatted_results())
        if not results.status:
            raise ReleasabilityException(f"Releasability checks failed")

    def _get_checks_count_and_max_timeout(self) -> tuple[int, int]:
        # Get lambdas
        lambda_client = self.session.client('lambda')
        function_response = lambda_client.list_functions()
        functions = function_response['Functions']
        while 'NextMarker' in function_response:
            function_response = lambda_client.list_functions(Marker=function_response['NextMarker'])
            functions += function_response['Functions']

        # Get all subscriptions to the input SNS topic
        sns = self.session.client('sns')
        sns_response = sns.list_subscriptions_by_topic(TopicArn=self.TRIGGER_TOPIC_ARN)
        subscriptions = sns_response['Subscriptions']
        while 'NextToken' in sns_response:
            sns_response = sns.list_subscriptions_by_topic(TopicArn=self.TRIGGER_TOPIC_ARN, NextToken=sns_response['Subscriptions'])
            subscriptions += sns_response['Subscriptions']
        subscriptions_endpoint_arn = [d['Endpoint'] for d in subscriptions]

        # Get all checks that are subscribed to the input SNS topic
        checks = [check for check in functions if check['FunctionArn'] in subscriptions_endpoint_arn]
        checks_count = len(checks)

        # Get the timeout of the lambdas
        functions_timeout = [check['Timeout'] for check in functions]
        max_function_timeout = max(functions_timeout)

        return checks_count, max_function_timeout
