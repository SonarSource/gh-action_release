#!/bin/bash

set -euo pipefail

LOCAL_REPO_DIR="$1"
NEXUS_URL="$2"
STAGING_PROFILE_ID="$3"
DO_RELEASE="$4"
: "${GITHUB_OUTPUT:=/dev/stdout}"

MVN_NEXUS_STAGING_CMD="mvn org.sonatype.plugins:nexus-staging-maven-plugin:1.6.13:"
DEFAULT_OPTS="-DnexusUrl=$NEXUS_URL -DserverId=ossrh"
PROFILE_OPT="-DstagingProfileId=$STAGING_PROFILE_ID"

# Open a new staging repository
open="$MVN_NEXUS_STAGING_CMD:rc-open $DEFAULT_OPTS $PROFILE_OPT"
# Deploy to the staging repository
deploy="$MVN_NEXUS_STAGING_CMD:deploy-staged-repository $DEFAULT_OPTS $PROFILE_OPT"
# Close the staging repository after deployment and perform checks
close="$MVN_NEXUS_STAGING_CMD:rc-close -DstagingProgressTimeoutMinutes=60 $DEFAULT_OPTS"
# Release the artifacts to the public repository
release="$MVN_NEXUS_STAGING_CMD:rc-release $DEFAULT_OPTS"

# R3P0 is a magic string to ensure that the correct line is grepped
echo "Opening staging repository..."
STAGING_REPO=$($open -DopenedRepositoryMessageFormat="R3P0:%s" 2>&1 | grep "R3P0:" | cut -d: -f2 | tee /dev/stdout)
if [ -z "$STAGING_REPO" ]; then
  echo "Failed to open staging repository."
  exit 1
fi

echo "Opened staging repository: $STAGING_REPO"
echo "repo=${STAGING_REPO}" >> "$GITHUB_OUTPUT"

echo "Deploying to staging repository..."
$deploy -DstagingRepositoryId="$STAGING_REPO" -DrepositoryDirectory="$LOCAL_REPO_DIR" 2>&1 | tee /dev/stdout

echo "Closing staging repository..."
$close -DstagingRepositoryId="$STAGING_REPO" 2>&1 | tee /dev/stdout

if [ "$DO_RELEASE" = true ]; then
  echo "Releasing the artifacts..."
  $release -DstagingRepositoryId="$STAGING_REPO" 2>&1 | tee /dev/stdout
fi

echo "Action completed successfully."
