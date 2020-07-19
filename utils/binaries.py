import os

import paramiko
from scp import SCPClient

OSS_REPO = "Distribution"

binaries_path_prefix = os.environ.get('PATH_PREFIX', '/tmp')
passphrase = os.environ.get('GPG_PASSPHRASE', 'no GPG_PASSPHRASE in env')

binaries_host = 'binaries.sonarsource.com'
binaries_url = f"https://{binaries_host}"
ssh_user = 'ssuopsa'
ssh_key = 'id_rsa_ssuopsa'

def upload(tempfile, filename, aid, version):
    binaries_repo = OSS_REPO

    # upload artifact
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(hostname=binaries_host, username=ssh_user, key_filename=ssh_key)
    # SonarLint Eclipse is uploaded to a special directory
    if aid == "org.sonarlint.eclipse.site":
        directory = f"{binaries_path_prefix}/SonarLint-for-Eclipse/releases"
        release_url = f"{binaries_url}/SonarLint-for-Eclipse/releases/{filename}"
    else:
        directory = f"{binaries_path_prefix}/{binaries_repo}/{aid}"
        release_url = f"{binaries_url}/{binaries_repo}/{aid}/{filename}"
    # create directory
    exec_ssh_command(ssh_client, f"mkdir -p {directory}")
    print(f'created {directory}')
    scp = SCPClient(ssh_client.get_transport())
    print('scp connexion created')
    # upload file to binaries
    scp.put(tempfile, remote_path=directory)
    print(f'uploaded {tempfile} to {directory}')
    scp.close()
    # SonarLint Eclipse is also unzipped on binaries for compatibility with P2 client
    if aid == "org.sonarlint.eclipse.site":
        sle_unzip_dir = f"{directory}/{version}"
        exec_ssh_command(ssh_client, f"mkdir -p {sle_unzip_dir}")
        exec_ssh_command(ssh_client, f"cd {sle_unzip_dir} && unzip ../org.sonarlint.eclipse.site-{version}.zip")
    # sign file
    exec_ssh_command(ssh_client,
                     f"gpg --batch --passphrase {passphrase} --armor --detach-sig --default-key infra@sonarsource.com {directory}/{filename}")
    print(f'signed {directory}/{filename}')
    ssh_client.close()
    return release_url


def exec_ssh_command(ssh_client, command):
    stdin, stdout, stderr = ssh_client.exec_command(command)
    stdout_contents = '\n'.join(stdout.readlines())
    print(f"stdout: {stdout_contents}")
    stderr_contents = '\n'.join(stderr.readlines())
    print(f"stderr: {stderr_contents}")
    if stderr_contents:
        raise Exception(f"Error during the SSH command '{command}': {stderr_contents}")