#!/bin/bash

set -euo pipefail

LOCAL_REPO_DIR="$1"
CENTRAL_URL="$2"
AUTO_PUBLISH="$3"

# Validate required environment variables
if [ -z "${CENTRAL_TOKEN:-}" ]; then
    echo "ERROR: CENTRAL_TOKEN environment variable is required"
    exit 1
fi

echo "Starting Central Portal publishing..."
echo "Repository: $LOCAL_REPO_DIR"
echo "Auto-publish: $AUTO_PUBLISH"

# Validate that we have artifacts in the repository directory
if [ ! -d "$LOCAL_REPO_DIR" ]; then
    echo "ERROR: Repository directory $LOCAL_REPO_DIR does not exist"
    exit 1
fi

# Check if we have any artifacts to publish
ARTIFACT_COUNT=$(find "$LOCAL_REPO_DIR" -name "*.jar" -o -name "*.war" -o -name "*.ear" -o -name "*.pom" | wc -l)
if [ "$ARTIFACT_COUNT" -eq 0 ]; then
    echo "ERROR: No artifacts found in $LOCAL_REPO_DIR"
    exit 1
fi

echo "Found $ARTIFACT_COUNT artifacts to publish"

AUTH_HEADER="Authorization: Bearer $CENTRAL_TOKEN"

BUNDLE_DIR=$(mktemp -d)
BUNDLE_FILE="$BUNDLE_DIR/central-bundle.zip"
trap 'rm -rf "$BUNDLE_DIR"' EXIT

echo "Creating deployment bundle..."
cd "$LOCAL_REPO_DIR"

# Create the bundle preserving the Maven repository structure
zip -r "$BUNDLE_FILE" . -x ".*" ".DS_Store" "Thumbs.db"

if [ ! -f "$BUNDLE_FILE" ]; then
    echo "ERROR: Failed to create bundle file"
    exit 1
fi

# Get bundle size using
BUNDLE_SIZE=$(stat -f%z "$BUNDLE_FILE" 2>/dev/null || stat -c%s "$BUNDLE_FILE" 2>/dev/null || echo "unknown")
echo "Bundle created: $BUNDLE_SIZE bytes"

# Determine publishing type
PUBLISHING_TYPE="USER_MANAGED"
if [ "$AUTO_PUBLISH" = "true" ]; then
    PUBLISHING_TYPE="AUTOMATIC"
fi

echo "Publishing type: $PUBLISHING_TYPE"

echo "Uploading to Central Portal..."

UPLOAD_RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" \
    -X POST \
    -H "$AUTH_HEADER" \
    -F "bundle=@$BUNDLE_FILE" \
    "$CENTRAL_URL/api/v1/publisher/upload?publishingType=$PUBLISHING_TYPE")

HTTP_STATUS=$(echo "$UPLOAD_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
RESPONSE_BODY="${UPLOAD_RESPONSE%HTTPSTATUS:*}"

echo "Upload status: $HTTP_STATUS"

if [ "$HTTP_STATUS" -ne 201 ]; then
    echo "ERROR: Upload failed with status $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi

DEPLOYMENT_ID=$(echo "$RESPONSE_BODY" | tr -d '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
echo "Deployment ID: $DEPLOYMENT_ID"

if [ -n "${GITHUB_OUTPUT:-}" ]; then
    echo "deployment-id=${DEPLOYMENT_ID}" >> "$GITHUB_OUTPUT"
fi

echo "If needed, check deployment status manually using /api/v1/publisher/status?id=$DEPLOYMENT_ID"
exit 1
