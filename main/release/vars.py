import os
from slack_sdk import WebClient

binaries_bucket_name = os.environ.get('BINARIES_AWS_DEPLOY')

slack_token = os.environ.get('SLACK_API_TOKEN')
slack_client = WebClient(slack_token)
slack_channel = os.environ.get('INPUT_SLACK_CHANNEL') or None

binaries_aws_access_key_id = os.environ.get('BINARIES_AWS_ACCESS_KEY_ID')
binaries_aws_secret_access_key = os.environ.get('BINARIES_AWS_SECRET_ACCESS_KEY')
binaries_aws_session_token = os.environ.get('BINARIES_AWS_SESSION_TOKEN')
binaries_aws_region_name = os.environ.get('BINARIES_AWS_DEFAULT_REGION')
