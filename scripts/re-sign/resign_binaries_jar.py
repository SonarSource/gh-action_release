#!/usr/bin/env python3
"""
Re-sign a JAR file from binaries.sonarsource.com and upload only the signature.

This script:
1. Downloads a JAR file from binaries.sonarsource.com given its URL
2. Attempts to download corresponding SBOM files (*-cyclonedx.json and *-cyclonedx.xml) if they exist
3. Re-signs the JAR and any SBOM files using a GPG key from Vault
4. Uploads only the .asc signature files to the S3 bucket, overwriting the existing signatures

Usage:
    # Single JAR URL
    python3 scripts/re-sign/resign_binaries_jar.py --jar-url <URL> [--bucket <BUCKET>] [--dry-run]

    # Multiple JAR URLs from file (one URL per line)
    python3 scripts/re-sign/resign_binaries_jar.py --jar-urls-file <FILE> [--bucket <BUCKET>] [--dry-run]

Environment Variables:
    VAULT_TOKEN - Vault authentication token (required)
    VAULT_ADDR - Vault URL (default: https://vault.sonar.build:8200)

    AWS credentials (standard AWS env vars preferred, BINARIES_AWS_* supported for backward compatibility):
    AWS_ACCESS_KEY_ID - AWS access key ID (or BINARIES_AWS_ACCESS_KEY_ID)
    AWS_SECRET_ACCESS_KEY - AWS secret access key (or BINARIES_AWS_SECRET_ACCESS_KEY)
    AWS_SESSION_TOKEN - AWS session token (optional, or BINARIES_AWS_SESSION_TOKEN)
    AWS_DEFAULT_REGION - AWS region (or AWS_REGION or BINARIES_AWS_DEFAULT_REGION, default: eu-central-1)

    BINARIES_AWS_DEPLOY - AWS S3 bucket name (default: downloads-cdn-eu-central-1-prod)

    Note: If AWS credentials are not provided via environment variables, boto3 will use
    the default credential chain (IAM role, ~/.aws/credentials, etc.)

Dry Run Mode:
    Use --dry-run to sign artifacts and print upload destinations without actually uploading to S3.
    AWS credentials are optional in dry-run mode.
"""

import argparse
import os
import sys
import tempfile
import urllib.parse
from pathlib import Path

import boto3
import requests

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


def parse_jar_url(url: str) -> tuple[str, str]:
    """Parse a binaries.sonarsource.com URL to extract bucket key and filename.

    Args:
        url: Full URL to the JAR file (e.g., https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar)

    Returns:
        Tuple of (bucket_key, filename)
        Example: ("Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar", "sonar-java-plugin-8.21.1.41883.jar")
    """
    parsed = urllib.parse.urlparse(url)

    # Extract path after domain (e.g., "/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar")
    path = parsed.path.lstrip('/')

    if not path:
        raise ValueError(f"Invalid URL: could not extract path from {url}")

    # Extract filename from path
    filename = os.path.basename(path)

    if not filename.endswith('.jar'):
        raise ValueError(f"URL does not point to a JAR file: {url}")

    return path, filename


def download_file(url: str, output_path: str, file_type: str = "file") -> bool:
    """Download a file from the given URL.

    Args:
        url: URL to download from
        output_path: Local path to save the file
        file_type: Type of file for logging (e.g., "JAR", "SBOM")

    Returns:
        True if file was downloaded successfully, False if file doesn't exist (404) or is forbidden (403)
    """
    try:
        print(f"Downloading {file_type} from {url}...")
        response = requests.get(url, stream=True, timeout=30)

        # Handle 404 (Not Found) and 403 (Forbidden) as non-fatal errors
        # 403 can occur when a file doesn't exist but the server returns Forbidden instead of Not Found
        if response.status_code == 404:
            print(f"  ⚠️  Warning: {file_type} not found (404), skipping...")
            return False
        elif response.status_code == 403:
            print(f"  ⚠️  Warning: {file_type} not accessible (403), skipping...")
            return False

        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"✓ Downloaded {file_type} to {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        # Handle 404 and 403 in exception handler as well
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 404:
                print(f"  ⚠️  Warning: {file_type} not found (404), skipping...")
                return False
            elif e.response.status_code == 403:
                print(f"  ⚠️  Warning: {file_type} not accessible (403), skipping...")
                return False
        raise


def get_sbom_urls(jar_url: str) -> tuple[str, str]:
    """Construct SBOM URLs from a JAR URL.

    Args:
        jar_url: URL to the JAR file

    Returns:
        Tuple of (sbom_json_url, sbom_xml_url)
    """
    # Replace .jar with -cyclonedx.json and -cyclonedx.xml
    sbom_json_url = jar_url.replace('.jar', '-cyclonedx.json')
    sbom_xml_url = jar_url.replace('.jar', '-cyclonedx.xml')

    return sbom_json_url, sbom_xml_url


def upload_signature_to_s3(
    signature_path: str,
    bucket_key: str,
    bucket_name: str,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None,
    region: str = 'eu-central-1',
    dry_run: bool = False
) -> None:
    """Upload a signature file to S3.

    Args:
        signature_path: Local path to the .asc signature file
        bucket_key: S3 bucket key (path) for the JAR file (without .asc extension)
        bucket_name: S3 bucket name
        aws_access_key_id: AWS access key ID (optional, uses boto3 default credential chain if not provided)
        aws_secret_access_key: AWS secret access key (optional, uses boto3 default credential chain if not provided)
        aws_session_token: AWS session token (optional)
        region: AWS region
        dry_run: If True, only print the destination without uploading
    """
    # Add .asc extension to bucket key
    signature_key = f"{bucket_key}.asc"
    destination = f"s3://{bucket_name}/{signature_key}"

    if dry_run:
        print(f"[DRY RUN] Would upload signature to {destination}")
        print(f"  Local file: {signature_path}")
        return

    print(f"Uploading signature to {destination}...")

    # Create S3 client using standard AWS credential chain
    # If credentials are provided, use them; otherwise boto3 will use default credential chain
    # (environment variables, IAM role, credentials file, etc.)
    session_kwargs = {'region_name': region}
    if aws_access_key_id and aws_secret_access_key:
        session_kwargs['aws_access_key_id'] = aws_access_key_id
        session_kwargs['aws_secret_access_key'] = aws_secret_access_key
        if aws_session_token:
            session_kwargs['aws_session_token'] = aws_session_token

    session = boto3.Session(**session_kwargs)
    s3_client = session.client('s3')

    # Upload the signature file
    s3_client.upload_file(signature_path, bucket_name, signature_key)

    print(f"✓ Uploaded signature to {destination}")


def read_urls_from_file(file_path: str) -> list[str]:
    """Read JAR URLs from a text file (one URL per line).

    Args:
        file_path: Path to the text file containing URLs

    Returns:
        List of URLs (stripped of whitespace, empty lines and comments skipped)
    """
    urls = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace
            line = line.strip()

            # Skip empty lines and comments (lines starting with #)
            if not line or line.startswith('#'):
                continue

            urls.append(line)

    return urls


def process_jar_url(
    jar_url: str,
    vault_client: vault_utils.VaultClient,
    bucket_name: str,
    aws_access_key_id: str = None,
    aws_secret_access_key: str = None,
    aws_session_token: str = None,
    aws_region: str = 'eu-central-1',
    dry_run: bool = False
) -> bool:
    """Process a single JAR URL: download, sign, and upload signature.
    Also processes SBOM files if they exist.

    Args:
        jar_url: URL to the JAR file
        vault_client: Initialized Vault client
        bucket_name: S3 bucket name
        aws_access_key_id: AWS access key ID (optional, uses boto3 default credential chain if not provided)
        aws_secret_access_key: AWS secret access key (optional, uses boto3 default credential chain if not provided)
        aws_session_token: AWS session token (optional)
        aws_region: AWS region
        dry_run: If True, only sign files and print upload destinations without uploading

    Returns:
        True if successful, False otherwise
    """
    try:
        # Parse URL to get bucket key
        bucket_key, filename = parse_jar_url(jar_url)
        print(f"\n{'='*70}")
        print(f"Processing: {filename}")
        print(f"URL: {jar_url}")
        print(f"Bucket key: {bucket_key}")

        # Create temporary directory for this JAR and SBOMs
        with tempfile.TemporaryDirectory(prefix=f'resign-{filename}-') as temp_dir:
            jar_path = os.path.join(temp_dir, filename)

            # Step 1: Download JAR
            print(f"\n[1/4] Downloading JAR...")
            if not download_file(jar_url, jar_path, "JAR"):
                return False

            # Step 2: Download SBOM files (if they exist)
            print(f"\n[2/4] Downloading SBOM files...")
            sbom_json_url, sbom_xml_url = get_sbom_urls(jar_url)

            # Extract base filename without .jar extension
            base_name = filename.replace('.jar', '')
            sbom_json_path = os.path.join(temp_dir, f"{base_name}-cyclonedx.json")
            sbom_xml_path = os.path.join(temp_dir, f"{base_name}-cyclonedx.xml")

            sbom_json_exists = download_file(sbom_json_url, sbom_json_path, "SBOM JSON")
            sbom_xml_exists = download_file(sbom_xml_url, sbom_xml_path, "SBOM XML")

            if not sbom_json_exists and not sbom_xml_exists:
                print("  ⚠️  Warning: No SBOM files found, continuing with JAR only...")

            # Step 3: Sign all files (JAR + SBOMs if they exist)
            print(f"\n[3/4] Signing files...")
            pgp_manager = pgp_utils.PGPManager(vault_client, temp_dir)
            # Import key (will reuse if already imported)
            pgp_manager.import_gpg_key()
            pgp_manager.sign_artifacts()

            # Verify signatures were created
            jar_signature_path = f"{jar_path}.asc"
            if not os.path.exists(jar_signature_path):
                print(f"❌ Error: JAR signature file not found at {jar_signature_path}")
                return False

            print(f"✓ Created JAR signature: {jar_signature_path}")

            # Step 4: Upload signatures to S3
            if dry_run:
                print(f"\n[4/4] [DRY RUN] Would upload signatures to S3...")
            else:
                print(f"\n[4/4] Uploading signatures to S3...")

            # Upload JAR signature
            upload_signature_to_s3(
                signature_path=jar_signature_path,
                bucket_key=bucket_key,
                bucket_name=bucket_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
                region=aws_region,
                dry_run=dry_run
            )

            # Upload SBOM signatures if they exist
            if sbom_json_exists:
                sbom_json_signature_path = f"{sbom_json_path}.asc"
                if os.path.exists(sbom_json_signature_path):
                    # Construct SBOM bucket key
                    sbom_json_bucket_key = bucket_key.replace('.jar', '-cyclonedx.json')
                    upload_signature_to_s3(
                        signature_path=sbom_json_signature_path,
                        bucket_key=sbom_json_bucket_key,
                        bucket_name=bucket_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        aws_session_token=aws_session_token,
                        region=aws_region,
                        dry_run=dry_run
                    )
                else:
                    print(f"⚠️  Warning: SBOM JSON signature not found at {sbom_json_signature_path}")

            if sbom_xml_exists:
                sbom_xml_signature_path = f"{sbom_xml_path}.asc"
                if os.path.exists(sbom_xml_signature_path):
                    # Construct SBOM bucket key
                    sbom_xml_bucket_key = bucket_key.replace('.jar', '-cyclonedx.xml')
                    upload_signature_to_s3(
                        signature_path=sbom_xml_signature_path,
                        bucket_key=sbom_xml_bucket_key,
                        bucket_name=bucket_name,
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key,
                        aws_session_token=aws_session_token,
                        region=aws_region,
                        dry_run=dry_run
                    )
                else:
                    print(f"⚠️  Warning: SBOM XML signature not found at {sbom_xml_signature_path}")

            if dry_run:
                print(f"\n✅ [DRY RUN] Successfully re-signed files for {filename} (no uploads performed)")
            else:
                print(f"\n✅ Successfully re-signed and uploaded signatures for {filename}")
            return True

    except Exception as e:
        print(f"\n❌ Error processing {jar_url}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Re-sign JAR file(s) from binaries.sonarsource.com and upload only the signature',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Mutually exclusive group for single URL vs file
    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument(
        '--jar-url',
        help='URL to a single JAR file on binaries.sonarsource.com'
    )
    url_group.add_argument(
        '--jar-urls-file',
        help='Path to a text file containing JAR URLs (one URL per line, empty lines and lines starting with # are ignored)'
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
        help='Dry run mode: sign artifacts and print upload destinations without actually uploading to S3'
    )

    args = parser.parse_args()

    # Get Vault token from environment
    vault_token = os.environ.get('VAULT_TOKEN')
    if not vault_token:
        parser.error("VAULT_TOKEN environment variable is required")

    # Get Vault URL
    vault_url = args.vault_url or os.environ.get('VAULT_ADDR', 'https://vault.sonar.build:8200')

    # Get AWS credentials from environment
    # Prefer standard AWS environment variables, fall back to BINARIES_AWS_* for backward compatibility
    aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('BINARIES_AWS_ACCESS_KEY_ID')
    aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('BINARIES_AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.environ.get('AWS_SESSION_TOKEN') or os.environ.get('BINARIES_AWS_SESSION_TOKEN')
    aws_region = os.environ.get('AWS_DEFAULT_REGION') or os.environ.get('AWS_REGION') or os.environ.get('BINARIES_AWS_DEFAULT_REGION', 'eu-central-1')

    # In dry-run mode, credentials are optional (boto3 will use default credential chain if not provided)
    # In normal mode, if no credentials are provided, boto3 will use default credential chain (IAM role, credentials file, etc.)
    # So we don't require explicit credentials unless they're needed for a specific reason

    # Get bucket name (same logic as resign_artifacts.py)
    bucket_name = args.bucket or binaries_bucket_name or os.environ.get('BINARIES_AWS_DEPLOY', 'downloads-cdn-eu-central-1-prod')

    # Initialize Vault client (shared for all JARs)
    print(f"Initializing Vault client: {vault_url}")
    vault_client = vault_utils.VaultClient(vault_url, vault_token)

    # Show dry-run mode banner
    if args.dry_run:
        print("\n" + "="*70)
        print("=== DRY RUN MODE ===")
        print("Artifacts will be downloaded and signed, but NOT uploaded to S3")
        print("Upload destinations will be printed for verification")
        print("="*70)

    # Determine URLs to process
    if args.jar_url:
        # Single URL mode
        urls = [args.jar_url]
        print("\nProcessing 1 JAR URL...")
    else:
        # File mode
        if not os.path.exists(args.jar_urls_file):
            parser.error(f"File not found: {args.jar_urls_file}")

        urls = read_urls_from_file(args.jar_urls_file)
        if not urls:
            parser.error(f"No valid URLs found in file: {args.jar_urls_file}")

        print(f"\nFound {len(urls)} JAR URL(s) in {args.jar_urls_file}")
        print(f"Processing {len(urls)} JAR(s)...")

    # Process each URL
    successful = 0
    failed = 0
    failed_urls = []

    for idx, jar_url in enumerate(urls, 1):
        print(f"\n{'='*70}")
        print(f"Processing JAR {idx}/{len(urls)}")
        print(f"{'='*70}")

        if process_jar_url(
            jar_url=jar_url,
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
            failed_urls.append(jar_url)

    # Summary
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Total processed: {len(urls)}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")

    if failed_urls:
        print(f"\nFailed JARs (could not be downloaded or processed):")
        for url in failed_urls:
            print(f"  - {url}")

    print(f"{'='*70}")

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()

