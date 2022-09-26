import os
from slack_sdk import WebClient

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

artifactory_access_token = os.environ.get('ARTIFACTORY_ACCESS_TOKEN', 'no access token in env')

binaries_bucket_name = os.environ.get('BINARIES_AWS_DEPLOY', 'no binaries bucket in the env')

slack_token = os.environ.get('SLACK_API_TOKEN', 'no slack token in env')
slack_client = WebClient(slack_token)
slack_channel = os.environ.get('INPUT_SLACK_CHANNEL') or None
