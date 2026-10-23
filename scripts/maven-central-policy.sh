#!/bin/bash
# Decide whether a repository may publish to Maven Central and write `allowed=true|false` to $GITHUB_OUTPUT.
# The policy is read from the default branch of the action repository so that a merged change applies immediately;
# the copy shipped with the running action ref is the fallback when it cannot be fetched or is invalid.
# Usage: scripts/maven-central-policy.sh <owner/name>
# Environment: GH_TOKEN (optional, for the fetch), POLICY_REPOSITORY (default SonarSource/gh-action_release),
#   POLICY_REF (default master)
set -euo pipefail

repository=$1
script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bundled="$script_dir/../maven-central-policy.yml"
checker="$script_dir/../main/release/utils/maven_central_policy.py"
policy_repository=${POLICY_REPOSITORY:-SonarSource/gh-action_release}
policy_ref=${POLICY_REF:-master}

fetched=$(mktemp)
trap 'rm -f "$fetched"' EXIT

result=
if gh api -H "Accept: application/vnd.github.raw" \
    "repos/$policy_repository/contents/maven-central-policy.yml?ref=$policy_ref" > "$fetched" 2> /dev/null; then
  result=$(python3 "$checker" "$fetched" "$repository") \
    || echo "::warning::The Maven Central policy of $policy_repository@$policy_ref is invalid, using the bundled copy"
else
  echo "::warning::Could not fetch the Maven Central policy of $policy_repository@$policy_ref, using the bundled copy"
fi
if [[ -z "$result" ]]; then
  result=$(python3 "$checker" "$bundled" "$repository")
fi

if [[ "$result" == "allowed" ]]; then
  echo "Maven Central sync is allowed for $repository"
  echo "allowed=true" >> "${GITHUB_OUTPUT:-/dev/null}"
else
  echo "::warning::Maven Central sync is disabled for $repository by maven-central-policy.yml of $policy_repository;" \
    "the release continues on Repox without calling Maven Central"
  echo "allowed=false" >> "${GITHUB_OUTPUT:-/dev/null}"
fi
