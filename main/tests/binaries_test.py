import os
import tempfile
from unittest.mock import patch, MagicMock, call
from xml.dom.minidom import parse

from pytest import fixture

from release.utils.binaries import Binaries
from release.utils.buildinfo import BuildInfo
from release.utils.release import publish_artifact


@fixture
def buildinfo_com():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "com.sonarsource.dummy:dummy:jar",
                },
                "id": "com.sonarsource.dummy:dummy:1.0.2.456",
            }]
        }
    })


@fixture
def buildinfo_org():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "org.sonarsource.dummy:dummy:jar:qualifier",
                },
                "id": "org.sonarsource.dummy:dummy:1.0.2.456",
            }]
        }
    })


@fixture
def buildinfo_sonarlint():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "org.sonarsource.sonarlint.eclipse:org.sonarlint.eclipse.site:zip",
                },
                "id": "org.sonarsource.sonarlint.eclipse:org.sonarlint.eclipse.cdt:7.9.0.63244",
            }]
        }
    })


@fixture
def buildinfo_sonarqube():
    return BuildInfo({
        "buildInfo": {
            "properties": {
                "buildInfo.env.ARTIFACTS_TO_PUBLISH": "org.sonarsource.sonarqube:sonar-application:zip",
            },
            "modules": [{
                "id": "org.sonarsource.sonarqube:sonar-xoo-plugin:10.0.0.66185",
            }]
        }
    })


# aid == "org.sonarlint.eclipse.site":

def test_publish_artifact_s3_upload(buildinfo_com, buildinfo_org, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.jar"})
        binaries = Binaries("test_bucket")
        version = buildinfo_com.get_version()
        with patch('release.utils.binaries.Binaries.s3_upload') as s3_upload:
            # com
            publish_artifact(artifactory, binaries, buildinfo_com.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_once_with("/tmp/dummy-1.0.2.456.jar", "dummy-1.0.2.456.jar", "com.sonarsource.dummy", "dummy",
                                              "1.0.2.456")
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing com.sonarsource.dummy:dummy:jar#1.0.2.456"
            assert captured[1] == "com.sonarsource.dummy dummy jar "

            # org
            publish_artifact(artifactory, binaries, buildinfo_org.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_with("/tmp/dummy-1.0.2.456.jar", "dummy-1.0.2.456-qualifier.jar", "org.sonarsource.dummy", "dummy",
                                         "1.0.2.456")
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing org.sonarsource.dummy:dummy:jar:qualifier#1.0.2.456"
            assert captured[1] == "org.sonarsource.dummy dummy jar qualifier"


def test_publish_artifact_s3_upload_sonarqube(buildinfo_sonarqube, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/sonarqube-10.0.0.66185.zip"})
        binaries = Binaries("test_bucket")
        version = buildinfo_sonarqube.get_version()
        with patch('release.utils.binaries.Binaries.s3_upload') as s3_upload:
            publish_artifact(artifactory, binaries, buildinfo_sonarqube.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_once_with("/tmp/sonarqube-10.0.0.66185.zip", "sonarqube-10.0.0.66185.zip", 'org.sonarsource.sonarqube',
                                              'sonarqube', '10.0.0.66185')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing org.sonarsource.sonarqube:sonar-application:zip#10.0.0.66185"
            assert captured[1] == "org.sonarsource.sonarqube sonar-application zip "


def test_publish_artifact_upload_file(buildinfo_com, buildinfo_org, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.jar"})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_sonarlint_unzip') as mock_upload_sonarlint_unzip, \
            patch.object(binaries, 'upload_sonarlint_p2_site') as mock_upload_sonarlint_p2_site, \
            patch.object(client, 'upload_file') as upload_file:
            # com
            version = buildinfo_com.get_version()
            publish_artifact(artifactory, binaries, buildinfo_com.get_artifacts_to_publish(), version, "repo")
            upload_file.assert_called_with('/tmp/dummy-1.0.2.456.jar.asc', 'test_bucket',
                                           'CommercialDistribution/dummy/dummy-1.0.2.456.jar.asc')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'publishing com.sonarsource.dummy:dummy:jar#1.0.2.456'
            assert captured[1] == 'com.sonarsource.dummy dummy jar '
            assert captured[2] == 'uploaded /tmp/dummy-1.0.2.456.jar to s3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.jar'
            assert captured[3] == 'uploaded /tmp/dummy-1.0.2.456.jar.md5 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.jar.md5'
            assert captured[4] == 'uploaded /tmp/dummy-1.0.2.456.jar.sha1 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.jar.sha1'
            assert captured[5] == 'uploaded /tmp/dummy-1.0.2.456.jar.sha256 to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.jar.sha256'
            assert captured[6] == 'uploaded /tmp/dummy-1.0.2.456.jar.asc to ' + \
                   's3://test_bucket/CommercialDistribution/dummy/dummy-1.0.2.456.jar.asc'
            mock_upload_sonarlint_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()
            # org
            version = buildinfo_org.get_version()
            publish_artifact(artifactory, binaries, buildinfo_org.get_artifacts_to_publish(), version, "repo")
            upload_file.assert_called_with('/tmp/dummy-1.0.2.456.jar.asc', 'test_bucket',
                                           'Distribution/dummy/dummy-1.0.2.456-qualifier.jar.asc')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'publishing org.sonarsource.dummy:dummy:jar:qualifier#1.0.2.456'
            assert captured[1] == 'org.sonarsource.dummy dummy jar qualifier'
            assert captured[2] == 'uploaded /tmp/dummy-1.0.2.456.jar to s3://test_bucket/Distribution/dummy/dummy-1.0.2.456-qualifier.jar'
            assert captured[3] == 'uploaded /tmp/dummy-1.0.2.456.jar.md5 to ' \
                                  's3://test_bucket/Distribution/dummy/dummy-1.0.2.456-qualifier.jar.md5'
            assert captured[4] == 'uploaded /tmp/dummy-1.0.2.456.jar.sha1 to ' \
                                  's3://test_bucket/Distribution/dummy/dummy-1.0.2.456-qualifier.jar.sha1'
            assert captured[5] == 'uploaded /tmp/dummy-1.0.2.456.jar.sha256 to ' \
                                  's3://test_bucket/Distribution/dummy/dummy-1.0.2.456-qualifier.jar.sha256'
            assert captured[6] == 'uploaded /tmp/dummy-1.0.2.456.jar.asc to ' \
                                  's3://test_bucket/Distribution/dummy/dummy-1.0.2.456-qualifier.jar.asc'
            mock_upload_sonarlint_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()


def test_publish_artifact_upload_file_sonarlint(buildinfo_sonarlint, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip"})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_sonarlint_unzip') as mock_upload_sonarlint_unzip, \
            patch.object(binaries, 'upload_sonarlint_p2_site') as mock_upload_sonarlint_p2_site, \
            patch.object(client, 'upload_file') as upload_file:
            version = buildinfo_sonarlint.get_version()
            publish_artifact(artifactory, binaries, buildinfo_sonarlint.get_artifacts_to_publish(), version, "repo")
            upload_file.assert_called_with('/tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip.asc', 'test_bucket',
                                           'SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip.asc')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'publishing org.sonarsource.sonarlint.eclipse:org.sonarlint.eclipse.site:zip#7.9.0.63244'
            assert captured[1] == 'org.sonarsource.sonarlint.eclipse org.sonarlint.eclipse.site zip '
            assert captured[2] == 'uploaded /tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip to ' + \
                   's3://test_bucket/SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip'
            assert captured[3] == 'uploaded /tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip.md5 to ' + \
                   's3://test_bucket/SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip.md5'
            assert captured[4] == 'uploaded /tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip.sha1 to ' + \
                   's3://test_bucket/SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip.sha1'
            assert captured[5] == 'uploaded /tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip.sha256 to ' + \
                   's3://test_bucket/SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip.sha256'
            assert captured[6] == 'uploaded /tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip.asc to ' + \
                   's3://test_bucket/SonarLint-for-Eclipse/releases/org.sonarlint.eclipse.site-7.9.0.63244.zip.asc'
            mock_upload_sonarlint_unzip.assert_called_with('SonarLint-for-Eclipse/releases/7.9.0.63244',
                                                           '/tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip')
            mock_upload_sonarlint_p2_site.assert_called_with('SonarLint-for-Eclipse/releases', 'SonarLint-for-Eclipse/releases/7.9.0.63244')


def test_upload_sonarlint_p2_site(capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client), \
        patch.object(client, 'upload_file') as upload_file:
        binaries = Binaries("test_bucket")
        binaries.upload_sonarlint_p2_site('SonarLint-for-Eclipse/releases', 'SonarLint-for-Eclipse/releases/7.9.0.63244')
        captured = capsys.readouterr().out.split('\n')
        assert captured[0] == 'uploaded compositeContent.xml to s3://test_bucket/SonarLint-for-Eclipse/releases/compositeContent.xml'
        assert captured[1] == 'uploaded compositeArtifacts.xml to s3://test_bucket/SonarLint-for-Eclipse/releases/compositeArtifacts.xml'
        upload_file.assert_has_calls([
            call('/tmp/compositeContent.xml', 'test_bucket', 'SonarLint-for-Eclipse/releases/compositeContent.xml'),
            call('/tmp/compositeArtifacts.xml', 'test_bucket', 'SonarLint-for-Eclipse/releases/compositeArtifacts.xml')
        ])
        for composite_file in ['compositeContent.xml', 'compositeArtifacts.xml']:
            document = parse(os.path.join(tempfile.gettempdir(), composite_file))
            assert document.getElementsByTagName('child')[-1].getAttribute(
                'location') == "https://binaries.sonarsource.com/SonarLint-for-Eclipse/releases/7.9.0.63244/"


def test_update_sonarlint_p2_site(capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client), \
        patch.object(client, 'create_invalidation') as create_invalidation:
        create_invalidation.return_value = {'Location': 'URI_123'}
        binaries = Binaries("test_bucket")
        binaries.update_sonarlint_p2_site('1234567890', '7.9.0.63244')
        captured = capsys.readouterr().out.split('\n')
        assert captured[0] == 'CloudFront invalidation: URI_123'
        create_invalidation.assert_called()
