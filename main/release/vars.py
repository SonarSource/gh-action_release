import os
from slack_sdk import WebClient

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER')
burgrx_password = os.environ.get('BURGRX_PASSWORD')

binaries_bucket_name = os.environ.get('BINARIES_AWS_DEPLOY')

slack_token = os.environ.get('SLACK_API_TOKEN')
slack_client = WebClient(slack_token)
slack_channel = os.environ.get('INPUT_SLACK_CHANNEL') or None
