from unittest.mock import patch, MagicMock

from pytest import fixture

from release.utils.binaries import Binaries
from release.utils.buildinfo import BuildInfo
from release.utils.release import publish_artifact


@fixture
def buildinfo():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "com.sonarsource.dummy:dummy:zip",
                },
                "id": "com.sonarsource.dummy:dummy:1.0.2.456",
            }]
        }
    })


def test_publish_artifact(buildinfo, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifact_to_publish = buildinfo.get_artifacts_to_publish()
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.zip"})
        binaries = Binaries("test_bucket")
        version = buildinfo.get_version()
        with patch('release.utils.binaries.Binaries.s3_upload') as s3_upload:
            publish_artifact(artifactory, binaries, artifact_to_publish, version, "repo")
            s3_upload.assert_called_once_with("/tmp/dummy-1.0.2.456.zip", "dummy-1.0.2.456.zip", "com.sonarsource.dummy", "dummy",
                                              "1.0.2.456")
            captured = capsys.readouterr()
            assert captured.out == "publishing com.sonarsource.dummy:dummy:zip#1.0.2.456\n" \
                                   "com.sonarsource.dummy dummy zip \n"
        with patch.object(binaries, 'upload_sonarlint_unzip') as mock_upload_sonarlint_unzip, \
            patch.object(binaries, 'upload_sonarlint_p2_site') as mock_upload_sonarlint_p2_site, \
            patch.object(client, 'upload_file') as upload_file:
            publish_artifact(artifactory, binaries, artifact_to_publish, version, "repo")
            upload_file.assert_called_with('/tmp/dummy-1.0.2.456.zip.asc', 'test_bucket',
                                           'CommercialDistribution/dummy/dummy-1.0.2.456.zip.asc')
            captured = capsys.readouterr()
            assert captured.out == 'publishing com.sonarsource.dummy:dummy:zip#1.0.2.456\n' + \
                   'com.sonarsource.dummy dummy zip \n' + \
                   'uploaded /tmp/dummy-1.0.2.456.zip to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.zip\n' + \
                   'uploaded /tmp/dummy-1.0.2.456.zip.md5 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.zip.md5\n' + \
                   'uploaded /tmp/dummy-1.0.2.456.zip.sha1 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.zip.sha1\n' + \
                   'uploaded /tmp/dummy-1.0.2.456.zip.sha256 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.zip.sha256\n' + \
                   'uploaded /tmp/dummy-1.0.2.456.zip.asc to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.zip.asc\n'
            mock_upload_sonarlint_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()
