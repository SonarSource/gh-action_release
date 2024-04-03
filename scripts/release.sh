#!/bin/bash
# Release a new version of the action
# Usage: scripts/release.sh <branch> <version>
set -xeuo pipefail

type git gh >/dev/null
branch=$1
version=$2
working_branch="release/update-self-references-${version}"
git checkout "${branch}"
git pull origin "${branch}"
git checkout -b "$working_branch"
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${branch},\1${version},g"
git commit -m "chore: update self-references to ${version}" -a
next_ref=$(git show -s --pretty=format:'%H')
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${version},\1${next_ref},g"
git commit -m "chore: update self-references to $next_ref" -a
git tag "$version"
git checkout "${branch}" -- .
git commit -m "chore: update self-references to ${branch}" -a
git log --pretty="%H %s %d" "${branch}".. --reverse >> scripts/pull-request-body.txt
git push origin "$working_branch"
git push origin "$version"
gh pr create --base "${branch}" --title "Release $version" --body-file scripts/pull-request-body.txt -a @me --label auto-approve
echo "Wait for PR approval..."
while ! gh pr view --json reviewDecision --jq .reviewDecision | grep -q APPROVED; do
  sleep 5
done
git fetch
git checkout "${branch}"
git merge --ff-only "$working_branch"
git push origin "${branch}"
gh release create "$version" -t "$version" --target "$(git show -s --pretty=format:'%H' "$version")" --verify-tag --generate-notes
