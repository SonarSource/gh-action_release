import os
import tempfile
from unittest.mock import patch, MagicMock, call
from xml.dom.minidom import parse

import pytest

from release.utils.binaries import Binaries, SONARLINT_AID


def test_upload_sonarlint_p2_site(capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session), \
        patch.object(client, 'upload_file') as upload_file:
        binaries = Binaries("test_bucket")
        binaries.upload_sonarlint_p2_site('SonarLint-for-Eclipse/releases', 'SonarLint-for-Eclipse/releases/7.9.0.63244')
        captured = capsys.readouterr().out.split('\n')
        assert captured[0] == 'uploaded compositeContent.xml to s3://test_bucket/SonarLint-for-Eclipse/releases/compositeContent.xml'
        assert captured[
                   1] == 'uploaded compositeArtifacts.xml to s3://test_bucket/SonarLint-for-Eclipse/releases/compositeArtifacts.xml'
        upload_file.assert_has_calls([
            call(f'{tempfile.gettempdir()}/compositeContent.xml', 'test_bucket', 'SonarLint-for-Eclipse/releases/compositeContent.xml'),
            call(f'{tempfile.gettempdir()}/compositeArtifacts.xml', 'test_bucket',
                 'SonarLint-for-Eclipse/releases/compositeArtifacts.xml')
        ])
        for composite_file in ['compositeContent.xml', 'compositeArtifacts.xml']:
            document = parse(os.path.join(tempfile.gettempdir(), composite_file))
            assert document.getElementsByTagName('child')[-1].getAttribute(
                'location') == "https://binaries.sonarsource.com/SonarLint-for-Eclipse/releases/7.9.0.63244/"


def test_update_sonarlint_p2_site(capsys):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        with patch.object(client, 'create_invalidation') as create_invalidation:
            create_invalidation.return_value = {'Location': 'URI_123'}
            binaries = Binaries("test_bucket")
            binaries.update_sonarlint_p2_site('1234567890', '7.9.0.63244')
            captured = capsys.readouterr().out.split('\n')
            assert captured[0] == 'CloudFront invalidation: URI_123'
            create_invalidation.assert_called()


def test_s3_delete_sonarlint_eclipse():
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        resource = MagicMock()
        with patch('boto3.resource', return_value=resource):
            bucket = MagicMock()
            with patch.object(resource, 'Bucket', return_value=bucket):
                Binaries('bucket').s3_delete('filename', 'whatever', SONARLINT_AID, 'version')
    client.delete_object.assert_called_once_with(Bucket='bucket', Key='SonarLint-for-Eclipse/releases/filename')
    bucket.objects.filter.assert_called_once_with(Prefix='SonarLint-for-Eclipse/releases/version/')
    bucket.objects.filter.return_value.delete.assert_called_once()


def test_qual_to_platform_folder():
    assert Binaries.qual_to_platform_folder(None) is None
    assert Binaries.qual_to_platform_folder('') is None
    assert Binaries.qual_to_platform_folder('linux-x64') == 'linux'
    assert Binaries.qual_to_platform_folder('darwin-arm64') == 'mac'
    assert Binaries.qual_to_platform_folder('win32-x64') == 'windows'
    assert Binaries.qual_to_platform_folder('unknown-platform') == 'unknown'


def test_use_hierarchical_qualifier_layout():
    assert Binaries.use_hierarchical_qualifier_layout('sonarqube-cli', 'linux-x64') is True
    assert Binaries.use_hierarchical_qualifier_layout('sonarqube-cli', '') is False
    assert Binaries.use_hierarchical_qualifier_layout('sonar-scanner-cli', 'linux-x64') is False
    assert Binaries.use_hierarchical_qualifier_layout('dummy', 'cyclonedx') is False


@pytest.mark.parametrize(
    'group_id, root_bucket_key',
    [
        ('org.whatever', 'Distribution'),
        ('com.whatever', 'CommercialDistribution')
    ]
)
def test_s3_delete_common_case(group_id, root_bucket_key):
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        Binaries('bucket').s3_delete('filename', group_id, "aid", 'version')
    client.delete_object.assert_called_once_with(Bucket='bucket', Key=f'{root_bucket_key}/aid/filename')


def test_s3_delete_sonarqube_cli_qualified():
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        Binaries('bucket').s3_delete(
            'sonarqube-cli-1.0.0-linux-x64.zip', 'org.sonarsource.sonarqube', 'sonarqube-cli', '1.0.0', 'linux-x64')
    client.delete_object.assert_called_once_with(
        Bucket='bucket', Key='Distribution/sonarqube-cli/1.0.0/linux/sonarqube-cli-1.0.0-linux-x64.zip')


def test_s3_delete_non_cli_qualified_deletes_flat_and_legacy_hierarchical():
    binaries_session = MagicMock()
    client = MagicMock()
    binaries_session.client.return_value = client
    with patch('boto3.Session', return_value=binaries_session):
        Binaries('bucket').s3_delete(
            'other-1.0.0-linux-x64.zip', 'org.sonarsource.foo', 'other', '1.0.0', 'linux-x64')
    client.delete_object.assert_has_calls([
        call(Bucket='bucket', Key='Distribution/other/other-1.0.0-linux-x64.zip'),
        call(Bucket='bucket', Key='Distribution/other/1.0.0/linux/other-1.0.0-linux-x64.zip')
    ])
    assert client.delete_object.call_count == 2
