#!/bin/bash
# Update the v* branch to the tag version
# Usage: scripts/updatevbranch.sh <version>
set -euo pipefail

version=$1
branch="v${version%%.*}"
git fetch --tags
git update-ref -m "reset: update branch $branch to tag $version" "refs/heads/$branch" "$version"
git push origin HEAD:"refs/heads/$branch"