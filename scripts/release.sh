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
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s/ref: \${{ github.ref }}/ref: ${version}/g"
git commit -m "chore: update self-references to ${version}" -a
next_ref=$(git show -s --pretty=format:'%H')
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${version},\1${next_ref},g"
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s/ref: ${version}/ref: ${next_ref}/g"
git commit -m "chore: update self-references to $next_ref" -a
git tag "$version"
git checkout "${branch}" -- .
git commit -m "chore: update self-references to ${branch}" -a
git log --pretty="%H %s %d" "${branch}".. --reverse >>scripts/pull-request-body.txt
git push origin "$working_branch"
git push origin "$version"
gh pr create --base "${branch}" --title "Release $version" --body-file scripts/pull-request-body.txt -a sonartech --label auto-approve
pr_number=$(gh pr view --json number --jq .number)
gh pr view "$pr_number" --json state,mergeable,reviewDecision --jq ".state,.mergeable,.reviewDecision"
set +x
echo "Wait until the PR $pr_number is mergeable and approved... (timeout after $(( 300*2 ))s)"
counter=0
while gh pr view "$pr_number" --json state --jq .state | grep -q OPEN &&
  (! gh pr view "$pr_number" --json mergeable --jq .mergeable | grep -q MERGEABLE ||
    ! gh pr view "$pr_number" --json reviewDecision --jq .reviewDecision | grep -q APPROVED); do
  ((counter++)) && ((counter == 300)) && echo "Timed out waiting for PR approval!" >&2 && exit 1
  printf "."
  sleep 2
done
set -x
gh pr checks "$pr_number" --fail-fast --watch --interval 30
if gh pr view "$pr_number" --json state --jq .state | grep -q OPEN &&
  gh pr view "$pr_number" --json mergeable --jq .mergeable | grep -q MERGEABLE &&
  gh pr view "$pr_number" --json reviewDecision --jq .reviewDecision | grep -q APPROVED; then
  echo "Fast-forward merge approved PR..."
  git fetch
  git checkout "${branch}"
  git merge --ff-only "$working_branch"
  git push origin "${branch}"
fi
counter=0
# wait for merge status to be updated
while ! gh pr view "$pr_number" --json state --jq .state | grep -q MERGED; do
  ((counter++)) && ((counter == 5)) && break
  sleep 2
done
if ! gh pr view "$pr_number" --json state --jq .state | grep -q MERGED; then
  echo "PR is not merged, exit" >&2
  exit 1
fi
gh release create "$version" -t "$version" --target "$(git show -s --pretty=format:'%H' "$version")" --verify-tag --generate-notes
