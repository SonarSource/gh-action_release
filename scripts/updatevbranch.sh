#!/bin/bash
# Update the v* branch to the tag version
# Usage: scripts/updatevbranch.sh <version>
set -xeuo pipefail

version=$1
vbranch="v${version%%.*}"
git fetch --tags --all
git checkout "$vbranch"
git update-ref -m "reset: update branch $vbranch to tag $version" "refs/heads/$vbranch" "$version"
git push --force origin "$vbranch:refs/heads/$vbranch" || (
  git show -s --pretty=format:'%h%d' "$vbranch" "origin/$vbranch" "$version"
  git log --graph --pretty=format:'%h -%d %s' --abbrev-commit "$vbranch" "origin/${vbranch}" "$version" -20
  echo "Push failed, please check the output above" >&2
  exit 1
)
