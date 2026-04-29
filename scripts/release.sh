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
original_ref=$(git rev-parse HEAD)
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${branch},\1${version},g"
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s/ref: \${{ github.ref }}/ref: ${version}/g"
git commit -m "chore: prepare ${version} for future reference" -a
next_ref=$(git show -s --pretty=format:'%H')
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${version},\1${next_ref},g"
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s/ref: ${version}/ref: ${next_ref}/g"
git commit -m "chore: release ${version} reference" -a
git tag "$version"
git checkout "${original_ref}" -- .
git commit -m "chore: revert release commits" -a
git push origin "$version"
git push origin "${branch}"
# Trigger the release workflow via workflow_dispatch.
# The reusable workflow owns draft creation, checks, promotion, and publication.
GITHUB_REPO="${GITHUB_REPO:-SonarSource/gh-action_release}"
gh workflow run release.yml \
  --repo "$GITHUB_REPO" \
  -f version="$version"
