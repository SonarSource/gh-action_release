import os
import tempfile
from unittest.mock import patch, MagicMock, call
from xml.dom.minidom import parse

from release.utils.binaries import Binaries


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
            call(f'{tempfile.gettempdir()}/compositeContent.xml', 'test_bucket', 'SonarLint-for-Eclipse/releases/compositeContent.xml'),
            call(f'{tempfile.gettempdir()}/compositeArtifacts.xml', 'test_bucket', 'SonarLint-for-Eclipse/releases/compositeArtifacts.xml')
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
