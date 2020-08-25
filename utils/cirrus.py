import os

import requests
import yaml

cirrus_token = os.environ.get('CIRRUS_TOKEN', 'no cirrus token in env')
cirrus_api_url = "https://api.cirrus-ci.com/graphql"
owner = "SonarSource"


def get_cirrus_repository_id(project):
  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query": f"query GitHubRepositoryQuery {{githubRepository(owner:\"{owner}\",name:\"{project}\"){{id}}}}"
  }
  try:
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    if r.status_code == 200:
      repository_id = r.json()["data"]["githubRepository"]["id"]
      print(f"Found cirrus repository_id for {project}:{repository_id}")
      return repository_id
    else:
      raise Exception("Invalid return code while retrieving repository id")
  except Exception as err:
    error = f"Failed to get repository id for {project} {err}"
    print(error)
    raise Exception(error)


def rules_cov(release_request, buildinfo):
  print(f"Triggering rules-cov for {release_request.project}#{release_request.buildnumber}")
  rulescov_repos = "rules-cov"
  repository_id = get_cirrus_repository_id(rulescov_repos)
  version = buildinfo.get_version()
  f = open("/app/config.yml", "r")
  config = f.read()
  data = yaml.safe_load(config)
  data['run_task']['env'].update(dict(SLUG=f"{owner}/{release_request.project}", VERSION=version))
  config = yaml.dump(data)
  url = cirrus_api_url
  headers = {'Authorization': f"Bearer {cirrus_token}"}
  payload = {
    "query": f"mutation CreateBuildDialogMutation($input: RepositoryCreateBuildInput!) {{createBuild(input: $input) {{build {{id}}}}}}",
    "variables": {
      "input": {
        "clientMutationId": f"{rulescov_repos}",
        "repositoryId": f"{repository_id}",
        "branch": "run",
        "sha": "",
        "configOverride": f"{config}"
      }
    }
  }
  error = f"Failed to trigger rules-cov for {release_request.project}#{release_request.buildnumber}"
  try:
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    if r.status_code == 200:
      if 'errors' in r.json():
        raise Exception(error)
      else:
        print(f"Triggered rules-cov on cirrus for {release_request.project}#{version}")
  except Exception as err:
    print(error)
    raise Exception(f"{error} {err}")
