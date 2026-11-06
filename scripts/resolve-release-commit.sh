#!/bin/bash
# Resolve the commit a release tags and the branch releasability checks.
#
# An explicit COMMIT_SHA is used as-is (expanded to 40 hex when GH_TOKEN is set).
# Otherwise the commit is read from the Repox build info of VERSION: vcsRevision,
# then vcs[0].revision, then buildInfo.env.GITHUB_SHA, then the legacy
# buildInfo.env.TRAVIS_COMMIT. The build name is the repository name, plus the
# optional ProjectName- version prefix — the same name the promotion uses.
# There is no fallback to the dispatched branch head.
#
# Environment:
#   REPOSITORY                 owner/name (required)
#   FALLBACK_BRANCH            branch used when build info has none, or with COMMIT_SHA
#   VERSION                    full version including build number (required unless COMMIT_SHA is set)
#   COMMIT_SHA                 optional override
#   ARTIFACTORY_ACCESS_TOKEN   required for the Repox lookup
#   ARTIFACTORY_URL            default https://repox.jfrog.io/repox
#   GH_TOKEN                   optional; expands a short COMMIT_SHA
#   GITHUB_OUTPUT              commit_sha and branch are appended here
#   GITHUB_STEP_SUMMARY        optional human-readable note
set -euo pipefail

: "${REPOSITORY:?REPOSITORY is required}"
: "${FALLBACK_BRANCH:?FALLBACK_BRANCH is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"

artifactory_url=${ARTIFACTORY_URL:-https://repox.jfrog.io/repox}
artifactory_url=${artifactory_url%/}

branch_ok() {
  [[ "$1" =~ ^[a-zA-Z0-9][a-zA-Z0-9/_.+-]*$ ]]
}

expand_sha() {
  local sha=$1
  sha=$(printf '%s' "$sha" | tr '[:upper:]' '[:lower:]')
  if [[ "$sha" =~ ^[0-9a-f]{40}$ ]]; then
    printf '%s' "$sha"
    return
  fi
  if [[ ! "$sha" =~ ^[0-9a-f]{7,40}$ ]]; then
    echo "::error::Commit '$1' is not a git SHA (7-40 hexadecimal characters)" >&2
    exit 1
  fi
  if [[ -z "${GH_TOKEN:-}" ]]; then
    printf '%s' "$sha"
    return
  fi
  gh api "repos/${REPOSITORY}/commits/${sha}" --jq .sha | tr '[:upper:]' '[:lower:]'
}

choose_branch() {
  local candidate=$1
  if branch_ok "$candidate"; then
    printf '%s' "$candidate"
    return
  fi
  if [[ -n "$candidate" ]]; then
    echo "::warning::Build info branch '$candidate' is not a usable branch name; using ${FALLBACK_BRANCH}" >&2
  fi
  if ! branch_ok "$FALLBACK_BRANCH"; then
    echo "::error::Branch '${FALLBACK_BRANCH}' is not a usable releasability branch name" >&2
    exit 1
  fi
  printf '%s' "$FALLBACK_BRANCH"
}

write_outputs() {
  local commit_sha=$1
  local branch=$2
  {
    printf 'commit_sha=%s\n' "$commit_sha"
    printf 'branch=%s\n' "$branch"
  } >> "$GITHUB_OUTPUT"
  echo "Release commit ${commit_sha} on branch ${branch}"
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      echo "## Release commit"
      echo
      echo "Tagging \`${commit_sha}\` on branch \`${branch}\`."
    } >> "$GITHUB_STEP_SUMMARY"
  fi
}

if [[ -n "${COMMIT_SHA:-}" ]]; then
  commit_sha=$(expand_sha "$COMMIT_SHA")
  branch=$(choose_branch "")
  echo "Using commitSha input ${commit_sha}"
  write_outputs "$commit_sha" "$branch"
  exit 0
fi

: "${VERSION:?VERSION is required when COMMIT_SHA is empty}"
: "${ARTIFACTORY_ACCESS_TOKEN:?ARTIFACTORY_ACCESS_TOKEN is required to resolve the commit of ${VERSION}}"

if [[ ! "$VERSION" =~ ^([a-zA-Z]+-)?[0-9]+\.[0-9]+\.[0-9]+(-M[0-9]+)?[-.+]([0-9]+)$ ]]; then
  echo "::error::Version '$VERSION' must follow [ProjectName-]Major.Minor.Patch[-Mx][-.+]BuildNumber"
  exit 1
fi
prefix=${BASH_REMATCH[1]}
build=${BASH_REMATCH[3]}
project=${REPOSITORY#*/}
if [[ -n "$prefix" ]]; then
  project="${project}-${prefix%-}"
fi

build_url="${artifactory_url}/api/build/${project}/${build}"
echo "Looking up Repox build ${project}/${build}"
response=$(mktemp)
trap 'rm -f "$response"' EXIT
if ! http_code=$(curl -sS -o "$response" -w '%{http_code}' \
  -H "Authorization: Bearer ${ARTIFACTORY_ACCESS_TOKEN}" \
  -H "Accept: application/json" \
  --retry 3 --retry-delay 2 \
  "$build_url"); then
  echo "::error::Could not reach Repox to resolve the commit of ${project}/${build}"
  exit 1
fi
if [[ "$http_code" != "200" ]]; then
  echo "::error::Repox build ${project}/${build} returned HTTP ${http_code}. Pass commitSha if this version's build info is not published under that name."
  exit 1
fi

{
  IFS= read -r commit_sha || true
  IFS= read -r build_branch || true
} < <(jq -r '
  def nonempty:
    if . == null or . == "" then empty else . end;
  def prop($name):
    (.properties // null) as $p
    | if $p == null then empty
      elif ($p | type) == "object" then ($p[$name] | nonempty)
      elif ($p | type) == "array" then
        (first($p[] | select((.key // .name) == $name) | .value) | nonempty)
      else empty end;
  (.buildInfo // .) as $b
  | [
      (first(
        ($b.vcsRevision | nonempty),
        ($b.vcs[0].revision | nonempty),
        ($b | prop("buildInfo.env.GITHUB_SHA")),
        ($b | prop("buildInfo.env.TRAVIS_COMMIT"))
      ) // ""),
      (
        ($b | prop("buildInfo.env.GITHUB_REF_NAME"))
        // (
          ($b | prop("buildInfo.env.GITHUB_REF")) as $ref
          | if ($ref | type) == "string" and ($ref | startswith("refs/heads/")) then $ref[11:] else empty end
        )
        // ""
      )
    ]
  | .[0], .[1]
' "$response")

if [[ -z "${commit_sha:-}" ]]; then
  echo "::error::Repox build ${project}/${build} has no commit (checked vcsRevision, vcs revision, buildInfo.env.GITHUB_SHA, and buildInfo.env.TRAVIS_COMMIT). Pass commitSha to release this version."
  exit 1
fi
commit_sha=$(expand_sha "$commit_sha")
branch=$(choose_branch "${build_branch:-}")
write_outputs "$commit_sha" "$branch"
