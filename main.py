import sys
import os
import requests
import json
import urllib.request
import paramiko
'''
x Promote
- Push to binaries
x Tag github
notify burgr
'''

artifactoryUrl='https://repox.jfrog.io/repox'
binariesHost='binaries.sonarsource.com'
binariesUrl=f"https://{binariesHost}"
artifactoryApiKey=os.environ.get('ARTIFACTORY_API_KEY','no api key in env')  

def main():
    my_input = os.environ["INPUT_MYINPUT"]
    my_output = f"Hello {my_input}"
    print(f"::set-output name=myOutput::{my_output}")


if __name__ == "__main__":
    main()

def repoxGetPropertyFromBuildInfo(project, buildNumber, property):  
  buildInfo = repoxGetBuildInfo(project,buildNumber)
  return buildInfo['buildInfo']['properties'][property]

def repoxGetModulePropertyFromBuildInfo(project, buildNumber, property):  
  buildInfo = repoxGetBuildInfo(project,buildNumber)
  return buildInfo['buildInfo']['modules'][0]['properties'][property]

def getVersion(project, buildNumber):  
  buildInfo = repoxGetBuildInfo(project,buildNumber)  
  return buildInfo['buildInfo']['modules'][0]['id'].split(":")[-1]
  
def repoxGetBuildInfo(project, buildNumber):  
  url = f"{artifactoryUrl}/api/build/{project}/{buildNumber}"
  headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey} 
  r = requests.get(url, headers=headers)  
  buildInfo = r.json()
  if r.status_code == 200:      
    return buildInfo
  else:
    raise Exception('unknown build')  

def getArtifactsToPublish(project,buildNumber):
  artifactsToPublish = repoxGetModulePropertyFromBuildInfo(project, buildNumber,'artifactsToPublish')
  return artifactsToPublish

def publishAllArtifacts(artifactsToPublish,version,repo):  
  artifacts = artifactsToPublish.split(",")
  artifactsCount = len(artifacts)   
  if artifactsCount == 1:
    print("only 1")
    return publishArtifact(artifactsToPublish,version,repo)  
  releaseURL = ""
  print(f"{artifactsCount} artifacts")
  for i in range(0, artifactsCount):      
    print(f"artifact {i}")  
    releaseURL = publishArtifact(artifacts[i - 1],version,repo)  
  return releaseURL


def publishArtifact(artifactToPublish,version,repo): 
  artifact = artifactToPublish.split(":")
  gid = artifact[0]
  aid = artifact[1]
  ext = artifact[2]
  qual = ''
  binariesRepo = "Distribution"  
  if repo.startswith('sonarsource-private'):
    binariesRepo = "CommercialDistribution"
  artifactoryRepo = repo.replace('builds', 'releases')    
  print(f"{gid} {aid} {ext}")
  releaseURL = f"{binariesUrl}/{bintrayRepo}/{aid}/{aid}-{version}.{ext}" 
  return releaseURL

def promote(project,buildNumber,multi):
  targetRepo="sonarsource-private-builds"
  targetRepo2="sonarsource-public-builds"
  status='release'  
  
  try:
    repo = repoxGetPropertyFromBuildInfo(project, buildNumber,'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
    targetRepo = repo.replace('builds', 'releases')
  except Exception as e:
    print(f"Could not get repository for {project} {buildNumber} {str(e)}")
  
  print(f"Promoting build {project}#{buildNumber}")
  json_payload={
      "status": f"{status}",
      "targetRepo": f"{targetRepo}"
  }
  if multi == "true":
    url = f"{artifactoryUrl}/api/plugins/execute/multiRepoPromote?params=buildName={project};buildNumber={buildNumber};src1=sonarsource-private-qa;target1={targetRepo};src2=sonarsource-public-qa;target2={targetRepo2};status={status}"
    headers = {'X-JFrog-Art-Api': artifactoryApiKey}
    r = requests.get(url, headers=headers)
  else:
    url = f"{artifactoryUrl}/api/build/promote/{project}/{buildNumber}"
    headers = {'content-type': 'application/json', 'X-JFrog-Art-Api': artifactoryApiKey}
    r = requests.post(url, data=json.dumps(json_payload), headers=headers)      
  if r.status_code == 200:      
    return f"status:{status}"
  else:
    return f"status:{status} code:{r.status_code}"

def uploadToBinaries(binariesRepo,artifactoryRepo,gid,aid,qual,ext,version):
  BINARIES_PATH_PREFIX=''
  PASSPHRASE=''
  #download artifact
  groupIdPath=gid.replace(".", "/")
  artifactory=artifactoryUrl+"/"+artifactoryRepo
  filename=f"{aid}-{version}.{ext}"
  if qual:
    filename=f"{aid}-{version}-{qual}.{ext}"
  url=f"{artifactory}/{groupIdPath}/{aid}/{version}/{filename}"    
  urllib.request.urlretrieve(url, filename)
  #upload artifact
  ssh_client =paramiko.SSHClient()
  ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
  ssh_client.connect(hostname=binariesHost,username='ssuopsa',password='password')
  #create directory
  stdin,stdout,stderr=ssh_client.exec_command(f"mkdir -p {BINARIES_PATH_PREFIX}/{binariesRepo}/{aid}/")
  ftp_client=ssh_client.open_sftp()
  #upload file
  ftp_client.put(filename,f"{BINARIES_PATH_PREFIX}/{binariesRepo}/{aid}/")
  ftp_client.close()
  #sign file
  stdin,stdout,stderr=ssh_client.exec_command(f"gpg --batch --passphrase {PASSPHRASE} --armor --detach-sig --default-key infra@sonarsource.com {filename}")
  ssh_client.close()