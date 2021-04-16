#!/bin/bash

set -euo pipefail

LOCAL_REPO_DIR=$1

MVN_NEXUS_STAGING_CMD="mvn org.sonatype.plugins:nexus-staging-maven-plugin:1.6.7:"
DEFAULT_OPTS="-DnexusUrl=https://s01.oss.sonatype.org/ -DserverId=ossrh"
PROFILE_OPT="-DstagingProfileId=13c1877339a4cf"

# Open a new staging repository
open="$MVN_NEXUS_STAGING_CMD:rc-open $DEFAULT_OPTS $PROFILE_OPT"
# Deploy to the staging repository
deploy="$MVN_NEXUS_STAGING_CMD:deploy-staged-repository $DEFAULT_OPTS $PROFILE_OPT"
# Close the staging repository after deployment and perform checks
close="$MVN_NEXUS_STAGING_CMD:rc-close $DEFAULT_OPTS"
# Release the artifacts to the public repository
release="$MVN_NEXUS_STAGING_CMD:rc-release $DEFAULT_OPTS"

# R3P0 is a magic string to ensure that the correct line is grepped
STAGING_REPO=$($open -DopenedRepositoryMessageFormat="R3P0:%s" | grep "R3P0:" | cut -d: -f2)

echo "::set-output name=repo=${STAGING_REPO}"

$deploy -DstagingRepositoryId="$STAGING_REPO" -DrepositoryDirectory="$LOCAL_REPO_DIR"

$close -DstagingRepositoryId="$STAGING_REPO"

$release -DstagingRepositoryId="$STAGING_REPO"