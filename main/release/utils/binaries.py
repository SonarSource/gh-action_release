import os
import tempfile
import zipfile

import boto3
from datetime import datetime, timezone
from importlib import resources
from release import resources as file_resources
from xml.dom.minidom import parseString

from release.vars import binaries_aws_region_name, binaries_aws_session_token, binaries_aws_secret_access_key, binaries_aws_access_key_id

OSS_REPO = "Distribution"
COMMERCIAL_REPO = "CommercialDistribution"
DISTRIBUTION_ID_PROD = 'E2WHX4O0Y6Z6C6'
SONARLINT_AID = "org.sonarlint.eclipse.site"
REDDEER_AID = "org.eclipse.reddeer.site"
UPLOAD_CHECKSUMS = ["md5", "sha1", "sha256", "asc"]


class Binaries:
    def __init__(self, binaries_bucket_name: str):
        self.binaries_bucket_name = binaries_bucket_name
        self.binaries_session = boto3.Session(
            aws_access_key_id=binaries_aws_access_key_id,
            aws_secret_access_key=binaries_aws_secret_access_key,
            aws_session_token=binaries_aws_session_token,
            region_name=binaries_aws_region_name
        )
        self.s3_client = self.binaries_session.client('s3')
        self.cloudfront_client = self.binaries_session.client('cloudfront')

    @staticmethod
    def get_binaries_repo(gid):
        if gid.startswith('com.'):
            return COMMERCIAL_REPO
        else:
            return OSS_REPO

    @staticmethod
    def get_actual_checksums(aid):
        if aid == REDDEER_AID:
            # Eclipse RedDeer does not have a ".asc" signature
            return UPLOAD_CHECKSUMS[:-1]
        return UPLOAD_CHECKSUMS

    def s3_upload(self, artifact_file, filename, gid, aid, version):
        root_bucket_key = self.get_file_bucket_key(aid, gid)
        file_bucket_key = f"{root_bucket_key}/{filename}"

        self.s3_client.upload_file(artifact_file, self.binaries_bucket_name, file_bucket_key)
        print(f'uploaded {artifact_file} to s3://{self.binaries_bucket_name}/{file_bucket_key}')
        for checksum in Binaries.get_actual_checksums(aid):
            self.s3_client.upload_file(f'{artifact_file}.{checksum}', self.binaries_bucket_name, f'{file_bucket_key}.{checksum}')
            print(f'uploaded {artifact_file}.{checksum} to s3://{self.binaries_bucket_name}/{file_bucket_key}.{checksum}')

        version_bucket_key = f"{root_bucket_key}/{version}"

        if aid == SONARLINT_AID:
            # SonarQube for IDE (formerly SonarLint)
            self.upload_eclipse_update_site_unzip(version_bucket_key, artifact_file)
            self.upload_sonarlint_p2_site(root_bucket_key, version_bucket_key)
            self.update_sonarlint_p2_site(DISTRIBUTION_ID_PROD, version)
        elif aid == REDDEER_AID:
            # Eclipse RedDeer fork. Does not require the composite XML files as it is only used
            # internally anyway and the update process inside SonarSource/sonarlint-eclipse is done
            # manually to not break something by relying on the "latest" released artifact!
            self.upload_eclipse_update_site_unzip(version_bucket_key, artifact_file)

    def get_file_bucket_key(self, aid, gid):
        # SonarLint Eclipse is uploaded to a special directory
        if aid == SONARLINT_AID:
            return "SonarLint-for-Eclipse/releases"
        elif aid == REDDEER_AID:
            return "RedDeer/releases"
        binaries_repo = Binaries.get_binaries_repo(gid)
        return f"{binaries_repo}/{aid}"

    def upload_eclipse_update_site_unzip(self, version_bucket_key, zip_file):
        """
        An Eclipse Update Site is also unzipped on binaries for compatibility with P2 clients like
        the "Installation Wizard" of the Eclipse IDE!
        """
        with tempfile.TemporaryDirectory() as tmpdirname, zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)
            for root, _, files in os.walk(tmpdirname):
                for filename in files:
                    local_file = os.path.join(root, filename)
                    s3_file = os.path.join(version_bucket_key, os.path.relpath(local_file, tmpdirname))
                    print(f"upload {s3_file}")
                    self.s3_client.upload_file(local_file, self.binaries_bucket_name, s3_file)
        print(f'uploaded content of {zip_file} to s3://{self.binaries_bucket_name}/{version_bucket_key}')

    def upload_sonarlint_p2_site(self, root_bucket_key, version_bucket_key):
        """
        Add the release to the SonarLint Eclipse P2 update site and upload
        """
        now_as_epoch_millis = str(round(datetime.now(timezone.utc).timestamp() * 1000))
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
            self.s3_client.upload_file(temp_file, self.binaries_bucket_name, composite_bucket_key)
            print(f'uploaded {composite_file} to s3://{self.binaries_bucket_name}/{composite_bucket_key}')

    def update_sonarlint_p2_site(self, distribution_id, version):
        """
        Create CloudFront invalidation to update the cache of SonarLint Eclipse P2 update site files
        """
        client = self.cloudfront_client
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

    def s3_delete(self, filename, gid, aid, version):
        root_bucket_key = self.get_file_bucket_key(aid, gid)
        bucket_key = f"{root_bucket_key}/{filename}"

        self.s3_client.delete_object(Bucket=self.binaries_bucket_name, Key=bucket_key)
        print(f'deleted {bucket_key}')

        if aid == SONARLINT_AID:
            version_bucket_key = f"{root_bucket_key}/{version}/"
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(self.binaries_bucket_name)
            objects = bucket.objects.filter(Prefix=f'{version_bucket_key}')
            objects.delete()
            print(f'deleted {version_bucket_key}')
