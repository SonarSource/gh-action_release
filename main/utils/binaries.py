import os
import tempfile
import zipfile

import boto3

OSS_REPO = "Distribution"
COMMERCIAL_REPO = "CommercialDistribution"


class Binaries:
    upload_checksums = ["md5", "sha1", "sha256", "asc"]

    def __init__(self, binaries_bucket_name: str):
        self.binaries_bucket_name = binaries_bucket_name

    @staticmethod
    def get_binaries_repo(gid):
        if gid.startswith('com.'):
            return COMMERCIAL_REPO
        else:
            return OSS_REPO

    def s3_upload(self, temp_file, filename, gid, aid, version):
        binaries_repo = Binaries.get_binaries_repo(gid)
        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
            aid = "sonarqube"
        # SonarLint Eclipse is uploaded to a special directory
        if aid == "org.sonarlint.eclipse.site":
            bucket_key = f"SonarLint-for-Eclipse/releases/{filename}"
        else:
            bucket_key = f"{binaries_repo}/{aid}/{filename}"

        client = boto3.client('s3')
        client.upload_file(temp_file, self.binaries_bucket_name, bucket_key)
        print(f'uploaded {temp_file} to s3://{self.binaries_bucket_name}/{bucket_key}')
        for checksum in self.upload_checksums:
            client.upload_file(f'{temp_file}.{checksum}', self.binaries_bucket_name, f'{bucket_key}.{checksum}')
            print(f'uploaded {temp_file}.{checksum} to s3://{self.binaries_bucket_name}/{bucket_key}.{checksum}')

        # SonarLint Eclipse is also unzipped on binaries for compatibility with P2 client
        if aid == "org.sonarlint.eclipse.site":
            bucket_key = f"SonarLint-for-Eclipse/releases/{version}"
            with tempfile.TemporaryDirectory() as tmpdirname, zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
                for root, _, files in os.walk(tmpdirname):
                    for filename in files:
                        local_file = os.path.join(root, filename)
                        s3_file = os.path.join(bucket_key, os.path.relpath(local_file, tmpdirname))
                        print(f"upload {s3_file}")
                        client.upload_file(local_file, self.binaries_bucket_name, s3_file)
            print(f'uploaded content of {temp_file} to s3://{self.binaries_bucket_name}/{bucket_key}')

    def s3_delete(self, filename, gid, aid, version):
        binaries_repo = Binaries.get_binaries_repo(gid)
        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
            aid = "sonarqube"
        bucket_key = f"{binaries_repo}/{aid}/{filename}"

        client = boto3.client('s3')
        client.delete_object(Bucket=self.binaries_bucket_name, Key=bucket_key)
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(self.binaries_bucket_name)
        objects = bucket.objects.filter(Prefix=f'{bucket_key}.')
        objects.delete()
        print(f'deleted {bucket_key}*')
