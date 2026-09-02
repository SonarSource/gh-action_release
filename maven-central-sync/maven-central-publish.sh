#!/bin/bash

set -euo pipefail

LOCAL_REPO_DIR="$1"
CENTRAL_URL="$2"
MODE="${3:-validate}" # validate (default) | finalize
DEPLOYMENT_ID="${4:-}" # required for finalize
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-central-bundle}"

if [ -z "${CENTRAL_TOKEN:-}" ]; then
    echo "ERROR: CENTRAL_TOKEN environment variable is required"
    exit 1
fi

AUTH_HEADER="Authorization: Bearer $CENTRAL_TOKEN"

poll_status() {
    echo "Polling deployment status..."
    local max_attempts=60 # 10 minutes (60 * 10s)
    local poll_interval=10
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        echo "Checking deployment status (attempt $attempt/$max_attempts)..."

        local status_response http_status response_body deployment_state
        status_response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "$AUTH_HEADER" \
            "$CENTRAL_URL/api/v1/publisher/status?id=$DEPLOYMENT_ID")
        http_status=$(echo "$status_response" | tr -d '\n' | sed -e 's/.*HTTPSTATUS://')
        response_body="${status_response%HTTPSTATUS:*}"

        if [ "$http_status" -ge 200 ] && [ "$http_status" -lt 300 ]; then
            deployment_state=$(echo "$response_body" | grep -o '"deploymentState":"[^"]*"' | cut -d'"' -f4)
            echo "Current deployment state: $deployment_state"

            case "$deployment_state" in
                "VALIDATED")
                    if [ "$MODE" = "validate" ]; then
                        echo "Validated, leaving deployment $DEPLOYMENT_ID pending-publish."
                        return 0
                    fi
                    ;;
                "PUBLISHING"|"PUBLISHED")
                    echo "Deployment successful with state: $deployment_state"
                    return 0
                    ;;
                "FAILED")
                    echo "Deployment failed validation"
                    echo "Status response: $response_body"
                    return 1
                    ;;
                "PENDING"|"VALIDATING")
                    echo "Deployment is still being processed (state: $deployment_state)..."
                    ;;
                *)
                    echo "Unknown deployment state: $deployment_state"
                    echo "Full response: $response_body"
                    ;;
            esac
        else
            echo "Warning: Status check failed with HTTP $http_status"
            echo "Response: $response_body"
        fi

        if [ "$attempt" -lt "$max_attempts" ]; then
            sleep "$poll_interval"
        fi
        attempt=$((attempt + 1))
    done

    echo "Timeout: deployment did not reach a final state within $((max_attempts * poll_interval / 60)) minutes"
    echo "Check deployment status manually using: $CENTRAL_URL/api/v1/publisher/status?id=$DEPLOYMENT_ID"
    return 1
}

if [ "$MODE" = "finalize" ]; then
    if [ -z "$DEPLOYMENT_ID" ]; then
        echo "ERROR: finalize mode requires a deployment id"
        exit 1
    fi
    echo "Publishing already-validated deployment $DEPLOYMENT_ID..."
    publish_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "$AUTH_HEADER" \
        "$CENTRAL_URL/api/v1/publisher/deployment/$DEPLOYMENT_ID")
    if [ "$publish_status" -lt 200 ] || [ "$publish_status" -ge 300 ]; then
        echo "ERROR: publish request failed with HTTP $publish_status"
        exit 1
    fi
    poll_status
    exit $?
fi

echo "Repository: $LOCAL_REPO_DIR"
echo "Deployment name: $DEPLOYMENT_NAME"

if [ ! -d "$LOCAL_REPO_DIR" ]; then
    echo "ERROR: Repository directory $LOCAL_REPO_DIR does not exist"
    exit 1
fi

ARTIFACT_COUNT=$(find "$LOCAL_REPO_DIR" -name "*.jar" -o -name "*.war" -o -name "*.ear" -o -name "*.pom" | wc -l)
if [ "$ARTIFACT_COUNT" -eq 0 ]; then
    echo "ERROR: No artifacts found in $LOCAL_REPO_DIR"
    exit 1
fi
echo "Found $ARTIFACT_COUNT artifacts to publish"

BUNDLE_DIR=$(mktemp -d)
BUNDLE_FILE="$BUNDLE_DIR/central-bundle.zip"
trap 'rm -rf "$BUNDLE_DIR"' EXIT

echo "Creating deployment bundle..."
cd "$LOCAL_REPO_DIR"
zip -r "$BUNDLE_FILE" . -x ".*" ".DS_Store" "Thumbs.db"

if [ ! -f "$BUNDLE_FILE" ]; then
    echo "ERROR: Failed to create bundle file"
    exit 1
fi

BUNDLE_SIZE=$(stat -f%z "$BUNDLE_FILE" 2>/dev/null || stat -c%s "$BUNDLE_FILE" 2>/dev/null || echo "unknown")
echo "Bundle created: $BUNDLE_SIZE bytes"

echo "Uploading to Central Portal..."
ENCODED_NAME=$(jq -rn --arg s "$DEPLOYMENT_NAME" '$s|@uri')
UPLOAD_URL="$CENTRAL_URL/api/v1/publisher/upload?publishingType=USER_MANAGED&name=$ENCODED_NAME"

UPLOAD_RESPONSE=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST -H "$AUTH_HEADER" -F "bundle=@$BUNDLE_FILE" "$UPLOAD_URL")
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

if poll_status; then
    exit 0
fi

echo "Dropping failed deployment $DEPLOYMENT_ID..."
drop_status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "$AUTH_HEADER" \
    "$CENTRAL_URL/api/v1/publisher/deployment/$DEPLOYMENT_ID")
if [ "$drop_status" -lt 200 ] || [ "$drop_status" -ge 300 ]; then
    echo "::warning::Could not drop failed deployment $DEPLOYMENT_ID (HTTP $drop_status) — drop it manually at $CENTRAL_URL"
fi
exit 1
