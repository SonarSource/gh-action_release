# Maven Central Sync

This action provides a **simplified approach** to release artifacts to Maven Central through the new **Central Portal** using pure curl API calls.

## Overview

This action takes artifacts that have already been downloaded by the `download-build` action and uploads them to Central Portal using the Publisher API.

**No Maven plugins, no Docker, no staging profiles - just simple API calls!**

## How it works

1. **Takes artifacts** from a local directory (provided by `download-build` action)
2. **Creates a zip bundle** preserving the Maven repository structure
3. **Uploads via curl** to Central Portal `/api/v1/publisher/upload` endpoint
4. **Monitors status** via polling until deployment is complete

## Inputs

- `local-repo-dir` (required): Directory containing artifacts in Maven repository structure
- `central-url` (optional): Central Portal URL (default: `https://central.sonatype.com`)
- `auto-publish` (optional): Whether to automatically publish after validation (default: `true`)

## Outputs

- `deployment-id`: The deployment ID from Central Portal (for tracking/debugging)

## Environment Variables

- `CENTRAL_TOKEN` (required): Authentication token from vault

## Usage

```yaml
- name: Maven Central Sync
  uses: ./.github/workflows/maven-central-sync
  with:
    local-repo-dir: ${{ steps.local_repo.outputs.dir }}
    central-url: https://central.sonatype.com
    auto-publish: "true"
  env:
    CENTRAL_TOKEN: ${{ secrets.CENTRAL_TOKEN }}
```

## Authentication

The action uses a token from vault that is already base64 encoded and ready to use directly as a Bearer token:

```bash
# Token from vault is already in correct format
curl -H "Authorization: Bearer $CENTRAL_TOKEN" ...
```

## Requirements

- Artifacts must be signed (GPG signatures)
- All required metadata (POM files, checksums) must be present
- Namespace must be registered in Central Portal
- Token must have publishing rights for the namespace

## Migration from Legacy OSSRH

This action replaces the old complex staging workflow with a simple API-based approach:

**Old approach**:
- Docker container with Maven runtime
- Complex staging profile management
- Multi-step workflow (open → deploy → close → release)

**New approach**:
- Simple shell script with curl calls
- Direct API upload
- One-step deployment with monitoring

## Works with any build system

Since this action operates on already-built artifacts in Maven repository structure, it works with:
- ✅ Maven projects
- ✅ Gradle projects
- ✅ Any build system that produces Maven-compatible artifacts