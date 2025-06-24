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

# Poll for deployment status until it's processed
echo "Polling deployment status..."
MAX_ATTEMPTS=720 # 2 hours (720 * 10s)
POLL_INTERVAL=10  # 10 seconds
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "Checking deployment status (attempt $ATTEMPT/$MAX_ATTEMPTS)..."

    STATUS_RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" \
        -X POST \
        -H "$AUTH_HEADER" \
        "$CENTRAL_URL/api/v1/publisher/status?id=$DEPLOYMENT_ID")

    HTTP_STATUS=$(echo "$STATUS_RESPONSE" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
    RESPONSE_BODY="${STATUS_RESPONSE%HTTPSTATUS:*}"

    echo "Status check HTTP: $HTTP_STATUS"

    if [ "$HTTP_STATUS" -ge 200 ] && [ "$HTTP_STATUS" -lt 300 ]; then
        # Extract deployment state from response
        DEPLOYMENT_STATE=$(echo "$RESPONSE_BODY" | grep -o '"deploymentState":"[^"]*"' | cut -d'"' -f4)
        echo "Current deployment state: $DEPLOYMENT_STATE"

        case "$DEPLOYMENT_STATE" in
            "VALIDATED"|"PUBLISHING"|"PUBLISHED")
                echo "✅ Deployment successful with state: $DEPLOYMENT_STATE"
                exit 0
                ;;
            "FAILED")
                echo "❌ Deployment failed validation"
                echo "Status response: $RESPONSE_BODY"
                exit 1
                ;;
            "PENDING"|"VALIDATING")
                echo "⏳ Deployment is still being processed (state: $DEPLOYMENT_STATE)..."
                ;;
            *)
                echo "Unknown deployment state: $DEPLOYMENT_STATE"
                echo "Full response: $RESPONSE_BODY"
                ;;
        esac
    else
        echo "Warning: Status check failed with HTTP $HTTP_STATUS"
        echo "Response: $RESPONSE_BODY"
    fi

    if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
        echo "Waiting $POLL_INTERVAL seconds before next check..."
        sleep $POLL_INTERVAL
    fi

    ATTEMPT=$((ATTEMPT + 1))
done

echo "❌ Timeout: Deployment did not reach a final state within $((MAX_ATTEMPTS * POLL_INTERVAL / 3600)) hours"
echo "Check deployment status manually using: $CENTRAL_URL/api/v1/publisher/status?id=$DEPLOYMENT_ID"
exit 1
