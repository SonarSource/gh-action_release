import tempfile
from unittest.mock import patch
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
        "buildInfo": {
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
        "buildInfo": {
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
        return {'message': 'done'}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


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
    with patch('release.utils.artifactory.requests.get') as request, \
         patch('builtins.open', create=True):
        mock_response = RepoxResponse(200)
        mock_response.iter_content = lambda chunk_size: [b'test data']
        request.return_value = mock_response

        Artifactory("token").download('repo', 'gid', 'aid', 'qual', 'ext', 'version')
        request.assert_called_once_with(
            f"{Artifactory.url}/repo/gid/aid/version/aid-version-qual.ext",
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'},
            stream=True
        )


def test_download_with_checksums():
    with patch('release.utils.artifactory.requests.get') as request, \
         patch('builtins.open', create=True):
        # Mock response for main file
        main_response = RepoxResponse(200)
        main_response.iter_content = lambda chunk_size: [b'test data']

        # Mock responses for checksums
        checksum_response = RepoxResponse(200)
        checksum_response.content = b'checksum_value'

        request.side_effect = [main_response, checksum_response, checksum_response]

        Artifactory("token").download('repo', 'gid', 'aid', 'qual', 'ext', 'version', checksums=['md5', 'sha1'])

        # Verify main file request
        assert request.call_count == 3
        assert request.call_args_list[0] == (
            (f"{Artifactory.url}/repo/gid/aid/version/aid-version-qual.ext",),
            {'headers': {'content-type': 'application/json', 'Authorization': 'Bearer token'}, 'stream': True}
        )
        # Verify checksum requests
        assert request.call_args_list[1] == (
            (f"{Artifactory.url}/repo/gid/aid/version/aid-version-qual.ext.md5",),
            {'headers': {'content-type': 'application/json', 'Authorization': 'Bearer token'}}
        )
        assert request.call_args_list[2] == (
            (f"{Artifactory.url}/repo/gid/aid/version/aid-version-qual.ext.sha1",),
            {'headers': {'content-type': 'application/json', 'Authorization': 'Bearer token'}}
        )


class StorageResponse:
    def __init__(self, status_code, children):
        self.status_code = status_code
        self._children = children
    def json(self):
        return {'children': self._children}


def _child(name, folder=False):
    return {'uri': f'/{name}', 'folder': folder}


def test_find_sbom_filename_cyclonedx():
    children = [
        _child('sonar-application-1.0-cyclonedx.json'),
        _child('sonar-application-1.0-cyclonedx.json.asc'),
        _child('sonar-application-1.0.zip'),
        _child('sonar-application-1.0.pom'),
    ]
    with patch('release.utils.artifactory.requests.get', return_value=StorageResponse(200, children)) as request:
        result = Artifactory("token").find_sbom_filename('repo', 'org.sonarsource.sonarqube', 'sonar-application', '1.0')
        assert result == 'sonar-application-1.0-cyclonedx.json'
        request.assert_called_once_with(
            f"{Artifactory.url}/api/storage/repo/org/sonarsource/sonarqube/sonar-application/1.0",
            headers={'content-type': 'application/json', 'Authorization': 'Bearer token'}
        )


def test_find_sbom_filename_sbom_named_and_private_repo():
    children = [_child('SonarLint.visualstudio.sbom-8.5.0-2022.json'), _child('binary.zip')]
    with patch('release.utils.artifactory.requests.get', return_value=StorageResponse(200, children)) as request:
        result = Artifactory("token").find_sbom_filename(
            'sonarsource-public-releases', 'com.sonarsource.foo', 'bar', '8.5.0')
        assert result == 'SonarLint.visualstudio.sbom-8.5.0-2022.json'
        # com.* gid must resolve to the private repo
        assert request.call_args[0][0].startswith(
            f"{Artifactory.url}/api/storage/sonarsource-private-releases/com/sonarsource/foo/bar/8.5.0")


def test_find_sbom_filename_none_when_absent():
    children = [_child('binary.zip'), _child('binary.zip.asc'), _child('binary.pom')]
    with patch('release.utils.artifactory.requests.get', return_value=StorageResponse(200, children)):
        assert Artifactory("token").find_sbom_filename('repo', 'org.x', 'aid', '1.0') is None


def test_find_sbom_filename_none_on_listing_error():
    with patch('release.utils.artifactory.requests.get', return_value=StorageResponse(404, [])):
        assert Artifactory("token").find_sbom_filename('repo', 'org.x', 'aid', '1.0') is None


def test_download_named_with_optional_checksum_present_and_absent():
    main_response = RepoxResponse(200)
    main_response.iter_content = lambda chunk_size: [b'sbom data']
    md5_response = RepoxResponse(200)
    md5_response.content = b'md5'
    sha1_response = RepoxResponse(200)
    sha1_response.content = b'sha1'
    sha256_response = RepoxResponse(200)
    sha256_response.content = b'sha256'
    asc_missing = RepoxResponse(404)
    with patch('release.utils.artifactory.requests.get') as request, \
         patch('builtins.open', create=True):
        request.side_effect = [main_response, md5_response, sha1_response, sha256_response, asc_missing]
        temp_file, optional = Artifactory("token").download_named(
            'repo', 'org.x', 'aid', '1.0', 'aid-1.0-cyclonedx.json',
            checksums=['md5', 'sha1', 'sha256'], optional_checksums=['asc'])
        assert temp_file == f"{tempfile.gettempdir()}/aid-1.0-cyclonedx.json"
        assert optional == []  # .asc was absent (404) -> skipped, not fatal
        assert request.call_args_list[0][0][0] == \
            f"{Artifactory.url}/repo/org/x/aid/1.0/aid-1.0-cyclonedx.json"
