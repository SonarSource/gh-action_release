import os
import tempfile
import zipfile
from io import StringIO

import boto3
import paramiko

OSS_REPO = "Distribution"
COMMERCIAL_REPO = "CommercialDistribution"


class Binaries:
    binaries_host: str
    binaries_url: str
    binaries_ssh_user: str
    binaries_ssh_key: str
    binaries_path_prefix: str
    passphrase: str
    ssh_client = None
    private_ssh_key = None
    upload_checksums = ["md5", "sha1", "sha256", "asc"]

    def __init__(self, binaries_host: str, binaries_ssh_user: str, binaries_ssh_key: str, binaries_path_prefix: str,
                 binaries_bucket_name: str):
        self.binaries_host = binaries_host
        self.binaries_url = f"https://{binaries_host}"
        self.binaries_ssh_user = binaries_ssh_user
        self.binaries_ssh_key = binaries_ssh_key
        self.binaries_path_prefix = binaries_path_prefix
        self.binaries_bucket_name = binaries_bucket_name
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.private_ssh_key = paramiko.RSAKey.from_private_key(StringIO(self.binaries_ssh_key))

    @staticmethod
    def get_binaries_repo(gid):
        if gid.startswith('com.'):
            return COMMERCIAL_REPO
        else:
            return OSS_REPO

    def exec_ssh_command(self, command):
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        stdout_contents = '\n'.join(stdout.readlines())
        print(f"stdout: {stdout_contents}")
        stderr_contents = '\n'.join(stderr.readlines())
        print(f"stderr: {stderr_contents}")
        if stderr_contents:
            raise Exception(f"Error during the SSH command '{command}': {stderr_contents}")

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
            sle_unzip_bucket_key = f"{bucket_key}/{version}"
            with tempfile.TemporaryDirectory() as tmpdirname, zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
                for root, _, files in os.walk(tmpdirname):
                    for filename in files:
                        client.upload_file(os.path.join(root, filename), self.binaries_bucket_name, f"{sle_unzip_bucket_key}/{root}/{filename})")
            print(f'uploaded content of {temp_file} to s3://{self.binaries_bucket_name}/{sle_unzip_bucket_key}')

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
