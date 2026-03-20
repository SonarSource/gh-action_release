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

# Hierarchical S3 layout (product/version/platform/file) for qualified artifacts is limited to
# sonarqube-cli only (PREQ-4535). All other artifact IDs keep the legacy flat path.
SONARQUBE_CLI_AID = "sonarqube-cli"

# Map artifact qualifier (e.g. linux-x64, darwin-arm64) to folder name for hierarchical S3 structure
# (used only when aid == SONARQUBE_CLI_AID and qual is set).
QUAL_TO_PLATFORM_FOLDER = {
    "linux": "linux",
    "linux-x64": "linux",
    "linux-arm64": "linux",
    "linux-arm": "linux",
    "darwin": "mac",
    "darwin-x64": "mac",
    "darwin-arm64": "mac",
    "mac": "mac",
    "mac-x64": "mac",
    "macos-x64": "mac",
    "win32": "windows",
    "win32-x64": "windows",
    "win32-arm64": "windows",
    "windows": "windows",
    "windows-x64": "windows",
}


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

    @staticmethod
    def qual_to_platform_folder(qual):
        """Map artifact qualifier to platform folder for hierarchical S3 structure."""
        if not qual:
            return None
        folder = QUAL_TO_PLATFORM_FOLDER.get(qual.lower())
        if folder:
            return folder
        # Fallback: use first segment before hyphen (e.g. linux-x64 -> linux)
        return qual.split("-")[0].lower() if "-" in qual else qual.lower()

    @staticmethod
    def use_hierarchical_qualifier_layout(aid, qual):
        return bool(qual) and aid == SONARQUBE_CLI_AID

    def get_flat_bucket_key(self, root_bucket_key, filename):
        return f"{root_bucket_key}/{filename}"

    def get_hierarchical_bucket_key(self, root_bucket_key, filename, version, qual):
        platform_folder = self.qual_to_platform_folder(qual)
        return f"{root_bucket_key}/{version}/{platform_folder}/{filename}"

    def s3_upload(self, artifact_file, filename, gid, aid, version, qual=None):
        root_bucket_key = self.get_file_bucket_key(aid, gid)
        if Binaries.use_hierarchical_qualifier_layout(aid, qual):
            file_bucket_key = self.get_hierarchical_bucket_key(root_bucket_key, filename, version, qual)
        else:
            file_bucket_key = self.get_flat_bucket_key(root_bucket_key, filename)

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

    def s3_delete(self, filename, gid, aid, version, qual=None):
        root_bucket_key = self.get_file_bucket_key(aid, gid)
        bucket_keys = [self.get_flat_bucket_key(root_bucket_key, filename)]
        if Binaries.use_hierarchical_qualifier_layout(aid, qual):
            bucket_keys = [self.get_hierarchical_bucket_key(root_bucket_key, filename, version, qual)]
        elif qual:
            # Backward compatibility for artifacts published by v6.4.0, where all qualifiers
            # used the hierarchical version/platform layout.
            bucket_keys.append(self.get_hierarchical_bucket_key(root_bucket_key, filename, version, qual))

        for bucket_key in dict.fromkeys(bucket_keys):
            self.s3_client.delete_object(Bucket=self.binaries_bucket_name, Key=bucket_key)
            print(f'deleted {bucket_key}')

        if aid == SONARLINT_AID:
            version_bucket_key = f"{root_bucket_key}/{version}/"
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(self.binaries_bucket_name)
            objects = bucket.objects.filter(Prefix=f'{version_bucket_key}')
            objects.delete()
            print(f'deleted {version_bucket_key}')
