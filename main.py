import json
import re
import sys
import os
import traceback

import steps.distribute as distributeStep
from steps import release, relesability
from steps.distribute import ReleaseRequest
from utils.artifactory import Artifactory
from utils.github import revoke_release, get_release_info

githup_api_url = "https://api.github.com"
github_token = os.environ.get('GITHUB_TOKEN', 'no github token in env')
github_event_path = os.environ.get('GITHUB_EVENT_PATH')
attach = os.environ.get('INPUT_ATTACH_ARTIFACTS_TO_GITHUB_RELEASE')
distribute = os.environ.get('INPUT_DISTRIBUTE')
run_rules_cov = os.environ.get('INPUT_RUN_RULES_COV')

artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')


def set_releasability_output(output):
    print(f"::set-output name=releasability::{output}")


def set_release_output(function, output):
    print(f"::set-output name={function}::{output}")


def abort_release(repo, version):
    print(f"::error  Aborting release")
    revoke_release(repo, version)
    sys.exit(1)


def current_branch():
    with open(github_event_path) as file:
        data = json.load(file)
        if 'release' not in data:
            print(f"::error Could not get release object of github event")
            return None
        if 'target_commitish' not in data['release']:
            print(f"::error Could not get the branch name of github event")
            return None
        possible_branch_name = data['release']['target_commitish']
        if re.compile("^([a-f0-9]{40})$").match(possible_branch_name):
            return None
        return possible_branch_name


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    organisation, project = repo.split("/")
    tag = os.environ["GITHUB_REF"]
    version = tag.replace('refs/tags/', '', 1)
    # tag shall be like X.X.X.BUILD_NUMBER
    build_number = version.split(".")[-1]
    headers = {'Authorization': f"token {github_token}"}
    release_info = get_release_info(repo, version)

    if not release_info:
        print(f"::error  No release info found")
        return

    try:
        relesability.releasability_checks(project, version, current_branch())
    except Exception as e:
        print(f"::error relesability did not complete correctly. " + str(e))
        print(traceback.format_exc())
        sys.exit(1)

    artifactory = Artifactory(artifactory_apikey)
    rr = ReleaseRequest(organisation, project, build_number)

    try:
        release.release(artifactory, rr, attach, run_rules_cov)
        set_release_output("release", f"{repo}:{version} release DONE")
        if distribute == 'true':
            distributeStep.distribute_release(artifactory, rr)
            set_release_output("distribute_release", f"{repo}:{version} distribute_release DONE")
    except Exception as e:
        print(f"::error release did not complete correctly." + str(e))
        abort_release(repo, version)
        sys.exit(1)


if __name__ == "__main__":
    main()
