#!/bin/bash
# Update the v* branch to the tag version
# Usage: scripts/updatevbranch.sh <version>
set -xeuo pipefail

version=$1
branch="v${version%%.*}"
git fetch origin "$branch" "$version"
git update-ref -m "reset: update branch $branch to tag $version" "refs/heads/$branch" "$version"
git push origin "$branch:refs/heads/$branch" || (
  git push --dry-run origin "$branch:refs/heads/$branch"
  git show -s --pretty=format:'%h%d' "$branch" "origin/$branch" "$version"
  git log --graph --pretty=format:'%h -%d %s' --abbrev-commit "$branch...origin/${branch}~"
  echo "Push failed, please check the output above" >&2
)
