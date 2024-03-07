import boto3
import json
import uuid
import logging
import sys
from botocore.exceptions import ClientError
from dryable import Dryable

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class PendingReleasability:

    class Check(object):

        def __init__(self, type, message=None):
            self.type = type
            self.message = message

        def get_status_and_formatted_result(self) -> tuple:
            if self.type in 'PASSED':
                return True, '\u2705', None
            if self.type == 'NOT_RELEVANT':
                return True, '\u2713', None
            return False, '\u274c', self.message

    def __init__(self, uuid, checks_count, timeout):
        self.uuid = uuid
        self.checks = {}
        self.checks_count = checks_count
        self.timeout = timeout

    def process_notification(self, message):
        msg = json.loads(message['Message'])
        if msg['requestUUID'] == self.uuid:
            check_type = msg['type']
            if check_type != 'ACK':
                if 'message' in msg:
                    check = self.Check(check_type, msg['message'])
                else:
                    check = self.Check(check_type)
                self.checks[msg['checkName']] = check

    def is_terminated(self):
        if not self.checks:
            return False
        if not len(self.checks) == self.checks_count:
            return False
        return True

    def get_status_and_formatted_result(self):
        status = True
        formatted_result = []
        for check_name, check in self.checks.items():
            check_status, emoji, message = check.get_status_and_formatted_result()
            if not check_status:
                status = False
            check_result = f'{emoji} {check_name}'
            check_result += f' - {message}' if message else ''
            formatted_result.append(check_result)
        return status, '\n'.join(formatted_result)


class Releasability:

    def __init__(self, env_type, release_request):
        self.session = boto3.Session(region_name='eu-west-1')
        self.env_type = env_type
        self.release_request = release_request
        self.trigger_topic_arn, self.result_topic_arn, self.result_queue_arn = self._get_input_and_output_topics_arn()
        logger.warn('Initializing Releasability')

    @Dryable(logging_msg='{function}({args})')
    def check(self, version, branch, git_sha1):
        # SLVSCODE-specific
        if self.release_request.project == 'sonarlint-vscode':
            version = version.split('+')[0]

        releasability_id = self._start_releasability(version, git_sha1, branch)
        checks_count, timeout = self._get_checks_count_and_max_timeout()
        pending_releasability = PendingReleasability(releasability_id, checks_count, timeout)
        try:
            status, result = self._get_releasability_status(pending_releasability)
            print(result)
        except Exception as e:
            raise e
        if not status:
            sys.exit(1)

    def _start_releasability(self, version, revision, branch_name=None, pr_number=None):

        releasability_id = str(uuid.uuid4())
        sns_request = {
            'uuid': releasability_id,
            'responseToARN': self.result_topic_arn,
            'repoSlug': f'{self.release_request.org}/{self.release_request.project}',
            'version': version,
            'vcsRevision': revision,
            'artifactoryBuildNumber': int(self.release_request.buildnumber)
        }
        if branch_name:
            sns_request['branchName'] = branch_name
        if pr_number:
            sns_request['prNumber'] = pr_number
        response = self.session.client('sns').publish(
            TopicArn=self.trigger_topic_arn,
            Message=str(sns_request),
        )
        logger.info(f"Issued SNS message {response['MessageId']}; the request identifier is {releasability_id}")
        return releasability_id


    def _arn_to_url(self, arn):
        parts = arn.split(':')
        return 'https://sqs.' + parts[3] + '.amazonaws.com/' + parts[4] + '/' + parts[5]


    def _get_releasability_status(self, pending_releasability: PendingReleasability):
        sqs = self.session.resource('sqs')
        queue_url = self._arn_to_url(self.result_queue_arn)
        queue = sqs.Queue(queue_url)
        more_messages = True
        i = pending_releasability.timeout
        while more_messages and i > 0:
            i -= 1
            messages = _receive_messages(queue, 10, 1)
            for msg in messages:
                pending_releasability.process_notification(json.loads(msg.body))
            more_messages = not pending_releasability.is_terminated()
        return pending_releasability.get_status_and_formatted_result()

    def _get_parameter_prefix_name(self):
        return f'/Burgr/Releasability/{self.env_type}'

    def _get_input_and_output_topics_arn(self):
        parameter_prefix_name = self._get_parameter_prefix_name()
        trigger_topic_arn_parameter_name = f'{parameter_prefix_name}/ReleasabilityTriggerArn'
        result_topic_arn_parameter_name = f'{parameter_prefix_name}/ReleasabilityResultArn'
        result_queue_arn_parameter_name = f'{parameter_prefix_name}/ReleasabilityResultQueueArn'
        try:
            parameters = self.session.client('ssm').get_parameters(Names=[trigger_topic_arn_parameter_name, result_topic_arn_parameter_name, result_queue_arn_parameter_name])
            logger.debug(f'Parameters: {parameters}')
            for parameter in parameters['Parameters']:
                if parameter['Name'] == trigger_topic_arn_parameter_name:
                    trigger_topic_arn = parameter['Value']
                    logger.debug(f'Trigger SNS Topic ARN: {trigger_topic_arn}')
                if parameter['Name'] == result_topic_arn_parameter_name:
                    result_topic_arn = parameter['Value']
                    logger.debug(f'Result SNS Topic ARN: {result_topic_arn}')
                if parameter['Name'] == result_queue_arn_parameter_name:
                    result_queue_arn = parameter['Value']
                    logger.debug(f'Result SQS Queue ARN: {result_queue_arn}')
            return trigger_topic_arn, result_topic_arn, result_queue_arn
        except:
            raise Exception('Couldn\'t retrieve SSM parameters')

    def _get_checks_count_and_max_timeout(self):
        # Get lambdas
        client = self.session.client('lambda')
        function_response = client.list_functions()
        functions = function_response['Functions']
        while 'NextMarker' in function_response:
            function_response = client.list_functions(Marker=function_response['NextMarker'])
            functions += function_response['Functions']

        # Get
        client = self.session.client('sns')
        sns_response = client.list_subscriptions_by_topic(TopicArn=self.trigger_topic_arn)
        subscriptions = sns_response['Subscriptions']
        while 'NextToken' in sns_response:
            sns_response = client.list_subscriptions_by_topic(TopicArn=self.trigger_topic_arn, NextToken=sns_response['Subscriptions'])
            subscriptions += sns_response['Subscriptions']
        subscriptions_endpoint_arn = [d['Endpoint'] for d in subscriptions]

        # Get all checks that are subscribed to the input SNS topic
        checks = [check for check in functions if check['FunctionArn'] in subscriptions_endpoint_arn]
        checks_count = len(checks)
        logger.debug(f'Checks count: {checks_count}')
        # Get the timeout of the lambdas
        functions_timeout = [check['Timeout'] for check in functions]
        max_function_timeout = max(functions_timeout)
        logger.debug(f'Max function timeout: {max_function_timeout}')

        return checks_count, max_function_timeout


def _receive_messages(queue, max_number, wait_time):
    try:
        messages = queue.receive_messages(
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=max_number,
            WaitTimeSeconds=wait_time
        )
        return messages
    except ClientError as error:
        logger.error("Couldn't receive messages from queue")
        raise error
