import os
from slack_sdk import WebClient

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

publish_to_binaries: bool = os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true"

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')

binaries_bucket_name = os.environ.get('BINARIES_AWS_DEPLOY', 'no binaries bucket in the env')

slack_token = os.environ.get('SLACK_API_TOKEN', 'no slack token in env')
slack_client = WebClient(slack_token)
slack_channel = os.environ.get('INPUT_SLACK_CHANNEL') or None
