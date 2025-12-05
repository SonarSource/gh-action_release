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
# Verify AWS credentials are set (standard AWS env vars)
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY
echo $AWS_SESSION_TOKEN  # Required for temporary credentials

# Or verify backward-compatible BINARIES_AWS_* vars
echo $BINARIES_AWS_ACCESS_KEY_ID
echo $BINARIES_AWS_SECRET_ACCESS_KEY
echo $BINARIES_AWS_SESSION_TOKEN

# Verify bucket name is set (optional, defaults to downloads-cdn-eu-central-1-prod)
echo $BINARIES_AWS_DEPLOY

# Verify region is set (optional, defaults to eu-central-1)
echo $AWS_DEFAULT_REGION
echo $AWS_REGION
echo $BINARIES_AWS_DEFAULT_REGION
```

**Note:** AWS credentials can be provided via:
- Standard AWS environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.)
- Backward-compatible `BINARIES_AWS_*` environment variables
- Default boto3 credential chain (IAM role, `~/.aws/credentials`, etc.)

The script will use the first available credential source.

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

## Resign Binaries JAR Script

A separate script `resign_binaries_jar.py` is available for re-signing individual JAR files from binaries.sonarsource.com.

### Purpose

This script downloads a JAR file from binaries.sonarsource.com, re-signs it using a GPG key from Vault, and uploads only the `.asc` signature file to the S3 bucket, overwriting the existing signature. It also automatically processes corresponding SBOM files (`*-cyclonedx.json` and `*-cyclonedx.xml`) if they exist.

### Usage

**Single JAR URL:**

```bash
export VAULT_TOKEN="your-vault-token"
export AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
export AWS_SESSION_TOKEN="your-aws-session-token"  # Optional

python3 scripts/re-sign/resign_binaries_jar.py \
    --jar-url https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar
```

**Multiple JAR URLs from file:**

Create a text file (`jar-urls.txt`) with one URL per line:

```
https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar
https://binaries.sonarsource.com/Distribution/sonar-python-plugin/sonar-python-plugin-3.15.0.1234.jar
# Comments are ignored
https://binaries.sonarsource.com/Distribution/sonar-javascript-plugin/sonar-javascript-plugin-9.0.0.5678.jar
```

Then run:

```bash
export VAULT_TOKEN="your-vault-token"
export BINARIES_AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export BINARIES_AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"

python3 scripts/re-sign/resign_binaries_jar.py \
    --jar-urls-file jar-urls.txt
```

**Note:** Empty lines and lines starting with `#` are ignored in the URLs file.

### Arguments

- `--jar-url` (required if `--jar-urls-file` not used): Full URL to a single JAR file on binaries.sonarsource.com
- `--jar-urls-file` (required if `--jar-url` not used): Path to a text file containing JAR URLs (one URL per line)
- `--bucket` (optional): AWS S3 bucket name (default: from `BINARIES_AWS_DEPLOY` env var or `downloads-cdn-eu-central-1-prod`)
- `--vault-url` (optional): Vault URL (default: from `VAULT_ADDR` env var or `https://vault.sonar.build:8200`)
- `--dry-run` (optional): Dry run mode - sign artifacts and print upload destinations without actually uploading to S3

**Note:** `--jar-url` and `--jar-urls-file` are mutually exclusive. You must provide exactly one of them.

### Environment Variables

**Required:**
- `VAULT_TOKEN` - Vault authentication token

**AWS Credentials (standard AWS env vars preferred):**
- `AWS_ACCESS_KEY_ID` - AWS access key ID (or `BINARIES_AWS_ACCESS_KEY_ID` for backward compatibility)
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key (or `BINARIES_AWS_SECRET_ACCESS_KEY` for backward compatibility)
- `AWS_SESSION_TOKEN` - AWS session token (optional, for temporary credentials, or `BINARIES_AWS_SESSION_TOKEN`)
- `AWS_DEFAULT_REGION` or `AWS_REGION` - AWS region (or `BINARIES_AWS_DEFAULT_REGION`, default: `eu-central-1`)

**Optional:**
- `BINARIES_AWS_DEPLOY` - AWS S3 bucket name (default: `downloads-cdn-eu-central-1-prod`)
- `VAULT_ADDR` - Vault URL (default: `https://vault.sonar.build:8200`)

**Note:** If AWS credentials are not provided via environment variables, boto3 will use the default credential chain (IAM role, `~/.aws/credentials`, etc.)

### How It Works

1. **Parse URL(s)**: Extracts the S3 bucket key and filename from the binaries.sonarsource.com URL(s)
2. **Download JAR**: Downloads each JAR file to a temporary directory
3. **Download SBOM files**: Attempts to download corresponding SBOM files (`*-cyclonedx.json` and `*-cyclonedx.xml`) if they exist
4. **Sign files**: Imports GPG key from Vault (once, reused for all JARs) and signs each JAR file and any SBOM files found
5. **Upload Signatures**: Uploads only the `.asc` signature files to S3 for each JAR and SBOM, overwriting the existing signatures

**SBOM Handling:**
- The script automatically looks for SBOM files by replacing `.jar` with `-cyclonedx.json` and `-cyclonedx.xml` in the JAR URL
- If SBOM files exist, they are downloaded, signed, and their signatures are uploaded
- If SBOM files don't exist (404), the script prints a warning and continues with JAR processing only (no error)

**Dry Run Mode:**
- Use `--dry-run` to test signing and verify upload destinations without actually uploading to S3
- In dry-run mode, AWS credentials are optional (not required)
- All files are still downloaded and signed, but uploads are skipped
- Upload destinations are printed with `[DRY RUN]` prefix for verification

When processing multiple JARs from a file:
- The GPG key is imported once and reused for all JARs (more efficient)
- Each JAR (and its SBOMs) is processed sequentially
- A summary is displayed at the end showing successful and failed operations
- The script exits with a non-zero code if any JAR failed to process

### Examples

**Single JAR:**

```bash
# Set required environment variables
export VAULT_TOKEN="your-vault-token"
export BINARIES_AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export BINARIES_AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Re-sign a single JAR file
python3 scripts/re-sign/resign_binaries_jar.py \
    --jar-url https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar
```

**Multiple JARs from file:**

```bash
# Set required environment variables
export VAULT_TOKEN="your-vault-token"
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Create URLs file
cat > jar-urls.txt << EOF
https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar
https://binaries.sonarsource.com/Distribution/sonar-python-plugin/sonar-python-plugin-3.15.0.1234.jar
https://binaries.sonarsource.com/Distribution/sonar-javascript-plugin/sonar-javascript-plugin-9.0.0.5678.jar
EOF

# Re-sign all JARs
python3 scripts/re-sign/resign_binaries_jar.py --jar-urls-file jar-urls.txt
```

**Dry Run Mode:**

Test the script without uploading to S3:

```bash
export VAULT_TOKEN="your-vault-token"
# AWS credentials are optional in dry-run mode

# Test with a single JAR
python3 scripts/re-sign/resign_binaries_jar.py \
    --jar-url https://binaries.sonarsource.com/Distribution/sonar-java-plugin/sonar-java-plugin-8.21.1.41883.jar \
    --dry-run

# Test with multiple JARs
python3 scripts/re-sign/resign_binaries_jar.py \
    --jar-urls-file jar-urls.txt \
    --dry-run
```

In dry-run mode:
- ✅ Downloads JAR and SBOM files
- ✅ Signs all files
- ✅ Prints upload destinations
- ❌ Does NOT upload to S3

## Upload Missing Artifacts to Binaries Script

A separate script `upload_missing_to_binaries.py` is available for uploading artifacts from Repox (Artifactory) to binaries.sonarsource.com (S3).

### Purpose

This script reads a file containing URLs to artifacts on binaries.sonarsource.com, downloads each artifact from Repox using JFrog CLI, signs it with the GPG key from Vault, and uploads both the artifact and its new signature to the S3 bucket maintaining the same path structure.

### Usage

**Process URLs from file:**

```bash
export VAULT_TOKEN="your-vault-token"
export JFROG_CLI_URL="https://repox.jfrog.io"
export JFROG_CLI_ACCESS_TOKEN="your-jfrog-access-token"
export AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"

python3 scripts/re-sign/upload_missing_to_binaries.py \
    --urls-file missing-artifacts.txt
```

**URLs file format** (one URL per line, supports list markers):

```
https://binaries.sonarsource.com/CommercialDistribution/sonar-ruby-plugin/sonar-ruby-plugin-1.19.0.471.jar
  - https://binaries.sonarsource.com/Distribution/sonar-go-plugin/sonar-go-plugin-1.26.1.4982.jar
# Comments are ignored
  - https://binaries.sonarsource.com/CommercialDistribution/sonar-cayc-plugin/sonar-cayc-plugin-2.4.0.2018.jar
```

### Arguments

- `--urls-file` (required): Path to a text file containing URLs (one URL per line)
- `--bucket` (optional): AWS S3 bucket name (default: from `BINARIES_AWS_DEPLOY` env var or `downloads-cdn-eu-central-1-prod`)
- `--vault-url` (optional): Vault URL (default: from `VAULT_ADDR` env var or `https://vault.sonar.build:8200`)
- `--dry-run` (optional): Dry run mode - display Repox download URLs without actually downloading or uploading

### Required Environment Variables

**Vault Authentication:**
- `VAULT_TOKEN` - Vault authentication token (required)
- `VAULT_ADDR` - Vault URL (default: `https://vault.sonar.build:8200` or use `--vault-url` flag)

The script will automatically retrieve:
- GPG key from `development/kv/data/sign` (key: `key`)
- GPG passphrase from `development/kv/data/sign` (key: `passphrase`)

**JFrog CLI Authentication:**
- `JFROG_CLI_URL` - JFrog Artifactory URL (e.g., `https://repox.jfrog.io`)
- `JFROG_CLI_ACCESS_TOKEN` - JFrog access token
- Or use `jfrog config add` to configure JFrog CLI

**AWS Authentication (standard AWS env vars preferred):**
- `AWS_ACCESS_KEY_ID` - AWS access key ID (or `BINARIES_AWS_ACCESS_KEY_ID`)
- `AWS_SECRET_ACCESS_KEY` - AWS secret access key (or `BINARIES_AWS_SECRET_ACCESS_KEY`)
- `AWS_SESSION_TOKEN` - AWS session token (optional, or `BINARIES_AWS_SESSION_TOKEN`)
- `AWS_DEFAULT_REGION` - AWS region (or `AWS_REGION` or `BINARIES_AWS_DEFAULT_REGION`, default: `eu-central-1`)

**S3 Bucket:**
- `BINARIES_AWS_DEPLOY` - AWS S3 bucket name (default: `downloads-cdn-eu-central-1-prod`)

### Examples

**Upload artifacts from file:**

```bash
# Set required environment variables
export VAULT_TOKEN="your-vault-token"
export JFROG_CLI_URL="https://repox.jfrog.io"
export JFROG_CLI_ACCESS_TOKEN="your-jfrog-token"
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# Create URLs file
cat > missing.txt << EOF
https://binaries.sonarsource.com/CommercialDistribution/sonar-ruby-plugin/sonar-ruby-plugin-1.19.0.471.jar
https://binaries.sonarsource.com/Distribution/sonar-go-plugin/sonar-go-plugin-1.26.1.4982.jar
EOF

# Upload artifacts
python3 scripts/re-sign/upload_missing_to_binaries.py --urls-file missing.txt
```

**Dry Run Mode:**

Test the script without downloading or uploading:

```bash
export VAULT_TOKEN="your-vault-token"
export JFROG_CLI_URL="https://repox.jfrog.io"
export JFROG_CLI_ACCESS_TOKEN="your-jfrog-token"
# AWS credentials are optional in dry-run mode

python3 scripts/re-sign/upload_missing_to_binaries.py \
    --urls-file missing.txt \
    --dry-run
```

In dry-run mode:
- ✅ Parses URLs and determines Repox paths
- ✅ Prints Repox download URLs
- ✅ Prints S3 upload destinations
- ❌ Does NOT download from Repox
- ❌ Does NOT sign artifacts
- ❌ Does NOT upload to S3

### How It Works

1. **Parse URL**: Extracts distribution (CommercialDistribution or Distribution), artifact name, and version from the binaries.sonarsource.com URL
2. **Determine Repository**: Maps distribution to Repox repository (`sonarsource-private-releases` or `sonarsource-public-releases`)
3. **Construct Repox Path**: Builds the artifact path in Repox based on artifact name and version
4. **Download**: Uses `jfrog rt download` to fetch the artifact (excluding `.asc` files)
5. **Sign**: Uses the GPG key from Vault to sign the artifact, creating a new `.asc` signature
6. **Upload**: Uses boto3 to upload both the artifact and its new signature to S3, maintaining the original path structure

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run with `--dry-run` to test without making changes
3. Verify all prerequisites are installed and configured
4. Check environment variables are set correctly

