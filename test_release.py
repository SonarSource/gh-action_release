from main import repoxGetPropertyFromBuildInfo,getArtifactsToPublish,getVersion
from main import promote
from main import publishAllArtifacts,publishArtifact

def test_repoxGetPropertyFromBuildInfo():
  project="sonar-dummy"
  buildNumber="396"
  repo = repoxGetPropertyFromBuildInfo(project, buildNumber, 'buildInfo.env.ARTIFACTORY_DEPLOY_REPO')
  assert repo == 'sonarsource-private-qa'

def test_promote():
  project="sonar-dummy"
  buildNumber="297"
  status = promote(project, buildNumber, "false")  
  assert status == 'status:release'

def test_getArtifactsToPublish():
  project="sonar-dummy"
  buildNumber="297"
  artifacts = getArtifactsToPublish(project,buildNumber)
  assert artifacts == 'com.sonarsource.dummy:sonar-dummy-plugin:jar'

def test_publishAllArtifacts():
  artifacts = 'com.sonarsource.dummy:sonar-dummy-plugin:jar,com.sonarsource.cpp:sonar-cpp-plugin:jar'
  version='10.0.0.297'
  print(publishAllArtifacts(artifacts,version))

def test_getVersion():
  project="sonar-java"
  buildNumber="20691"
  version = getVersion(project,buildNumber)
  print(version)
  