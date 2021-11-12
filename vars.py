import os

repo = os.environ["GITHUB_REPOSITORY"]
ref = os.environ["GITHUB_REF"]

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')
#github_attach: bool = os.environ.get('INPUT_ATTACH_ARTIFACTS_TO_GITHUB_RELEASE').lower() == "true"

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')

publish_to_binaries: bool = os.environ.get('INPUT_PUBLISH_TO_BINARIES').lower() == "true"
distribute: bool = os.environ.get('INPUT_DISTRIBUTE').lower() == "true"
run_rules_cov: bool = os.environ.get('INPUT_RUN_RULES_COV').lower() == "true"

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')
distribute_target = os.environ.get('INPUT_DISTRIBUTE_TARGET') or None

bintray_api_url='https://api.bintray.com'
bintray_user=os.environ.get('BINTRAY_USER','no bintray api user in env')
bintray_apikey=os.environ.get('BINTRAY_TOKEN','no bintray api key in env')
central_user=os.environ.get('CENTRAL_USER','no central user in env')
central_password=os.environ.get('CENTRAL_PASSWORD','no central password in env')

binaries_host = 'binaries.sonarsource.com'
binaries_ssh_user=os.environ.get('RELEASE_SSH_USER','no ssh user in env')
binaries_ssh_key=os.environ.get('RELEASE_SSH_KEY','no ssh key in env')
binaries_path_prefix = os.environ.get('PATH_PREFIX', '/tmp')
passphrase = os.environ.get('GPG_PASSPHRASE', 'no GPG_PASSPHRASE in env')
