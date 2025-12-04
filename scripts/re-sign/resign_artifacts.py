#!/usr/bin/env python3
"""
Script to re-sign artifacts from a build.

This script:
1. Downloads artifacts from a build given project name and build number
2. Deletes all .asc files
3. Re-signs artifacts using a GPG key from Vault
4. Updates version in POM files
5. Creates/updates buildinfo
6. Uploads to Artifactory
7. Uploads to binaries.sonarsource.com (if applicable)
8. Uploads to Maven Central (if group ID starts with org.sonarsource)

Usage:
    python3 scripts/re-sign/resign_artifacts.py \
        --project PROJECT_NAME \
        --build-number BUILD_NUMBER \
        --version NEW_VERSION \
        [--dry-run] \
        [--artifactory-token TOKEN] \
        [--local-repo-dir DIR] \
        [--vault-token TOKEN] \
        [--vault-url URL] \
        [--vault-repo-owner OWNER]
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

# Add parent directory to path to import release modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "main"))
# Add re-sign directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from release.utils.artifactory import Artifactory
from release.utils.binaries import Binaries
from release.utils.dryrun import DryRunHelper
from release.vars import binaries_bucket_name

import artifactory_utils
import checksum_utils
import file_utils
import maven_metadata_utils
import pgp_utils
import pom_utils
import sbom_utils
import vault_utils


class ResignArtifacts:
    def __init__(
        self,
        project: str,
        build_number: str,
        version: str,
        op_item: Optional[str] = None,
        artifactory_token: Optional[str] = None,
        local_repo_dir: Optional[str] = None,
        dry_run: bool = False,
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
        vault_repo_owner: str = 'gh-action_release',
        vault_role_suffix: str = 'qa-deployer'
    ):
        self.project = project
        self.build_number = build_number
        self.version = version
        self.op_item = op_item  # Kept for backward compatibility, but not used anymore
        self.local_repo_dir = local_repo_dir or tempfile.mkdtemp(prefix='resign-')
        self.dry_run = dry_run

        # Initialize Vault client if token provided
        self.vault_client = None
        if vault_token:
            vault_url = vault_url or os.environ.get('VAULT_ADDR', 'https://vault.sonar.build:8200')
            self.vault_client = vault_utils.VaultClient(vault_url, vault_token)
            print(f"Vault client initialized: {vault_url}")

        # Get Artifactory token from Vault or environment/parameter
        if not artifactory_token:
            if self.vault_client:
                # Try project-specific role first (for uploads), then fallback to default
                # Role format: SonarSource-{project}-{role_suffix}
                repo_owner = None
                role_to_try = vault_role_suffix

                # First, try with project name (most common case for uploads)
                if self.project and self.project != 'gh-action_release':
                    try:
                        # Try project-specific role (e.g., SonarSource-sonar-dummy-qa-deployer)
                        artifactory_token = self.vault_client.read_artifactory_token(self.project, vault_role_suffix)
                        print(f"Retrieved Artifactory token from Vault (using role: SonarSource-{self.project}-{vault_role_suffix})")
                    except Exception as e1:
                        print(f"Warning: Failed to get Artifactory token for project '{self.project}': {e1}")
                        # Fallback: try with 'promoter' role (default in workflows)
                        try:
                            artifactory_token = self.vault_client.read_artifactory_token(self.project, 'promoter')
                            print(f"Retrieved Artifactory token from Vault (using role: SonarSource-{self.project}-promoter)")
                        except Exception as e2:
                            print(f"Warning: Failed to get Artifactory token with 'promoter' role: {e2}")
                            artifactory_token = None

                # If project-specific didn't work, try default gh-action_release role
                if not artifactory_token:
                    if vault_repo_owner == 'gh-action_release':
                        repo_owner = None  # None triggers default in read_artifactory_token
                    elif vault_repo_owner and vault_repo_owner != 'gh-action_release':
                        repo_owner = vault_repo_owner
                    else:
                        repo_owner = None

                    try:
                        artifactory_token = self.vault_client.read_artifactory_token(repo_owner, vault_role_suffix)
                        role_used = repo_owner if repo_owner else 'SonarSource-gh-action_release'
                        print(f"Retrieved Artifactory token from Vault (using role: {role_used}-{vault_role_suffix})")
                    except Exception as e:
                        print(f"Warning: Failed to get Artifactory token from Vault: {e}")
                        # Last fallback: try 'promoter' role
                        try:
                            artifactory_token = self.vault_client.read_artifactory_token(repo_owner, 'promoter')
                            role_used = repo_owner if repo_owner else 'SonarSource-gh-action_release'
                            print(f"Retrieved Artifactory token from Vault (using role: {role_used}-promoter)")
                        except Exception as e2:
                            print(f"Warning: Failed to get Artifactory token with 'promoter' role: {e2}")
                            artifactory_token = os.environ.get('ARTIFACTORY_ACCESS_TOKEN')
                else:
                    # Already got token from project-specific role
                    pass
            else:
                artifactory_token = os.environ.get('ARTIFACTORY_ACCESS_TOKEN')

        if not artifactory_token:
            raise ValueError(
                "Artifactory access token is required. Provide via:\n"
                "  - Vault (--vault-token, defaults to SonarSource-gh-action_release-qa-deployer role)\n"
                "  - Environment variable ARTIFACTORY_ACCESS_TOKEN\n"
                "  - Command line --artifactory-token"
            )

        self.artifactory = Artifactory(artifactory_token)
        self.binaries = None
        # Try to initialize binaries from binaries_bucket_name or environment variable, with default
        bucket_name = binaries_bucket_name or os.environ.get('BINARIES_AWS_DEPLOY', 'downloads-cdn-eu-central-1-prod')
        if bucket_name:
            # AWS credentials should be provided via environment variables:
            # - BINARIES_AWS_ACCESS_KEY_ID
            # - BINARIES_AWS_SECRET_ACCESS_KEY
            # - BINARIES_AWS_SESSION_TOKEN (optional, for temporary credentials)
            # - BINARIES_AWS_DEFAULT_REGION (optional, defaults to eu-central-1)

            # Set default region if not already set
            if not os.environ.get('BINARIES_AWS_DEFAULT_REGION'):
                os.environ['BINARIES_AWS_DEFAULT_REGION'] = 'eu-central-1'

            # Reload release.vars module to pick up any environment variables
            # This is necessary because release.vars reads from os.environ at import time
            try:
                import importlib
                import release.vars as release_vars_module
                importlib.reload(release_vars_module)
            except Exception:
                pass

            self.binaries = Binaries(bucket_name)

        # Initialize PGP manager
        self.pgp_manager = pgp_utils.PGPManager(self.vault_client, self.local_repo_dir)

        if self.dry_run:
            DryRunHelper.init()
            print("=== DRY RUN MODE ===")
            print("Artifacts will be downloaded and signed, but NOT uploaded to:")
            print("  - Artifactory (repox)")
            print("  - binaries.sonarsource.com")
            print("  - Maven Central")
            print("=" * 50)

    def run(self):
        """Main execution flow."""
        try:
            print(f"Working directory: {self.local_repo_dir}")
            print(f"Project: {self.project}")
            print(f"Build number: {self.build_number}")
            print(f"New version: {self.version}")

            # Step 1: Get original buildinfo (needed to determine repository)
            print("\n[1/10] Fetching original buildinfo...")
            buildinfo = artifactory_utils.get_buildinfo(self.artifactory, self.project, self.build_number)

            # Step 2: Download artifacts
            print("\n[2/10] Downloading artifacts from build...")
            artifactory_utils.download_artifacts(self.local_repo_dir, self.project, self.build_number, buildinfo)

            # Step 3: Delete .asc files
            print("\n[3/10] Deleting existing .asc signature files...")
            artifactory_utils.delete_asc_files(self.local_repo_dir)

            # Step 4: Import and setup GPG key from Vault
            print("\n[4/13] Importing GPG key from Vault...")
            self.pgp_manager.import_gpg_key()

            # Step 5: Update version in POM files (before signing, so signatures match updated content)
            print("\n[5/13] Updating version in POM files...")
            old_version = buildinfo.get_version()
            pom_utils.update_pom_versions(self.local_repo_dir, old_version, self.version)

            # Extract new build number from new version (last part after separator)
            # Version format: Major.Minor.Patch.BuildNumber or Major.Minor.Patch-BuildNumber
            import re
            version_pattern = re.compile(
                r'^(?P<prefix>[a-zA-Z]+-)?'   # Optional ProjectName- prefix
                r'\d+\.\d+\.\d+'              # Major.Minor.Patch version
                r'(?:-M\d+)?'                 # Optional -Mx suffix
                r'[-.+]'                       # Separator
                r'(?P<build>\d+)$'            # Build number in a captured group
            )
            version_match = version_pattern.match(self.version)
            if version_match:
                new_build_number = version_match.group('build')
                print(f"Extracted build number from version '{self.version}': {new_build_number}")
            else:
                # Fallback: try to extract last numeric part
                parts = re.split(r'[-.+]', self.version)
                if parts and parts[-1].isdigit():
                    new_build_number = parts[-1]
                    print(f"Extracted build number from version '{self.version}' (fallback): {new_build_number}")
                else:
                    # If we can't extract, use the original build number
                    new_build_number = self.build_number
                    print(f"Warning: Could not extract build number from version '{self.version}', using original: {new_build_number}")

            # Step 6: Update version in maven-metadata.xml files
            print("\n[6/13] Updating version in maven-metadata.xml files...")
            maven_metadata_utils.update_maven_metadata_versions(self.local_repo_dir, old_version, self.version)

            # Step 7: Restructure directories to reflect new version (BEFORE renaming files)
            # This ensures files are in the correct directory structure before renaming
            print("\n[7/13] Restructuring directories to reflect new version...")
            file_utils.restructure_version_directories(self.local_repo_dir, old_version, self.version)

            # Step 8: Rename files with version in filename (after restructuring, so files are in new directories)
            print("\n[8/13] Renaming files with version in filename...")
            file_utils.rename_versioned_files(self.local_repo_dir, old_version, self.version)

            # Step 9: Update version in SBOM files (after restructuring and renaming, so we update files in new directory)
            print("\n[9/13] Updating version in SBOM files...")
            sbom_utils.update_sbom_versions(self.local_repo_dir, old_version, self.version)

            # Step 10: Sign artifacts (AFTER all updates and renaming, so signatures match final filenames and content)
            print("\n[10/13] Signing artifacts...")
            self.pgp_manager.sign_artifacts()

            # Step 11: Create and upload buildinfo
            # Note: We do NOT regenerate checksums locally - Artifactory will generate them automatically
            # during upload. This avoids conflicts with checksum files that might already exist.
            print("\n[11/13] Creating and uploading buildinfo...")
            print(f"Using new build number: {new_build_number} (extracted from version: {self.version})")
            new_buildinfo = artifactory_utils.create_and_upload_buildinfo(
                self.local_repo_dir,
                self.project,
                new_build_number,  # Use extracted build number from new version
                self.version,
                buildinfo,
                self.artifactory,  # Pass artifactory client for fetching buildinfo
                self.dry_run
            )

            # Step 12: Upload to binaries.sonarsource.com if applicable
            # Use new_buildinfo if available, otherwise fall back to original buildinfo
            buildinfo_for_check = new_buildinfo if new_buildinfo else buildinfo
            artifacts_to_publish = buildinfo_for_check.get_artifacts_to_publish()
            should_upload_binaries = self.binaries and artifacts_to_publish
            should_upload_central = artifactory_utils.should_upload_to_maven_central(buildinfo_for_check)

            # Debug output
            if not artifacts_to_publish:
                print("\n[INFO] No artifacts to publish found in buildinfo, skipping binaries upload")
            elif self.binaries:
                print(f"\n[INFO] Binaries client initialized (bucket: {self.binaries.binaries_bucket_name})")
                print(f"[INFO] Will upload to binaries: {artifacts_to_publish}")

            if should_upload_binaries:
                print("\n[12/13] Uploading to binaries.sonarsource.com...")
                artifactory_utils.upload_to_binaries(
                    self.artifactory,
                    self.binaries,
                    self.project,
                    new_build_number,  # Use extracted build number from new version
                    self.version,
                    new_buildinfo if new_buildinfo else buildinfo,  # Use new buildinfo if available
                    self.dry_run
                )

            # Step 13: Upload to Maven Central if group ID starts with org.sonarsource
            if should_upload_central:
                print("\n[13/13] Uploading to Maven Central...")
                artifactory_utils.upload_to_maven_central(
                    self.local_repo_dir,
                    self.vault_client,
                    self.dry_run
                )

            print("\n✅ Resigning complete!")

        except Exception as e:
            print(f"\n❌ Error: {e}", file=sys.stderr)
            raise
        finally:
            # Cleanup GPG key if imported
            if self.pgp_manager.gpg_key_imported:
                self.pgp_manager.cleanup_gpg_key(self.dry_run)


def main():
    parser = argparse.ArgumentParser(
        description='Re-sign artifacts from a build',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--project', required=True, help='Project name')
    parser.add_argument('--build-number', required=True, help='Build number')
    parser.add_argument('--version', required=True, help='New version to use')
    parser.add_argument('--1password-item', dest='op_item',
                       help='1Password item reference (deprecated: GPG key is now retrieved from Vault)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode - no actual changes')
    parser.add_argument('--artifactory-token',
                       help='Artifactory access token (or set ARTIFACTORY_ACCESS_TOKEN env var)')
    parser.add_argument('--local-repo-dir',
                       help='Local directory for artifacts (default: temp directory)')
    parser.add_argument('--vault-url',
                       help='Vault URL (default: https://vault.sonar.build:8200 or VAULT_ADDR env var)')
    parser.add_argument('--vault-token',
                       help='Vault token for retrieving secrets (or set VAULT_TOKEN env var)')
    parser.add_argument('--vault-repo-owner',
                       default='gh-action_release',
                       help='Repository owner name for Vault lookup (default: gh-action_release, falls back to --project if not set)')
    parser.add_argument('--vault-role-suffix',
                       default='qa-deployer',
                       help='Vault role suffix for Artifactory token (default: qa-deployer)')

    args = parser.parse_args()

    # Set dry run environment variable if needed
    if args.dry_run:
        os.environ['INPUT_DRY_RUN'] = 'true'

    # Get Vault token from argument or environment
    vault_token = args.vault_token or os.environ.get('VAULT_TOKEN')
    vault_url = args.vault_url or os.environ.get('VAULT_ADDR', 'https://vault.sonar.build:8200')

    # Vault token is required for GPG key retrieval
    if not vault_token:
        parser.error("--vault-token or VAULT_TOKEN environment variable is required to retrieve GPG key from Vault")

    resigner = ResignArtifacts(
        project=args.project,
        build_number=args.build_number,
        version=args.version,
        op_item=args.op_item,
        artifactory_token=args.artifactory_token,
        local_repo_dir=args.local_repo_dir,
        dry_run=args.dry_run,
        vault_url=vault_url,
        vault_token=vault_token,
        vault_repo_owner=args.vault_repo_owner,
        vault_role_suffix=args.vault_role_suffix
    )

    resigner.run()


if __name__ == '__main__':
    main()

