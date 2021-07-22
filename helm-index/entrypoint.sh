#!/bin/sh

set -euo pipefail

cr index \
    --charts-repo "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY" \
    --git-repo "$GITHUB_REPOSITORY" \
    --owner "SonarSource" \
    --package-path "$1" \
    --push \
    --token $CR_TOKEN