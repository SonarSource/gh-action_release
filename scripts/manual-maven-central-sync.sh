#!/usr/bin/env bash
#
# Manual re-sync of a SonarSource build to Maven Central via the Central Portal.
#
# Use this when the `mavenCentral` job in `gh-action_release/.github/workflows/main.yaml` was skipped at release time and you need to push
# the already-built artifacts to Maven Central after the fact
#
# This script mirrors what `.github/workflows/maven-central.yaml` does in CI:
#   1. Download the build's artifacts + checksums from JFrog (sonarsource-public-releases) into a temp dir.
#   2. Bundle and upload them to the Central Portal via the existing `maven-central-sync/maven-central-publish.sh` script, then poll for
#      validation/publication.
#
# Prerequisites:
#   - `jfrog` (v1) or `jf` (v2) CLI configured against repox.jfrog.io with read access to the build's `sonarsource-public-releases` repo
#   and build-info.
#   - `vault` CLI logged in to https://vault.sonar.build:8200
#   - `zip`, `curl`, `find`, `jq`.
#
# Usage:
#   scripts/manual-maven-central-sync.sh <build-name> <build-number> [project-name]
#
# Arguments:
#   <build-name>     Repository / build name as registered in Artifactory build-info (e.g. `sonar-dotnet-enterprise`).
#                    Used both for the JFrog build lookup and as the default project name.
#   <build-number>   Build number = 4th dot-segment of the version. For `10.26.0.140279` the build number is `140279`.
#   [project-name]   Optional override of the JFrog project name when it differs from the build name.
#                    Required for sonar-enterprise (use `sonar-enterprise-sqcb`).
#
# Environment overrides (rarely needed):
#   REMOTE_REPO      JFrog repo to download from (default: sonarsource-public-releases)
#   FILTER           Path prefix under REMOTE_REPO to constrain the download (default: `org/sonarsource`).
#                    Restricts the download to SonarSource Maven artifacts and drops non-Maven payloads (e.g. `.nupkg`) that Central
#                    Portal rejects when they end up at the zip root. Set to empty (FILTER=) to download every file in the build.
#   EXCLUSIONS       Passed verbatim to `jfrog rt download --exclusions` (default: `-`, i.e. no exclusions). Use to filter out a
#                    specific path pattern, e.g. EXCLUSIONS='*.nupkg;*.snupkg'.
#   CENTRAL_URL      Central Portal URL (default: https://central.sonatype.com)
#   AUTO_PUBLISH     "true" to auto-publish, "false" to stop at VALIDATED (default: true)
#   DEPLOYMENT_NAME  Name shown for the deployment on Central Portal (default: `<project-name>-<build-number>`).
#   KEEP_WORK_DIR    Force-keep the temp work directory after the script exits (default: `true` on failure, `false` on success).
#   JFROG_CLI        Force `jfrog` or `jf` CLI binary; auto-detected otherwise.
#
# Examples:
#   # PREQ-6069 — sync 10.26.0.140279 then 10.27.0.140913 for sonar-dotnet-enterprise:
#   scripts/manual-maven-central-sync.sh sonar-dotnet-enterprise 140279
#   scripts/manual-maven-central-sync.sh sonar-dotnet-enterprise 140913
#
#   # sonar-enterprise (build name differs from project name):
#   scripts/manual-maven-central-sync.sh sonar-enterprise 12345 sonar-enterprise-sqcb

set -euo pipefail

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
    sed -n '2,/^set -euo/p' "$0" | sed -e 's/^# \{0,1\}//' -e '$d'
    exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "Usage: $0 <build-name> <build-number> [project-name]" >&2
    echo "Run '$0 --help' for details." >&2
    exit 2
fi

BUILD_NAME="$1"
BUILD_NUMBER="$2"
PROJECT_NAME="${3:-$BUILD_NAME}"

REMOTE_REPO="${REMOTE_REPO:-sonarsource-public-releases}"
FILTER="${FILTER-org/sonarsource}"
EXCLUSIONS="${EXCLUSIONS:--}"
CENTRAL_URL="${CENTRAL_URL:-https://central.sonatype.com}"
AUTO_PUBLISH="${AUTO_PUBLISH:-true}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-${PROJECT_NAME}-${BUILD_NUMBER}}"
export DEPLOYMENT_NAME

DOWNLOAD_TARGET="$REMOTE_REPO"
if [[ -n "$FILTER" ]]; then
    DOWNLOAD_TARGET="${REMOTE_REPO}/${FILTER}/"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PUBLISH_SCRIPT="$REPO_ROOT/maven-central-sync/maven-central-publish.sh"

# Detect JFrog CLI (v2 `jf` or legacy `jfrog`).
if [[ -z "${JFROG_CLI:-}" ]]; then
    if command -v jfrog >/dev/null 2>&1; then
        JFROG_CLI=jfrog
    elif command -v jf >/dev/null 2>&1; then
        JFROG_CLI=jf
    else
        echo "ERROR: neither 'jfrog' nor 'jf' CLI is on PATH" >&2
        exit 1
    fi
fi

# Resolve Central Portal token from Vault.
CENTRAL_TOKEN="$(vault kv get -field=token development/kv/ossrh)"
if [[ -z "$CENTRAL_TOKEN" ]]; then
    echo "ERROR: empty CENTRAL_TOKEN — check 'vault login' and the secret path" >&2
    exit 1
fi
export CENTRAL_TOKEN

WORK_DIR="$(mktemp -d -t manual-mc-sync-XXXXXX)"
LOCAL_REPO_DIR="$WORK_DIR/repo"
mkdir -p "$LOCAL_REPO_DIR"

cleanup() {
    local rc=$?
    if [[ $rc -ne 0 || "${KEEP_WORK_DIR:-false}" == "true" ]]; then
        echo "Leaving $WORK_DIR for inspection (exit=$rc, KEEP_WORK_DIR=${KEEP_WORK_DIR:-false})"
    else
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

echo "=================================================================="
echo "  Build name      : $BUILD_NAME"
echo "  Build number    : $BUILD_NUMBER"
echo "  Project name    : $PROJECT_NAME"
echo "  Remote repo     : $REMOTE_REPO"
echo "  Filter          : ${FILTER:-<none>}"
echo "  Exclusions      : $EXCLUSIONS"
echo "  Download target : $DOWNLOAD_TARGET"
echo "  Central URL     : $CENTRAL_URL"
echo "  Auto-publish    : $AUTO_PUBLISH"
echo "  Deployment name : $DEPLOYMENT_NAME"
echo "  Work dir        : $LOCAL_REPO_DIR"
echo "  JFrog CLI       : $JFROG_CLI"
echo "=================================================================="

echo "Downloading build artifacts from JFrog..."
(
    cd "$LOCAL_REPO_DIR"
    "$JFROG_CLI" rt download --fail-no-op --exclusions "${EXCLUSIONS}" \
        --build "${PROJECT_NAME}/${BUILD_NUMBER}" \
        "${DOWNLOAD_TARGET}"
)

echo "Downloading checksums (md5/sha1/sha256) for every artifact..."
# Note: `{{}}` is intentional — find substitutes the inner `{}` with the file
# path and leaves the outer braces in place, so `jfrog rt curl` sees two
# URL `{...}` expansions and the `#1.#2` output template resolves correctly
# (#1 = path, #2 = md5|sha1|sha256). With a single `{}` curl writes the
# literal string `#2` into the working directory.
(
    cd "$LOCAL_REPO_DIR"
    find . -type f \
        -not \( -name "*.asc" -or -name "*.md5" -or -name "*.sha1" -or -name "*.sha256" \) \
        -exec "$JFROG_CLI" rt curl "${REMOTE_REPO}/{{}}.{md5,sha1,sha256}" --output "#1.#2" \;
)

# Sanity check 1: there must be at least one Maven-shaped artifact.
if ! find "$LOCAL_REPO_DIR" -type f \( -name "*.jar" -o -name "*.war" -o -name "*.ear" -o -name "*.pom" \) | grep -q .; then
    echo "ERROR: no Maven artifacts (jar/war/ear/pom) found under $LOCAL_REPO_DIR" >&2
    echo "       Either the build has no Java payload (nothing to push to Maven Central)" >&2
    echo "       or the JFrog download did not return what was expected." >&2
    exit 1
fi

# Sanity check 2: nothing must be present directly at the bundle root.
# Central Portal rejects bundles containing files at "./" — every artifact
# must live under a groupId/artifactId/version/ path.
if find "$LOCAL_REPO_DIR" -mindepth 1 -maxdepth 1 -type f | grep -q .; then
    echo "ERROR: files found at the bundle root — Central Portal will reject this:" >&2
    find "$LOCAL_REPO_DIR" -mindepth 1 -maxdepth 1 -type f | while IFS= read -r f; do
        echo "       $f" >&2
    done
    echo "       Restrict the download to the Maven path prefix with FILTER, e.g." >&2
    echo "       FILTER=org/sonarsource $0 $*" >&2
    exit 1
fi

echo "Downloaded layout (top 3 levels):"
( cd "$LOCAL_REPO_DIR" && find . -mindepth 1 -maxdepth 3 -type d | sort )

echo "Publishing to Central Portal..."
"$PUBLISH_SCRIPT" "$LOCAL_REPO_DIR" "$CENTRAL_URL" "$AUTO_PUBLISH"

echo "Manual Maven Central sync completed for ${BUILD_NAME}/${BUILD_NUMBER}."
