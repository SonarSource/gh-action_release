import sys
import os
import requests
import json

def show_output(output):
  print(f"::set-output name=myOutput::{output}")

def find_buildnumber_from_sha1(sha1):  
  query = f'build.properties.find({{"buildInfo.env.GIT_SHA1": "{sha1}"}}).include("buildInfo.env.BUILD_NUMBER")'
  url = f"{artifactory_url}/api/search/aql"
  headers = {'content-type': 'text/plain', 'X-JFrog-Art-Api': artifactory_apikey} 
  r = requests.post(url, data=query, headers=headers)      
  return r.json()['results'][0]['build.property.value']

def main():
    function_url="https://us-central1-language-team.cloudfunctions.net/release"
    buildnumber=find_buildnumber_from_sha1(os.environ["GITHUB_SHA"])
    url = f"{function_url}/{repos}/{buildnumber}/"
    GITHUB_TOKEN=os.environ["GITHUB_TOKEN"]
    headers = {'Authorization': f"token {GITHUB_TOKEN}"}
    #r = requests.get(url, headers=headers)

    show_output(url)

if __name__ == "__main__":
    main()

  