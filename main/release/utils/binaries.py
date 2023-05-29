import os
import tempfile
import zipfile

import boto3
from datetime import datetime
from importlib import resources
from release import resources as file_resources
from xml.dom.minidom import parseString

OSS_REPO = "Distribution"
COMMERCIAL_REPO = "CommercialDistribution"
DISTRIBUTION_ID_PROD = 'E2WHX4O0Y6Z6C6'


class Binaries:
    upload_checksums = ["md5", "sha1", "sha256", "asc"]

    def __init__(self, binaries_bucket_name: str):
        self.binaries_bucket_name = binaries_bucket_name
        self.client = boto3.client('s3')

    @staticmethod
    def get_binaries_repo(gid):
        if gid.startswith('com.'):
            return COMMERCIAL_REPO
        else:
            return OSS_REPO

    def s3_upload(self, artifact_file, filename, gid, aid, version):
        # SonarLint Eclipse is uploaded to a special directory
        if aid == "org.sonarlint.eclipse.site":
            root_bucket_key = "SonarLint-for-Eclipse/releases"
        else:
            binaries_repo = Binaries.get_binaries_repo(gid)
            root_bucket_key = f"{binaries_repo}/{aid}"

        file_bucket_key = f"{root_bucket_key}/{filename}"
        self.client.upload_file(artifact_file, self.binaries_bucket_name, file_bucket_key)
        print(f'uploaded {artifact_file} to s3://{self.binaries_bucket_name}/{file_bucket_key}')
        for checksum in self.upload_checksums:
            self.client.upload_file(f'{artifact_file}.{checksum}', self.binaries_bucket_name, f'{file_bucket_key}.{checksum}')
            print(f'uploaded {artifact_file}.{checksum} to s3://{self.binaries_bucket_name}/{file_bucket_key}.{checksum}')

        # SonarLint
        if aid == "org.sonarlint.eclipse.site":
            version_bucket_key = f"{root_bucket_key}/{version}"
            self.upload_sonarlint_unzip(version_bucket_key, artifact_file)
            self.upload_sonarlint_p2_site(root_bucket_key, version_bucket_key)
            self.update_sonarlint_p2_site(DISTRIBUTION_ID_PROD, version)

    def upload_sonarlint_unzip(self, version_bucket_key, zip_file):
        """
        SonarLint Eclipse is also unzipped on binaries for compatibility with P2 client
        """
        with tempfile.TemporaryDirectory() as tmpdirname, zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)
            for root, _, files in os.walk(tmpdirname):
                for filename in files:
                    local_file = os.path.join(root, filename)
                    s3_file = os.path.join(version_bucket_key, os.path.relpath(local_file, tmpdirname))
                    print(f"upload {s3_file}")
                    self.client.upload_file(local_file, self.binaries_bucket_name, s3_file)
        print(f'uploaded content of {zip_file} to s3://{self.binaries_bucket_name}/{version_bucket_key}')

    def upload_sonarlint_p2_site(self, root_bucket_key, version_bucket_key):
        """
        Add the release to the SonarLint Eclipse P2 update site and upload
        """
        now_as_epoch_millis = str(round(datetime.utcnow().timestamp() * 1000))
        for composite_file in ['compositeContent.xml', 'compositeArtifacts.xml']:
            template = resources.read_text(file_resources, composite_file)
            document = parseString(template)
            document.getElementsByTagName('property')[0].setAttribute('value', now_as_epoch_millis)
            document.getElementsByTagName('child')[-1] \
                .setAttribute('location', f"https://binaries.sonarsource.com/{version_bucket_key}/")
            temp_file = f"{tempfile.gettempdir()}/{composite_file}"
            with open(temp_file, 'w') as output:
                document.writexml(output, encoding='UTF-8')
            composite_bucket_key = f"{root_bucket_key}/{composite_file}"
            self.client.upload_file(temp_file, self.binaries_bucket_name, composite_bucket_key)
            print(f'uploaded {composite_file} to s3://{self.binaries_bucket_name}/{composite_bucket_key}')

    @staticmethod
    def update_sonarlint_p2_site(distribution_id, version):
        """
        Create CloudFront invalidation to update the cache of SonarLint Eclipse P2 update site files
        """
        client = boto3.client('cloudfront')
        response = client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': 2,
                    'Items': [
                        '/SonarLint-for-Eclipse/releases/compositeContent.xml',
                        '/SonarLint-for-Eclipse/releases/compositeArtifacts.xml'
                    ]
                },
                'CallerReference': f"gh-action_release-SonarLint-{version}"
            }
        )
        invalidation_uri = response['Location']
        print(f'CloudFront invalidation: {invalidation_uri}')

    def s3_delete(self, filename, gid, aid):
        binaries_repo = Binaries.get_binaries_repo(gid)
        bucket_key = f"{binaries_repo}/{aid}/{filename}"

        self.client.delete_object(Bucket=self.binaries_bucket_name, Key=bucket_key)
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(self.binaries_bucket_name)
        objects = bucket.objects.filter(Prefix=f'{bucket_key}.')
        objects.delete()
        print(f'deleted {bucket_key}*')
