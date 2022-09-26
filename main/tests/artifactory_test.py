from unittest.mock import patch, ANY
from pytest import fixture

from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.artifactory import Artifactory
from release.utils.buildinfo import BuildInfo


@fixture
def release_request():
    return ReleaseRequest('org', 'project', 'version', 'buildnumber', 'branch', 'sha')

@fixture
def buildinfo_multi():
    return  BuildInfo({
        "buildInfo":{
            "statuses": [{
            "status": "it-passed",
            "timestamp": "2022-09-09T14:50:41.770+0000",
            "user": "repox-build-promoter-re-ef42e7",
            "timestampDate": 1662735041770
            }]
        }
    })    

@fixture
def buildinfo():
    return  BuildInfo({
        "buildInfo":{
            "statuses": [{
            "status": "it-passed",
            "repository": "sonarsource-public-builds",
            "timestamp": "2022-09-09T14:50:41.770+0000",
            "user": "repox-build-promoter-re-ef42e7",
            "timestampDate": 1662735041770
            }]
        }
    })    


class RepoxResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "{ 'message' : 'done' }"
        self.ok = True
    def json(self):
        return { 'message' : 'done' }

def test_notify(release_request):
    with patch('release.utils.artifactory.requests.get', return_value=RepoxResponse(200)) as request:
        Artifactory("token").receive_build_info(release_request)
        request.assert_called_once_with(
            f"{Artifactory.url}/api/build/{release_request.project}/{release_request.buildnumber}",
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )

def test_promote(release_request,buildinfo):    
    with patch('release.utils.artifactory.requests.post', return_value=RepoxResponse(200)) as request:
        Artifactory("token").promote(release_request,buildinfo)
        request.assert_called_once_with(
            f"{Artifactory.url}/api/build/promote/{release_request.project}/{release_request.buildnumber}",
            data='{"status": "released", "sourceRepo": "sonarsource-public-builds", "targetRepo": "sonarsource-public-releases"}',
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )


def test_promote_revoke(release_request,buildinfo):    
    with patch('release.utils.artifactory.requests.post', return_value=RepoxResponse(200)) as request:
        Artifactory("token").promote(release_request,buildinfo,True)
        request.assert_called_once_with(
            f"{Artifactory.url}/api/build/promote/{release_request.project}/{release_request.buildnumber}",
            data='{"status": "it-passed", "sourceRepo": "sonarsource-public-releases", "targetRepo": "sonarsource-public-builds"}',
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )


def test_multi_promote(release_request,buildinfo_multi):
    with patch('release.utils.artifactory.requests.get', return_value=RepoxResponse(200)) as request:        
        Artifactory("token").promote(release_request,buildinfo_multi)
        request.assert_called_once_with(
            f"{Artifactory.url}/api/plugins/execute/multiRepoPromote?params="+
                "buildName=project;"+
                "buildNumber=buildnumber;"+
                "status=released;"+
                "src1=sonarsource-private-builds;"+
                "target1=sonarsource-private-releases;"+
                "src2=sonarsource-public-builds;"+
                "target2=sonarsource-public-releases",
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )

def test_multi_promote_revoke(release_request,buildinfo_multi):
    with patch('release.utils.artifactory.requests.get', return_value=RepoxResponse(200)) as request:        
        Artifactory("token").promote(release_request,buildinfo_multi,True)
        request.assert_called_once_with(
            f"{Artifactory.url}/api/plugins/execute/multiRepoPromote?params="+
                "buildName=project;"+
                "buildNumber=buildnumber;"+
                "status=it-passed;"+
                "src1=sonarsource-private-releases;"+
                "target1=sonarsource-private-builds;"+
                "src2=sonarsource-public-releases;"+
                "target2=sonarsource-public-builds", 
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )

def test_download():
    with patch('release.utils.artifactory.urllib.request.urlretrieve') as request:        
        Artifactory("token").download('repo','gid','aid','qual','ext','version')
        request.assert_called_once_with(
            f"{Artifactory.url}/repo/gid/aid/version/aid-version-qual.ext", 
            '/tmp/aid-version-qual.ext'
        )
