#!/usr/bin/env python3
"""
Upload missing artifacts from Repox (Artifactory) to binaries.sonarsource.com (S3).

This script:
1. Reads a file containing URLs to artifacts on binaries.sonarsource.com
2. For each URL, extracts the artifact name and version
3. Downloads the artifact and its signature (.asc) from Repox using JFrog CLI
4. Uploads both files to the S3 bucket at the same path structure

Usage:
    # Process URLs from file
    python3 scripts/re-sign/upload_missing_to_binaries.py --urls-file <FILE> [--bucket <BUCKET>] [--dry-run]

Environment Variables:
    VAULT_TOKEN - Vault authentication token (required)
    VAULT_ADDR - Vault URL (default: https://vault.sonar.build:8200)

    JFROG_CLI_* - JFrog CLI configuration (URL, access token, etc.)

    AWS credentials (standard AWS env vars preferred, BINARIES_AWS_* supported for backward compatibility):
    AWS_ACCESS_KEY_ID - AWS access key ID (or BINARIES_AWS_ACCESS_KEY_ID)
    AWS_SECRET_ACCESS_KEY - AWS secret access key (or BINARIES_AWS_SECRET_ACCESS_KEY)
    AWS_SESSION_TOKEN - AWS session token (optional, or BINARIES_AWS_SESSION_TOKEN)
    AWS_DEFAULT_REGION - AWS region (or AWS_REGION or BINARIES_AWS_DEFAULT_REGION, default: eu-central-1)

    BINARIES_AWS_DEPLOY - AWS S3 bucket name (default: downloads-cdn-eu-central-1-prod)

Dry Run Mode:
    Use --dry-run to display download URLs from Repox without actually downloading or uploading.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

import boto3

# Add scripts/re-sign directory to path to import utilities
sys.path.insert(0, str(Path(__file__).parent))
# Add main directory to path to import release.vars
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'main'))

import pgp_utils
import vault_utils

try:
    from release.vars import binaries_bucket_name
except ImportError:
    binaries_bucket_name = None


def parse_binaries_url(url: str) -> tuple[str, str, str, str]:
    """Parse a binaries.sonarsource.com URL to extract distribution, artifact name, version, and S3 key.

    Args:
        url: Full URL to the artifact (e.g., https://binaries.sonarsource.com/CommercialDistribution/sonar-ruby-plugin/sonar-ruby-plugin-1.19.0.471.jar)

    Returns:
        Tuple of (distribution, artifact_name, version, s3_key)
        Example: ("CommercialDistribution", "sonar-ruby-plugin", "1.19.0.471", "CommercialDistribution/sonar-ruby-plugin/sonar-ruby-plugin-1.19.0.471.jar")
    """
    parsed = urllib.parse.urlparse(url)

    # Extract path after domain (e.g., "/CommercialDistribution/sonar-ruby-plugin/sonar-ruby-plugin-1.19.0.471.jar")
    path = parsed.path.lstrip('/')

    if not path:
        raise ValueError(f"Invalid URL: could not extract path from {url}")

    # Split path into parts
    parts = path.split('/')
    if len(parts) < 3:
        raise ValueError(f"Invalid URL format: expected at least 3 path components in {url}")

    distribution = parts[0]  # CommercialDistribution or Distribution
    artifact_name = parts[1]  # sonar-ruby-plugin
    filename = parts[2]       # sonar-ruby-plugin-1.19.0.471.jar

    # Extract version from filename
    # Pattern: artifact-name-VERSION.jar
    # Remove .jar extension
    name_without_ext = filename.replace('.jar', '')
    # Remove artifact name prefix
    version_part = name_without_ext.replace(f"{artifact_name}-", '', 1)

    if not version_part:
        raise ValueError(f"Could not extract version from filename: {filename}")

    return distribution, artifact_name, version_part, path


def search_artifact_in_repox(artifact_name: str, version: str, dry_run: bool = False) -> str:
    """Search for an artifact in Repox to find its actual path.

    Args:
        artifact_name: Artifact name (e.g., "sonar-ruby-plugin")
        version: Version (e.g., "1.19.0.471")
        dry_run: If True, only print the search command

    Returns:
        Full path to the artifact in Repox (e.g., "sonarsource/com/sonarsource/ruby/sonar-ruby-plugin/1.19.0.471/sonar-ruby-plugin-1.19.0.471.jar")
    """
    # Search in the sonarsource repository (contains both private and public)
    search_pattern = f"sonarsource/**/{artifact_name}-{version}.jar"

    if dry_run:
        print(f"  [DRY RUN] Would search in Repox: {search_pattern}")
        return f"sonarsource/path/to/{artifact_name}/{version}/{artifact_name}-{version}.jar"

    print(f"  Searching in Repox: {search_pattern}")

    # Use JFrog CLI to search
    cmd = [
        'jfrog', 'rt', 'search',
        search_pattern,
        '--limit=1'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # Parse JSON output
        import json
        search_results = json.loads(result.stdout)

        if not search_results:
            raise ValueError(f"Artifact not found in Repox: {artifact_name}-{version}.jar")

        # Get the first result's path
        artifact_path = search_results[0].get('path')
        if not artifact_path:
            raise ValueError(f"Invalid search result for {artifact_name}-{version}.jar")

        print(f"  ✓ Found in Repox: {artifact_path}")
        return artifact_path

    except subprocess.CalledProcessError as e:
        raise ValueError(f"Error searching Repox: {e.stderr}")


def extract_directory_from_path(artifact_path: str) -> str:
    """Extract the directory path from a full artifact path.

    Args:
        artifact_path: Full path to artifact (e.g., "com/sonarsource/ruby/sonar-ruby-plugin/1.19.0.471/sonar-ruby-plugin-1.19.0.471.jar")

    Returns:
        Directory path (e.g., "com/sonarsource/ruby/sonar-ruby-plugin/1.19.0.471")
    """
    return '/'.join(artifact_path.split('/')[:-1])


def download_from_repox(
    artifact_dir_path: str,
    artifact_name: str,
    version: str,
    temp_dir: str,
    dry_run: bool = False
) -> list[str]:
    """Download artifacts from Repox using JFrog CLI.

    Args:
        artifact_dir_path: Directory path in Repox (e.g., "sonarsource/com/sonarsource/ruby/sonar-ruby-plugin/1.19.0.471")
        artifact_name: Artifact name (e.g., "sonar-ruby-plugin")
        version: Version (e.g., "1.19.0.471")
        temp_dir: Temporary directory to download to
        dry_run: If True, only print the download command

    Returns:
        List of downloaded file paths (excluding .asc files)
    """
    # Construct download pattern - exclude .asc files since we'll sign ourselves
    artifact_pattern = f"{artifact_name}-{version}.*"
    download_pattern = f"{artifact_dir_path}/{artifact_pattern}"

    if dry_run:
        print(f"  [DRY RUN] Would download from Repox: {download_pattern}")
        return []

    # Use JFrog CLI to download, excluding .asc files
    # jfrog rt download <pattern> <target> --flat=false --exclusions="*.asc"
    cmd = [
        'jfrog', 'rt', 'download',
        download_pattern,
        temp_dir + '/',
        '--flat=false',
        '--exclusions=*.asc'
    ]

    print(f"  Downloading from Repox: {download_pattern}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        # List all files in temp_dir to find what was downloaded (excluding .asc)
        downloaded_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if not file.endswith('.asc'):
                    file_path = os.path.join(root, file)
                    downloaded_files.append(file_path)

        print(f"  ✓ Downloaded {len(downloaded_files)} file(s)")
        return downloaded_files

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error downloading from Repox: {e}")
        print(f"  stdout: {e.stdout}")
        print(f"  stderr: {e.stderr}")
        return []


def upload_to_s3(
    local_path: str,
    s3_key: str,
    bucket_name: str,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None,
    region: str = 'eu-central-1',
    dry_run: bool = False
) -> None:
    """Upload a file to S3.

    Args:
        local_path: Local path to the file
        s3_key: S3 key (path) for the file
        bucket_name: S3 bucket name
        aws_access_key_id: AWS access key ID (optional)
        aws_secret_access_key: AWS secret access key (optional)
        aws_session_token: AWS session token (optional)
        region: AWS region
        dry_run: If True, only print the destination
    """
    destination = f"s3://{bucket_name}/{s3_key}"

    if dry_run:
        print(f"  [DRY RUN] Would upload to {destination}")
        return

    print(f"  Uploading to {destination}...")

    # Create S3 client
    session_kwargs = {'region_name': region}
    if aws_access_key_id and aws_secret_access_key:
        session_kwargs['aws_access_key_id'] = aws_access_key_id
        session_kwargs['aws_secret_access_key'] = aws_secret_access_key
        if aws_session_token:
            session_kwargs['aws_session_token'] = aws_session_token

    session = boto3.Session(**session_kwargs)
    s3_client = session.client('s3')

    # Upload the file
    s3_client.upload_file(local_path, bucket_name, s3_key)

    print(f"  ✓ Uploaded to {destination}")


def read_urls_from_file(file_path: str) -> list[str]:
    """Read URLs from a text file.

    Args:
        file_path: Path to the text file containing URLs

    Returns:
        List of URLs (stripped of whitespace and list markers)
    """
    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Remove list markers (-, *, •, etc.) and leading/trailing spaces
            line = re.sub(r'^[-*•]\s*', '', line)
            line = line.strip()

            if line.startswith('http'):
                urls.append(line)

    return urls


def process_url(
    url: str,
    vault_client: vault_utils.VaultClient,
    bucket_name: str,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None,
    aws_region: str = 'eu-central-1',
    dry_run: bool = False
) -> bool:
    """Process a single URL: download from Repox, sign, and upload to S3.

    Args:
        url: URL to the artifact on binaries.sonarsource.com
        vault_client: Initialized Vault client
        bucket_name: S3 bucket name
        aws_access_key_id: AWS access key ID (optional)
        aws_secret_access_key: AWS secret access key (optional)
        aws_session_token: AWS session token (optional)
        aws_region: AWS region
        dry_run: If True, only display URLs without downloading/uploading

    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse URL
        distribution, artifact_name, version, s3_key = parse_binaries_url(url)
        print(f"\nProcessing: {artifact_name} {version}")
        print(f"  Distribution: {distribution}")
        print(f"  S3 key: {s3_key}")

        # Search for artifact in Repox (sonarsource repository contains both private and public)
        artifact_path = search_artifact_in_repox(artifact_name, version, dry_run)
        artifact_dir_path = extract_directory_from_path(artifact_path)

        if dry_run:
            print(f"  [DRY RUN] Would download from: {artifact_dir_path}/{artifact_name}-{version}.*")
            print(f"  [DRY RUN] Would sign with Vault GPG key")
            print(f"  [DRY RUN] Would upload to: s3://{bucket_name}/{s3_key}")
            print(f"  [DRY RUN] Would upload to: s3://{bucket_name}/{s3_key}.asc")
            return True

        # Create temporary directory
        with tempfile.TemporaryDirectory(prefix=f'upload-{artifact_name}-') as temp_dir:
            # Download from Repox (excluding .asc files)
            downloaded_files = download_from_repox(
                artifact_dir_path=artifact_dir_path,
                artifact_name=artifact_name,
                version=version,
                temp_dir=temp_dir,
                dry_run=dry_run
            )

            if not downloaded_files:
                print(f"  ⚠️  Warning: No files downloaded from Repox")
                return False

            # Sign all downloaded files using Vault GPG key
            print(f"  Signing {len(downloaded_files)} file(s) with Vault GPG key...")
            pgp_manager = pgp_utils.PGPManager(vault_client, temp_dir)
            pgp_manager.import_gpg_key()
            pgp_manager.sign_artifacts()

            # Upload each file and its signature to S3
            for local_path in downloaded_files:
                # Extract filename
                filename = os.path.basename(local_path)

                # Construct S3 key
                file_s3_key = f"{distribution}/{artifact_name}/{filename}"

                # Upload artifact to S3
                upload_to_s3(
                    local_path=local_path,
                    s3_key=file_s3_key,
                    bucket_name=bucket_name,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    aws_session_token=aws_session_token,
                    region=aws_region,
                    dry_run=dry_run
                )

                # Upload signature to S3
                signature_path = f"{local_path}.asc"
                if os.path.exists(signature_path):
                    upload_to_s3(
                        local_path=signature_path,
                        s3_key=f"{file_s3_key}.asc",
                        bucket_name=bucket_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        aws_session_token=aws_session_token,
                        region=aws_region,
                        dry_run=dry_run
                    )
                else:
                    print(f"  ⚠️  Warning: Signature not found for {filename}")

            print(f"✅ Successfully processed {artifact_name} {version}")
            return True

    except Exception as e:
        print(f"\n❌ Error processing {url}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Upload missing artifacts from Repox to binaries.sonarsource.com (S3)',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--urls-file',
        required=True,
        help='Path to a text file containing URLs (one URL per line)'
    )
    parser.add_argument(
        '--bucket',
        default=None,
        help='AWS S3 bucket name (default: from BINARIES_AWS_DEPLOY env var or downloads-cdn-eu-central-1-prod)'
    )
    parser.add_argument(
        '--vault-url',
        default=None,
        help='Vault URL (default: from VAULT_ADDR env var or https://vault.sonar.build:8200)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode: display download URLs without actually downloading or uploading'
    )

    args = parser.parse_args()

    # Get Vault token from environment
    vault_token = os.environ.get('VAULT_TOKEN')
    if not vault_token:
        parser.error("VAULT_TOKEN environment variable is required")

    # Get Vault URL
    vault_url = args.vault_url or os.environ.get('VAULT_ADDR', 'https://vault.sonar.build:8200')

    # Initialize Vault client
    print(f"Initializing Vault client: {vault_url}")
    vault_client = vault_utils.VaultClient(vault_url, vault_token)

    # Get AWS credentials from environment
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('BINARIES_AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('BINARIES_AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.environ.get('AWS_SESSION_TOKEN') or os.environ.get('BINARIES_AWS_SESSION_TOKEN')
    aws_region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION') or os.environ.get('BINARIES_AWS_DEFAULT_REGION', 'eu-central-1')

    # Get bucket name
    bucket_name = args.bucket or binaries_bucket_name or os.environ.get('BINARIES_AWS_DEPLOY', 'downloads-cdn-eu-central-1-prod')

    print(f"S3 bucket: {bucket_name}")
    print(f"AWS region: {aws_region}")

    # Show dry-run mode banner
    if args.dry_run:
        print("\n" + "="*70)
        print("=== DRY RUN MODE ===")
        print("Will only display Repox download URLs")
        print("No files will be downloaded or uploaded")
        print("="*70)

    # Read URLs from file
    if not os.path.exists(args.urls_file):
        parser.error(f"File not found: {args.urls_file}")

    urls = read_urls_from_file(args.urls_file)
    if not urls:
        parser.error(f"No valid URLs found in file: {args.urls_file}")

    print(f"\nFound {len(urls)} URL(s) in {args.urls_file}")
    print(f"Processing {len(urls)} artifact(s)...\n")

    # Process each URL
    successful = 0
    failed = 0
    failed_urls = []

    for idx, url in enumerate(urls, 1):
        print(f"\n{'='*70}")
        print(f"Processing artifact {idx}/{len(urls)}")
        print(f"{'='*70}")

        if process_url(
            url=url,
            vault_client=vault_client,
            bucket_name=bucket_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            aws_region=aws_region,
            dry_run=args.dry_run
        ):
            successful += 1
        else:
            failed += 1
            failed_urls.append(url)

    # Summary
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Total processed: {len(urls)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if failed_urls:
        print(f"\nFailed URLs:")
        for url in failed_urls:
            print(f"  - {url}")

    print(f"{'='*70}")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()

