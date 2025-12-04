# Resign Artifacts Script

This script re-signs artifacts from a build in Artifactory with a new GPG key, updates versions, and optionally uploads to Maven Central and binaries.sonarsource.com.

## Overview

The `resign_artifacts.py` script performs the following operations:

1. **Downloads artifacts** from a build given project name and build number
2. **Deletes all `.asc` signature files** (old signatures)
3. **Re-signs artifacts** using a GPG key from Vault
4. **Updates version** in POM files to the provided version
5. **Regenerates checksums** (MD5, SHA1, SHA256) for all files
6. **Creates and uploads buildinfo** to Artifactory
7. **Uploads to binaries.sonarsource.com** (if applicable)
8. **Uploads to Maven Central** (if group ID starts with `org.sonarsource`)

## Project Structure

The script is organized into utility modules:

- **`resign_artifacts.py`** - Main script that orchestrates the re-signing process
- **`vault_utils.py`** - Vault client for retrieving secrets (GPG key, passphrase, tokens)
- **`pgp_utils.py`** - GPG key import, signing, and cleanup operations
- **`artifactory_utils.py`** - Artifactory operations (download, upload, buildinfo, Maven Central)
- **`pom_utils.py`** - POM file version updates
- **`checksum_utils.py`** - Checksum generation (MD5, SHA1, SHA256)

## Prerequisites

### Required Tools

- **Python 3.7+** with standard library modules
- **JFrog CLI** (`jfrog`) installed and configured with Artifactory access
- **GPG** installed and configured
- **curl** (for Maven Central upload)

### Required Credentials

You can provide credentials either via **Vault** (recommended) or **environment variables**:

#### Option 1: Using Vault (Recommended)

- `VAULT_TOKEN` - Vault authentication token (or use `--vault-token` flag)
- `VAULT_ADDR` - Vault URL (default: `https://vault.sonar.build:8200` or use `--vault-url` flag)
- `--vault-repo-owner` - Repository owner name for Vault lookup (default: `gh-action_release`)

The script will automatically retrieve:
- GPG key from `development/kv/data/sign` (key: `key`)
- GPG passphrase from `development/kv/data/sign` (key: `passphrase`)
- Artifactory token from `development/artifactory/token/{repo-owner}-{role-suffix}` (defaults to `SonarSource-gh-action_release-private-reader`)
- Maven Central token from `development/kv/data/ossrh` (key: `token`)

#### Option 2: Using Environment Variables

- `ARTIFACTORY_ACCESS_TOKEN` - Artifactory access token (or use `--artifactory-token` flag)
- `CENTRAL_TOKEN` - Maven Central OSSRH token (required if uploading to Maven Central)

**Mandatory AWS Environment Variables (for binaries.sonarsource.com upload):**

- `BINARIES_AWS_ACCESS_KEY_ID` - AWS access key ID (required for binaries upload)
- `BINARIES_AWS_SECRET_ACCESS_KEY` - AWS secret access key (required for binaries upload)
- `BINARIES_AWS_SESSION_TOKEN` - AWS session token (optional, required for temporary credentials)
- `BINARIES_AWS_DEPLOY` - AWS S3 bucket name (optional, defaults to `downloads-cdn-eu-central-1-prod`)
- `BINARIES_AWS_DEFAULT_REGION` - AWS region (optional, defaults to `eu-central-1`)

### Optional Environment Variables

- `CENTRAL_URL` - Maven Central Portal URL (default: `https://central.sonatype.com`)
- `CENTRAL_AUTO_PUBLISH` - Auto-publish to Maven Central (default: `true`)
- `BINARIES_AWS_DEPLOY` - AWS S3 bucket name (default: `downloads-cdn-eu-central-1-prod`)
- `BINARIES_AWS_DEFAULT_REGION` - AWS region (default: `eu-central-1`)

## Setup

### 1. Get Vault Token (if using Vault)

Obtain a Vault token with access to:
- `development/kv/data/sign` - For GPG key and passphrase
- `development/artifactory/token/{repo-owner}-{role-suffix}` - For Artifactory access token
- `development/kv/data/ossrh` - For Maven Central token

Set it as an environment variable:
```bash
export VAULT_TOKEN="your-vault-token"
```

Or provide it via command line:
```bash
--vault-token "your-vault-token"
```

### 2. Configure JFrog CLI

```bash
jfrog config add repox --artifactory-url=https://repox.jfrog.io/repox --user=your-username --apikey=your-api-key
jfrog config use repox
```

### 3. Install Python Dependencies

The script uses modules from the `main/release` directory. Ensure you're running from the repository root:

```bash
# Install dependencies using pipenv (if available)
cd main
pipenv install

# Or install dependencies manually
pip install -r requirements.txt
```

## Usage

### Basic Usage with Vault

```bash
export VAULT_TOKEN="your-vault-token"

python3 scripts/re-sign/resign_artifacts.py \
    --project PROJECT_NAME \
    --build-number BUILD_NUMBER \
    --version NEW_VERSION \
    --vault-token YOUR_VAULT_TOKEN
    # --vault-repo-owner defaults to 'gh-action_release'
```

### Basic Usage with Environment Variables

```bash
export ARTIFACTORY_ACCESS_TOKEN="your-artifactory-token"
export CENTRAL_TOKEN="your-central-token"

# AWS credentials (mandatory for binaries upload)
export BINARIES_AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export BINARIES_AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"

python3 scripts/re-sign/resign_artifacts.py \
    --project PROJECT_NAME \
    --build-number BUILD_NUMBER \
    --version NEW_VERSION
```

### With Custom Artifactory Token

```bash
python3 scripts/re-sign/resign_artifacts.py \
    --project PROJECT_NAME \
    --build-number BUILD_NUMBER \
    --version NEW_VERSION \
    --artifactory-token YOUR_TOKEN
```

### Dry Run Mode

Test the script without making actual changes:

```bash
python3 scripts/re-sign/resign_artifacts.py \
    --project PROJECT_NAME \
    --build-number BUILD_NUMBER \
    --version NEW_VERSION \
    --dry-run
```

**Note:** In dry-run mode, artifacts are still downloaded and signed, but NOT uploaded to:
- Artifactory (repox)
- binaries.sonarsource.com
- Maven Central

### With Custom Local Directory

```bash
python3 scripts/re-sign/resign_artifacts.py \
    --project PROJECT_NAME \
    --build-number BUILD_NUMBER \
    --version NEW_VERSION \
    --local-repo-dir /path/to/local/directory
```

### Complete Example with Vault

```bash
# Set Vault token
export VAULT_TOKEN="your-vault-token"

# Run the script (secrets retrieved from Vault automatically)
python3 scripts/re-sign/resign_artifacts.py \
    --project sonarqube \
    --build-number 1234 \
    --version 10.0.0.1234 \
    --vault-token your-vault-token \
    --dry-run
```

### Complete Example with Environment Variables

```bash
# Set environment variables
export ARTIFACTORY_ACCESS_TOKEN="your-artifactory-token"
export CENTRAL_TOKEN="your-maven-central-token"

# Set AWS credentials (mandatory for binaries upload)
export BINARIES_AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export BINARIES_AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
export BINARIES_AWS_SESSION_TOKEN="your-aws-session-token"  # Optional, for temporary credentials
export BINARIES_AWS_DEPLOY="downloads-cdn-eu-central-1-prod"  # Optional, defaults to prod bucket
export BINARIES_AWS_DEFAULT_REGION="eu-central-1"  # Optional, defaults to eu-central-1

# Run the script
python3 scripts/re-sign/resign_artifacts.py \
    --project sonarqube \
    --build-number 1234 \
    --version 10.0.0.1234 \
    --dry-run
```

## Command Line Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--project` | Yes | Project name (e.g., `sonarqube`) |
| `--build-number` | Yes | Build number to download artifacts from |
| `--version` | Yes | New version to use in POM files |
| `--dry-run` | No | Enable dry-run mode (no uploads, but downloads and signing still occur) |
| `--artifactory-token` | No | Artifactory access token (or use env var or Vault) |
| `--local-repo-dir` | No | Local directory for artifacts (default: temp directory) |
| `--vault-token` | Yes* | Vault token for retrieving secrets (or set VAULT_TOKEN env var) |
| `--vault-url` | No | Vault URL (default: https://vault.sonar.build:8200 or VAULT_ADDR env var) |
| `--vault-repo-owner` | No | Repository owner name for Vault lookup (default: gh-action_release) |
| `--vault-role-suffix` | No | Vault role suffix for Artifactory token (default: private-reader) |
| `--1password-item` | No | Deprecated: GPG key is now retrieved from Vault |

\* Required for GPG key retrieval from Vault

## How It Works

### Step-by-Step Process

1. **Fetch Buildinfo**: Retrieves the original buildinfo from Artifactory to determine the repository and artifacts.

2. **Download Artifacts**: Downloads all artifacts from the specified build using JFrog CLI, preserving the Maven repository structure.

3. **Delete Old Signatures**: Removes all existing `.asc` signature files.

4. **Import GPG Key**: Retrieves the GPG key and passphrase from Vault and imports the key into the local GPG keyring.

5. **Sign Artifacts**: Signs all `.jar`, `.pom`, `.war`, and `.ear` files with the imported GPG key.

6. **Update POM Versions**: Updates the version in all POM files from the original version to the new version.

7. **Regenerate Checksums**: Calculates and creates MD5, SHA1, and SHA256 checksum files for all artifacts.

8. **Upload to Artifactory**: Uploads all artifacts and creates/updates the buildinfo in Artifactory.

9. **Upload to Binaries**: If artifacts are configured for binaries publication, uploads them to binaries.sonarsource.com. **Requires AWS credentials** (`BINARIES_AWS_ACCESS_KEY_ID`, `BINARIES_AWS_SECRET_ACCESS_KEY`, and optionally `BINARIES_AWS_SESSION_TOKEN`).

10. **Upload to Maven Central**: If any artifact has a group ID starting with `org.sonarsource`, uploads the bundle to Maven Central Portal and polls for deployment status.

## Maven Central Upload

The script automatically detects if artifacts should be uploaded to Maven Central by checking if any artifact has a group ID starting with `org.sonarsource`.

### Requirements for Maven Central

- `CENTRAL_TOKEN` must be available (from Vault or environment variable)
- Artifacts must be signed (GPG signatures)
- All required metadata (POM files, checksums) must be present
- Namespace must be registered in Central Portal
- Token must have publishing rights for the namespace

### Maven Central Token Retrieval

If using Vault, the script automatically retrieves the Maven Central token from:
- Vault path: `development/kv/data/ossrh`
- Key: `token`

If not using Vault, set the `CENTRAL_TOKEN` environment variable.

### Maven Central Upload Process

1. Creates a zip bundle preserving the Maven repository structure
2. Uploads the bundle to Central Portal via API
3. Polls deployment status until completion (up to 2 hours)
4. Reports final deployment state

## Dry Run Mode

Dry run mode allows you to test the script without making actual uploads:

- **Downloads artifacts** - Yes, artifacts are downloaded for testing
- **Signs artifacts** - Yes, artifacts are signed for testing
- **Updates POMs** - Yes, POM versions are updated for testing
- **Regenerates checksums** - Yes, checksums are regenerated for testing
- **Uploads to Artifactory** - No, skipped in dry-run mode
- **Uploads to binaries.sonarsource.com** - No, skipped in dry-run mode
- **Uploads to Maven Central** - No, skipped in dry-run mode

Use `--dry-run` to:
- Test signing and buildinfo creation logic
- Verify the script can access Vault
- Check that all required environment variables are set
- Validate command-line arguments

## Troubleshooting

### Vault Access Issues

```bash
# Verify Vault token is set
echo $VAULT_TOKEN

# Test Vault access (if vault CLI is installed)
vault auth $VAULT_TOKEN
vault read development/kv/data/sign

# Or test with curl
curl -H "X-Vault-Token: $VAULT_TOKEN" \
  https://vault.sonar.build:8200/v1/development/kv/data/sign
```

### JFrog CLI Issues

```bash
# Verify JFrog CLI is configured
jfrog config show

# Test Artifactory access
jfrog rt ping
```

### GPG Key Issues

```bash
# List imported keys
gpg --list-secret-keys

# Test signing
echo "test" > test.txt
gpg --armor --detach-sign test.txt
```

### AWS Credentials Issues (Binaries Upload)

If you encounter `InvalidAccessKeyId` or other AWS-related errors:

```bash
# Verify AWS credentials are set
echo $BINARIES_AWS_ACCESS_KEY_ID
echo $BINARIES_AWS_SECRET_ACCESS_KEY
echo $BINARIES_AWS_SESSION_TOKEN  # Required for temporary credentials

# Verify bucket name is set (optional, defaults to downloads-cdn-eu-central-1-prod)
echo $BINARIES_AWS_DEPLOY

# Verify region is set (optional, defaults to eu-central-1)
echo $BINARIES_AWS_DEFAULT_REGION
```

**Note:** AWS credentials are mandatory when uploading to binaries.sonarsource.com. The script will fail with an `InvalidAccessKeyId` error if credentials are not provided.

### Maven Central Upload Issues

- Ensure `CENTRAL_TOKEN` is available (from Vault or environment variable)
- Verify the token has publishing rights for the namespace
- Check that all artifacts are properly signed
- Ensure POM files have correct metadata

### Import Errors

If you see import errors like `ModuleNotFoundError: No module named 'release'`:

```bash
# Make sure you're running from the repository root
cd /path/to/gh-action_release

# Ensure the main directory is accessible
ls main/release/utils/
```

## Examples

### Example 1: Resign SonarQube Artifacts with Vault

```bash
export VAULT_TOKEN="your-vault-token"

python3 scripts/re-sign/resign_artifacts.py \
    --project sonarqube \
    --build-number 1234 \
    --version 10.0.0.1234 \
    --vault-token your-vault-token
```

### Example 2: Dry Run Test

```bash
python3 scripts/re-sign/resign_artifacts.py \
    --project sonarqube \
    --build-number 1234 \
    --version 10.0.0.1234 \
    --dry-run
```

## Notes

- The script preserves the Maven repository structure when downloading and uploading
- GPG key remains imported after script execution (not cleaned up by default)
- The script uses temporary directories that are cleaned up automatically
- Maven Central upload can take up to 2 hours to complete (script polls automatically)
- All operations are logged with clear progress indicators
- The script is organized into utility modules for better maintainability

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run with `--dry-run` to test without making changes
3. Verify all prerequisites are installed and configured
4. Check environment variables are set correctly

