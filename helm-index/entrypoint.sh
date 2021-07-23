#!/bin/sh

set -euo pipefail

rm -rf .cr-index
mkdir -p .cr-index

cr index \
    --charts-repo "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY" \
    --git-repo "$GITHUB_REPOSITORY" \
    --owner "SonarSource" \
    --package-path "$1" \
    --release-name-template "$2" \
    --push \
    --token $CR_TOKEN