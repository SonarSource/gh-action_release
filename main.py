import sys
import os
import requests
import json

def show_output(output):
  print(f"::set-output name=myOutput::{output}")

def main():
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    sha1=os.environ["GITHUB_SHA"]
    repo=os.environ["GITHUB_REPOSITORY"]
    url = f"{function_url}/{repo}/{sha1}/"
    GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
    headers = {'Authorization': f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)

    show_output(url)

if __name__ == "__main__":
    main()

  