#!/bin/bash

set -euo pipefail

type git gh jq >/dev/null
branch=$1
version=$2
working_branch="release/update-self-references-${version}"
git checkout "${branch}"
git pull
git checkout -b "$working_branch"
git grep -Hl SonarSource/gh-action_release | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${branch},\1${version},g"
git commit -m "chore: update self-references to ${version}" -a
next_ref=$(git show -s --pretty=format:'%H')
git grep -Hl SonarSource/gh-action_release | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${version},\1${next_ref},g"
git commit -m "chore: update self-references to $next_ref" -a
git tag "$version"
git checkout "${branch}" -- .
git commit -m "chore: update self-references to ${branch}" -a
gh pr create -B "${branch}" # TO BE MERGED ON MASTER BEFORE ANY OTHER PR
# wait until the PR is approved
while ! gh pr view --json reviewDecision --jq .reviewDecision | grep -q APPROVED; do
  sleep 5
done

gh pr status | grep -q OPEN

gh pr view --json reviewDecision | jq -r ".reviewDecision" | grep -q APPROVED
git push origin "$version"
