import requests
import os
import sys

def prepare_logs():
    return [
      {
        "run_id": os.environ.get('run_id'),
        "source": "github",
        "message": f"https://github.com/{os.environ.get('repo')}/actions/runs/{os.environ.get('run_id')}",
        "service": "gh-action_release",
        "repo": os.environ.get('repo'),
        "releasability_checks": {
          "dependencies": os.environ.get('releasabilityCheckDependencies'),
          "qualitygate": os.environ.get('releasabilityQualityGate'),
          "github": os.environ.get('releasabilityGitHub'),
          "qa": os.environ.get('releasabilityQA'),
          "manifest_values": os.environ.get('releasabilityCheckManifestValues'),
          "jira": os.environ.get('releasabilityJira'),
          "peachee_stats": os.environ.get('releasabilityCheckPeacheeLanguagesStatistics'),
          "parent_pom": os.environ.get('releasabilityParentPOM')
        },
        "release_passed": os.environ.get('release_passed'),
        "maven_central_published": os.environ.get('maven_central_published'),
        "javadoc_published": os.environ.get('javadoc_published'),
        "testpypi_published": os.environ.get('testpypi_published'),
        "pypi_published": os.environ.get('pypi_published'),
        "npm_published": os.environ.get('npm_published'),
        "status": os.environ.get('status'),
        "is_dummy_project": os.environ.get('is_dummy_project')
      }
    ]

def push_logs(logs, token):
    response = requests.post("https://http-intake.logs.datadoghq.eu/api/v2/logs",
        json=logs,
        headers={
         "Content-Type": "application/json",
         "DD-API-KEY": token,
        },
    )
    return response


if __name__ == '__main__':
    logs = prepare_logs()
    res = push_logs(logs, os.environ.get('datadog_token'))
    if res.status_code != 202:
       print(res.text)
       sys.exit(1)
