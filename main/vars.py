import os
from slack import WebClient

repo = os.environ.get('GITHUB_REPOSITORY', 'no github repo in env')
ref = os.environ.get('GITHUB_REF', 'no github repo in env')

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')

releasability_access_key_id = os.environ.get('RELEASABILITY_AWS_ACCESS_KEY_ID', 'no releasability access key id in env')
releasability_secret_access_key = os.environ.get('RELEASABILITY_AWS_SECRET_ACCESS_KEY', 'no releasability secret key in env')

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')

publish_to_binaries: bool = os.environ.get('INPUT_PUBLISH_TO_BINARIES', 'false').lower() == "true"
binaries_bucket_name = os.environ.get('BINARIES_AWS_DEPLOY', 'no binaries bucket in the env')
binaries_access_key_id = os.environ.get('BINARIES_AWS_ACCESS_KEY_ID', 'no binaries access key id in env')
binaries_secret_access_key = os.environ.get('BINARIES_AWS_SECRET_ACCESS_KEY', 'no binaries secret key in env')
binaries_region = os.environ.get('BINARIES_AWS_REGION', 'no binaries region in env')

slack_token = os.environ.get('SLACK_API_TOKEN', 'no slack token in env')
slack_client = WebClient(slack_token)
slack_channel = os.environ.get('INPUT_SLACK_CHANNEL') or None
