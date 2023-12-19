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
close="$MVN_NEXUS_STAGING_CMD:rc-close -X -DstagingProgressTimeoutMinutes=30 $DEFAULT_OPTS" # TODO Remove temporary -X debugging flag.
# Release the artifacts to the public repository
release="$MVN_NEXUS_STAGING_CMD:rc-release $DEFAULT_OPTS"

# R3P0 is a magic string to ensure that the correct line is grepped
STAGING_REPO=$($open -DopenedRepositoryMessageFormat="R3P0:%s" | grep "R3P0:" | cut -d: -f2)

echo "repo=${STAGING_REPO}" >> "${GITHUB_OUTPUT}"

echo "running deploy-staged-repository" >> "${GITHUB_OUTPUT}"
$deploy -DstagingRepositoryId="$STAGING_REPO" -DrepositoryDirectory="$LOCAL_REPO_DIR"

echo "running rc-close" >> "${GITHUB_OUTPUT}"
echo $close -DstagingRepositoryId="$STAGING_REPO" >> "${GITHUB_OUTPUT}" # DELME
$close -DstagingRepositoryId="$STAGING_REPO"

if [ "$DO_RELEASE" = true ]; then
    echo "running rc-release" >> "${GITHUB_OUTPUT}"
    $release -DstagingRepositoryId="$STAGING_REPO"
fi
