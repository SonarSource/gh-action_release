import os
import tempfile
import zipfile
from io import StringIO

import boto3
import paramiko
from scp import SCPClient

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

    def upload(self, temp_file, filename, gid, aid, version):
        binaries_repo = self.get_binaries_repo(gid)

        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
            aid = "sonarqube"

        self.ssh_client.connect(hostname=self.binaries_host, username=self.binaries_ssh_user, pkey=self.private_ssh_key)

        # upload artifact
        # SonarLint Eclipse is uploaded to a special directory
        if aid == "org.sonarlint.eclipse.site":
            directory = f"{self.binaries_path_prefix}/SonarLint-for-Eclipse/releases"
            release_url = f"{self.binaries_url}/SonarLint-for-Eclipse/releases/{filename}"
        else:
            directory = f"{self.binaries_path_prefix}/{binaries_repo}/{aid}"
            release_url = f"{self.binaries_url}/{binaries_repo}/{aid}/{filename}"
        # create directory
        self.exec_ssh_command(f"mkdir -p {directory}")
        print(f'created {directory}')
        scp = SCPClient(self.ssh_client.get_transport())
        print('scp connexion created')
        # upload file to binaries
        scp.put(temp_file, remote_path=directory)
        print(f'uploaded {temp_file} to {directory}')
        for checksum in self.upload_checksums:
            scp.put(f'{temp_file}.{checksum}', remote_path=directory)
            print(f'uploaded {temp_file}.{checksum} to {directory}')
        scp.close()
        # SonarLint Eclipse is also unzipped on binaries for compatibility with P2 client
        if aid == "org.sonarlint.eclipse.site":
            sle_unzip_dir = f"{directory}/{version}"
            self.exec_ssh_command(f"mkdir -p {sle_unzip_dir}")
            self.exec_ssh_command(f"cd {sle_unzip_dir} && unzip ../org.sonarlint.eclipse.site-{version}.zip")
        self.ssh_client.close()
        return release_url

    def delete(self, filename, gid, aid, version):
        binaries_repo = self.get_binaries_repo(gid)

        if aid == "sonar-application":
            filename = f"sonarqube-{version}.zip"
            aid = "sonarqube"

        # delete artifact
        self.ssh_client.connect(hostname=self.binaries_host, username=self.binaries_ssh_user, pkey=self.private_ssh_key)

        directory = f"{self.binaries_path_prefix}/{binaries_repo}/{aid}"
        self.exec_ssh_command(f"rm {directory}/{filename}*")
        print(f'deleted {directory}/{filename}*')
        self.ssh_client.close()

    def get_binaries_repo(self, gid):
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
        binaries_repo = self.get_binaries_repo(gid)
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
                        client.upload_file(filename, self.binaries_bucket_name, f"{sle_unzip_bucket_key}/{root}/{filename})")
            print(f'uploaded content of {temp_file} to s3://{self.binaries_bucket_name}/{sle_unzip_bucket_key}')

    def s3_delete(self, filename, gid, aid, version):
        binaries_repo = self.get_binaries_repo(gid)
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
        # to_delete = list(bucket.list(prefix=bucket_key))
        # bucket.delete_keys(to_delete)
        print(f'deleted {bucket_key}*')
