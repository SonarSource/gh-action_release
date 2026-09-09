# Maven Central Sync

This action provides a **simplified approach** to release artifacts to Maven Central through the new **Central Portal** using pure curl API calls.

## Overview

This action takes artifacts that have already been downloaded by the `download-build` action and uploads them to Central Portal using the Publisher API.

**No Maven plugins, no Docker, no staging profiles - just simple API calls!**

## How it works

Two modes, selected via the `mode` input:

- **validate** (default): build a zip bundle, upload it as a `USER_MANAGED` deployment, and poll
  until `VALIDATED`. The deployment is left pending-publish; on `FAILED` it is dropped
  automatically.
- **finalize**: publish an already-validated `deployment-id` (no re-upload).

The bundle is uploaded once: `validate` → `finalize`.

## Inputs

- `local-repo-dir`: Directory containing artifacts in Maven repository structure. Required for
  `mode: validate`; ignored for `finalize`.
- `central-url` (optional): Central Portal URL (default: `https://central.sonatype.com`)
- `mode` (optional): `validate` (default) | `finalize`
- `deployment-id`: Deployment to publish. Required for `mode: finalize`.

## Outputs

- `deployment-id`: The deployment ID from Central Portal (for tracking/debugging; `validate` only)

## Environment Variables

- `CENTRAL_TOKEN` (required): Authentication token from vault

## Usage

```yaml
- name: Maven Central Sync
  uses: ./.github/workflows/maven-central-sync
  with:
    local-repo-dir: ${{ steps.local_repo.outputs.dir }}
    central-url: https://central.sonatype.com
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