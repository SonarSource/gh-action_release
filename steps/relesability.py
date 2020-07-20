import os
import urllib

import polling
import requests
from polling import TimeoutException
from requests.auth import HTTPBasicAuth
from requests.models import Response

burgrx_url = 'https://burgrx.sonarsource.com'
burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')


def releasability_checks(project: str, version: str, branch: str = 'master', nb_of_commits: int = 5):
  r"""Starts the releasability check operation. Post the start releasability HTTP request to Burgrx and polls until
    all checks have completed.

    :param project: Github project name, ex: 'sonar-dummy'
    :param version: full version to be checked for releasability.
    :param branch: branch to be checked for releasability.
    :param nb_of_commits: number of latest commits on the branch to get the status from.
    :return: True if releasability check succeeded, False otherwise.
    """

  print(f"Starting releasability check: {project}#{version}")
  url = f"{burgrx_url}/api/project/SonarSource/{project}/releasability/start/{version}"
  response = requests.post(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password))
  message = response.json().get('message', '')
  if response.status_code == 200 and message == "done":
    print(f"Releasability checks started successfully")
    return start_polling_releasability_status(project, version, branch, nb_of_commits)
  else:
    print(f"Releasability checks failed to start: {response} '{message}'")
    raise Exception(f"Releasability checks failed to start: '{message}'")


def start_polling_releasability_status(project: str,
                                       version: str,
                                       branch: str,
                                       nb_of_commits: int,
                                       step: int = 4,
                                       timeout: int = 300,
                                       check_releasable: bool = True) -> bool:
  r"""Starts polling Burgrx for latest releasability status.

    :param project: Github project name, ex: 'sonar-dummy'
    :param version: full version to be checked for releasability.
    :param branch: branch to be checked for releasability.
    :param nb_of_commits: number of latest commits on the branch to get the status from.
    :param step: step in seconds between polls. (For testing, otherwise use default value)
    :param timeout: timeout in seconds for attempting to get status. (For testing, otherwise use default value)
    :param check_releasable: whether should check for 'releasable' flag in json response. (For testing, otherwise use default value)
    :return: Metadata containing detailed releasability information, False if an unexpected error occurred.
    """

  url_encoded_project = urllib.parse.quote(f"SonarSource/{project}", safe='')
  url = f"{burgrx_url}/api/commitPipelinesStages?project={url_encoded_project}&branch={branch}&nbOfCommits={nb_of_commits}&startAtCommit=0"

  try:
    releasability = polling.poll(
      lambda: get_latest_releasability_stage(requests.get(url, auth=HTTPBasicAuth(burgrx_user, burgrx_password)),
                                             version,
                                             check_releasable),
      step=step,
      timeout=timeout)
    print(f"Releasability checks finished with status '{releasability['status']}'")
    return releasability.get('metadata')
  except TimeoutException:
    print("Releasability timed out")
    raise Exception("Releasability timed out")
  except Exception as e:
    print(f"Cannot complete releasability checks:", e)
    raise e


def get_latest_releasability_stage(response: Response, version: str, check_releasable: bool = True) -> bool:
  print("Polling releasability status...")

  if response.status_code != 200:
    raise Exception(f"Error occurred while trying to retrieve current releasability status: {response}")

  commits_info = response.json()
  if len(commits_info) == 0:
    raise Exception(f"No commit information found in burgrx for this branch")

  pipeline = get_corresponding_pipeline(commits_info, version)
  if not pipeline:
    raise Exception(f"No pipeline info found for version '{version}'")

  if check_releasable and not pipeline.get('releasable'):
    raise Exception(f"Pipeline '{pipeline}' is not releasable")

  stages = pipeline.get('stages') or []
  latest_releasability_stage = next((stage for stage in reversed(stages) if stage.get('type') == 'releasability'),
                                    None)
  if latest_releasability_stage and is_finished(latest_releasability_stage['status']):
    return latest_releasability_stage

  print("Releasability checks still running")
  return False


def get_corresponding_pipeline(commits_info, version):
  for commit_info in commits_info:
    pipelines = commit_info.get('pipelines') or []
    pipeline = next((x for x in pipelines if x.get('version') == version), None)
    if pipeline is not None:
      return pipeline

  return None


def is_finished(status: str):
  return status == 'errored' or status == 'failed' or status == 'passed'
