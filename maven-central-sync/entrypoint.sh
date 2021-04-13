#!/bin/bash

set -euo pipefail

LOCAL_REPO_DIR=$1

CMD="mvn org.sonatype.plugins:nexus-staging-maven-plugin:1.6.7:"
DEFAULT_OPTS="-DnexusUrl=https://s01.oss.sonatype.org/ -DserverId=ossrh"
PROFILE_OPT="-DstagingProfileId=13c1877339a4cf"

open="$CMD:rc-open $DEFAULT_OPTS $PROFILE_OPT"
deploy="$CMD:deploy-staged-repository $DEFAULT_OPTS $PROFILE_OPT"
close="$CMD:rc-close $DEFAULT_OPTS"
release="$CMD:rc-release $DEFAULT_OPTS"

STAGING_REPO=$($open -DopenedRepositoryMessageFormat="R3P0:%s" | grep "R3P0:" | cut -d: -f2)

echo "::set-output name=repo=${STAGING_REPO}"

$deploy -DstagingRepositoryId="$STAGING_REPO" -DrepositoryDirectory="$LOCAL_REPO_DIR"

$close -DstagingRepositoryId="$STAGING_REPO"

#$release -DstagingRepositoryId="$STAGING_REPO"