#!/bin/bash
# Release a new version of the action
# Usage: scripts/release.sh <branch> <version>
set -xeuo pipefail

type git gh >/dev/null
branch=$1
version=$2
git fetch --tags --all
git checkout "${branch}"
git pull origin "${branch}"
original_sha=$(git rev-parse HEAD)

# Create a detached release commit with SHA-pinned self-references (branch untouched)
git checkout --detach HEAD
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | \
  xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${branch},\1${original_sha},g"
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | \
  xargs sed -i "s/ref: \${{ github.ref }}/ref: ${original_sha}/g"
git commit -m "chore: release ${version}" -a
git tag "$version"
git checkout "${branch}"

git push origin "$version"
gh release create "$version" \
  -t "$version" \
  --target "$(git show -s --pretty=format:'%H' "$version")" \
  --verify-tag \
  --generate-notes
