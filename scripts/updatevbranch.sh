#!/bin/bash
# Update the v* branch to the tag version
# Usage: scripts/updatevbranch.sh <branch> <version>
set -xeuo pipefail

branch=$1
version=$2
vbranch="v${version%%.*}"
git fetch --tags origin "$vbranch" "$branch"
git update-ref -m "reset: update branch $vbranch to tag $version" "refs/heads/$vbranch" "$version"
git push origin "$vbranch:refs/heads/$vbranch" || (
  git show -s --pretty=format:'%h%d' "$vbranch" "origin/$vbranch" "$version"
  git log --graph --pretty=format:'%h -%d %s' --abbrev-commit "$vbranch...origin/${vbranch}~"
  echo "Push failed, please check the output above" >&2
  exit 1
)
