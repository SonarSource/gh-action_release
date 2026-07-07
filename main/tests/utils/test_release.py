import tempfile
from unittest.mock import MagicMock, patch

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
def buildinfo_reddeer():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "org.sonarsource.eclipse.reddeer:org.eclipse.reddeer.site:zip",
                },
                "id": "org.sonarsource.eclipse.reddeer:org.eclipse.reddeer.core:4.7.0.53",
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


@fixture
def buildinfo_sonarqube_cli():
    return BuildInfo({
        "buildInfo": {
            "modules": [{
                "properties": {
                    "artifactsToPublish": "org.sonarsource.sonarqube:sonarqube-cli:zip:linux-x64",
                },
                "id": "org.sonarsource.sonarqube:sonarqube-cli:0.6.0.500",
            }]
        }
    })


def test_publish_artifact_s3_upload(buildinfo_com, buildinfo_org, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.jar",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        version = buildinfo_com.get_version()
        with patch('release.utils.binaries.Binaries.s3_upload') as s3_upload:
            # com
            publish_artifact(artifactory, binaries, buildinfo_com.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_once_with("/tmp/dummy-1.0.2.456.jar", "dummy-1.0.2.456.jar", "com.sonarsource.dummy", "dummy",
                                              "1.0.2.456", "")
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing com.sonarsource.dummy:dummy:jar#1.0.2.456"
            assert captured[1] == "com.sonarsource.dummy dummy jar "

            # org
            publish_artifact(artifactory, binaries, buildinfo_org.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_with("/tmp/dummy-1.0.2.456.jar", "dummy-1.0.2.456-qualifier.jar", "org.sonarsource.dummy", "dummy",
                                         "1.0.2.456", "qualifier")
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing org.sonarsource.dummy:dummy:jar:qualifier#1.0.2.456"
            assert captured[1] == "org.sonarsource.dummy dummy jar qualifier"


def test_publish_artifact_s3_upload_sonarqube(buildinfo_sonarqube, capsys):
    client = MagicMock()
    with patch('boto3.client', return_value=client):
        artifactory = MagicMock(**{'download.return_value': "/tmp/sonarqube-10.0.0.66185.zip",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        version = buildinfo_sonarqube.get_version()
        with patch('release.utils.binaries.Binaries.s3_upload') as s3_upload:
            publish_artifact(artifactory, binaries, buildinfo_sonarqube.get_artifacts_to_publish(), version, "repo")
            s3_upload.assert_called_once_with("/tmp/sonarqube-10.0.0.66185.zip", "sonarqube-10.0.0.66185.zip", 'org.sonarsource.sonarqube',
                                              'sonarqube', '10.0.0.66185', '')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == "publishing org.sonarsource.sonarqube:sonar-application:zip#10.0.0.66185"
            assert captured[1] == "org.sonarsource.sonarqube sonar-application zip "


def test_publish_artifact_upload_file_sonarqube_cli(buildinfo_sonarqube_cli, capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{'download.return_value': "/tmp/sonarqube-cli-0.6.0.500-linux-x64.zip",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_eclipse_update_site_unzip') as mock_upload_eclipse_update_site_unzip, \
            patch.object(binaries, 'upload_sonarlint_p2_site') as mock_upload_sonarlint_p2_site, \
            patch.object(client, 'upload_file') as upload_file:
            version = buildinfo_sonarqube_cli.get_version()
            publish_artifact(artifactory, binaries, buildinfo_sonarqube_cli.get_artifacts_to_publish(), version, "repo")
            upload_file.assert_called_with(
                '/tmp/sonarqube-cli-0.6.0.500-linux-x64.zip.asc', 'test_bucket',
                'Distribution/sonarqube-cli/0.6.0.500/linux/sonarqube-cli-0.6.0.500-linux-x64.zip.asc')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'publishing org.sonarsource.sonarqube:sonarqube-cli:zip:linux-x64#0.6.0.500'
            assert captured[1] == 'org.sonarsource.sonarqube sonarqube-cli zip linux-x64'
            assert captured[2] == 'uploaded /tmp/sonarqube-cli-0.6.0.500-linux-x64.zip to s3://test_bucket/Distribution/sonarqube-cli/0.6.0.500/linux/sonarqube-cli-0.6.0.500-linux-x64.zip'
            mock_upload_eclipse_update_site_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()


def test_publish_artifact_upload_file(buildinfo_com, buildinfo_org, capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.jar",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_eclipse_update_site_unzip') as mock_upload_eclipse_update_site_unzip, \
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
            mock_upload_eclipse_update_site_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()
            # org (with qualifier: flat path — hierarchical layout is only for sonarqube-cli)
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
            mock_upload_eclipse_update_site_unzip.assert_not_called()
            mock_upload_sonarlint_p2_site.assert_not_called()


def test_publish_artifact_upload_file_sonarlint(buildinfo_sonarlint, capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{'download.return_value': "/tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_eclipse_update_site_unzip') as mock_upload_eclipse_update_site_unzip, \
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
            mock_upload_eclipse_update_site_unzip.assert_called_with('SonarLint-for-Eclipse/releases/7.9.0.63244',
                                                           '/tmp/org.sonarlint.eclipse.site-7.9.0.63244.zip')
            mock_upload_sonarlint_p2_site.assert_called_with('SonarLint-for-Eclipse/releases', 'SonarLint-for-Eclipse/releases/7.9.0.63244')


def test_publish_artifact_upload_file_reddeer(buildinfo_reddeer, capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{'download.return_value': "/tmp/org.eclipse.reddeer.site-4.7.0.53.zip",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        with patch.object(binaries, 'upload_eclipse_update_site_unzip') as mock_upload_eclipse_update_site_unzip, \
            patch.object(binaries, 'upload_sonarlint_p2_site') as mock_upload_sonarlint_p2_site, \
            patch.object(client, 'upload_file') as upload_file:
            version = buildinfo_reddeer.get_version()
            publish_artifact(artifactory, binaries, buildinfo_reddeer.get_artifacts_to_publish(), version, "repo")
            upload_file.assert_called_with('/tmp/org.eclipse.reddeer.site-4.7.0.53.zip.sha256', 'test_bucket',
                                           'RedDeer/releases/org.eclipse.reddeer.site-4.7.0.53.zip.sha256')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'publishing org.sonarsource.eclipse.reddeer:org.eclipse.reddeer.site:zip#4.7.0.53'
            assert captured[1] == 'org.sonarsource.eclipse.reddeer org.eclipse.reddeer.site zip '
            assert captured[2] == 'uploaded /tmp/org.eclipse.reddeer.site-4.7.0.53.zip to ' + \
                   's3://test_bucket/RedDeer/releases/org.eclipse.reddeer.site-4.7.0.53.zip'
            mock_upload_eclipse_update_site_unzip.assert_called_with('RedDeer/releases/4.7.0.53',
                                                           '/tmp/org.eclipse.reddeer.site-4.7.0.53.zip')
            mock_upload_sonarlint_p2_site.assert_not_called()


def test_revoke_publish_artifact():
    artifactory = MagicMock()
    binaries = MagicMock()
    publish_artifact(artifactory, binaries, "groupId:artefactId:ext", "version", "repo", True)
    artifactory.assert_not_called()
    binaries.s3_delete.assert_called_once_with('artefactId-version.ext', 'groupId', 'artefactId', 'version', '')
    binaries.s3_delete_sbom.assert_called_once_with('artefactId-version.sbom.json', 'groupId', 'artefactId', 'version', '')


def test_publish_artifact_uploads_sbom(buildinfo_sonarqube):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    sbom_local = f"{tempfile.gettempdir()}/sonar-application-10.0.0.66185-cyclonedx.json"
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{
            'download.return_value': f"{tempfile.gettempdir()}/sonarqube-10.0.0.66185.zip",
            'find_sbom_filename.return_value': "sonar-application-10.0.0.66185-cyclonedx.json",
            'download_named.return_value': (sbom_local, ["asc"]),
        })
        binaries = Binaries("test_bucket")
        with patch.object(client, 'upload_file') as upload_file:
            version = buildinfo_sonarqube.get_version()
            publish_artifact(artifactory, binaries, buildinfo_sonarqube.get_artifacts_to_publish(), version, "repo")

            # SBOM is discovered using the original aid (sonar-application), not the s3 aid.
            artifactory.find_sbom_filename.assert_called_once_with(
                "repo", "org.sonarsource.sonarqube", "sonar-application", "10.0.0.66185")
            artifactory.download_named.assert_called_once_with(
                "repo", "org.sonarsource.sonarqube", "sonar-application", "10.0.0.66185",
                "sonar-application-10.0.0.66185-cyclonedx.json",
                checksums=["md5", "sha1", "sha256"], optional_checksums=["asc"])
            # SBOM uploaded next to the binary with the normalized name + checksums (incl. .asc).
            sbom_key = "Distribution/sonarqube/sonarqube-10.0.0.66185.sbom.json"
            upload_file.assert_any_call(sbom_local, "test_bucket", sbom_key)
            upload_file.assert_any_call(f"{sbom_local}.asc", "test_bucket", f"{sbom_key}.asc")


def test_publish_artifact_skips_when_no_sbom(buildinfo_org, capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        artifactory = MagicMock(**{'download.return_value': "/tmp/dummy-1.0.2.456.jar",
                                   'find_sbom_filename.return_value': None})
        binaries = Binaries("test_bucket")
        version = buildinfo_org.get_version()
        publish_artifact(artifactory, binaries, buildinfo_org.get_artifacts_to_publish(), version, "repo")
        artifactory.download_named.assert_not_called()
        assert "no SBOM found for org.sonarsource.dummy:dummy:1.0.2.456 - skipping SBOM upload" \
               in capsys.readouterr().out
