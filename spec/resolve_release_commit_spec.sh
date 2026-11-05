#!/usr/bin/env bash

Describe 'resolve-release-commit.sh'

  BeforeEach 'setup_test_dirs'
  AfterEach 'cleanup_test_dirs'

  setup_test_dirs() {
    original_dir=$(pwd)
    test_dir="$original_dir/$(mktemp -u resolve-release-commit.XXXXXXXX)"
    mock_bin="$test_dir/bin"
    mkdir -p "$mock_bin"
    export REPOSITORY="SonarSource/sonarcloud-webapp"
    export FALLBACK_BRANCH="master"
    export ARTIFACTORY_ACCESS_TOKEN="token"
    unset COMMIT_SHA VERSION CURL_FORBIDDEN MOCK_HTTP_CODE FIXTURE GH_TOKEN || true
    cat > "$mock_bin/curl" <<'EOF'
#!/usr/bin/env bash
if [[ "${CURL_FORBIDDEN:-}" == "1" ]]; then
  echo "curl should not have been called" >&2
  exit 1
fi
out=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o) out=$2; shift 2 ;;
    *) shift ;;
  esac
done
cp "${FIXTURE:?}" "$out"
printf '%s' "${MOCK_HTTP_CODE:-200}"
EOF
    chmod +x "$mock_bin/curl"
  }

  cleanup_test_dirs() {
    cd "$original_dir" || return
    rm -rf "$test_dir"
  }

  resolve() {
    export GITHUB_OUTPUT="$test_dir/github_output"
    export PATH="$mock_bin:$PATH"
    export ARTIFACTORY_URL="https://repox.example/repox"
    : > "$GITHUB_OUTPUT"
    "$original_dir/scripts/resolve-release-commit.sh"
  }

  It 'reads vcsRevision and the branch recorded on the build'
    cat > "$test_dir/build.json" <<'EOF'
{"buildInfo":{"vcsRevision":"0123456789abcdef0123456789abcdef01234567","properties":{"buildInfo.env.GITHUB_REF_NAME":"branch-2026.1"}}}
EOF
    export FIXTURE="$test_dir/build.json"
    export VERSION="10.8.0.12345"

    When call resolve

    The status should be success
    The stdout should include "Looking up Repox build sonarcloud-webapp/12345"
    The stdout should include "Release commit 0123456789abcdef0123456789abcdef01234567 on branch branch-2026.1"
    The contents of file "$GITHUB_OUTPUT" should include "commit_sha=0123456789abcdef0123456789abcdef01234567"
    The contents of file "$GITHUB_OUTPUT" should include "branch=branch-2026.1"
  End

  It 'appends the ProjectName prefix to the build name'
    cat > "$test_dir/build.json" <<'EOF'
{"buildInfo":{"vcsRevision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}
EOF
    export FIXTURE="$test_dir/build.json"
    export VERSION="scanner-1.2.3.456"
    export REPOSITORY="SonarSource/sonar-scanner-azdo"

    When call resolve

    The status should be success
    The stdout should include "Looking up Repox build sonar-scanner-azdo-scanner/456"
    The contents of file "$GITHUB_OUTPUT" should include "branch=master"
  End

  It 'falls back to buildInfo.env.GITHUB_SHA and refs/heads'
    cat > "$test_dir/build.json" <<'EOF'
{"buildInfo":{"properties":[
  {"key":"buildInfo.env.GITHUB_SHA","value":"BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"},
  {"key":"buildInfo.env.GITHUB_REF","value":"refs/heads/master"}
]}}
EOF
    export FIXTURE="$test_dir/build.json"
    export VERSION="1.2.3+456"

    When call resolve

    The status should be success
    The stdout should include "Release commit bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb on branch master"
    The contents of file "$GITHUB_OUTPUT" should include "commit_sha=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    The contents of file "$GITHUB_OUTPUT" should include "branch=master"
  End

  It 'uses an explicit commitSha and does not call Repox'
    export CURL_FORBIDDEN=1
    export COMMIT_SHA="abcdef1234567890abcdef1234567890abcdef12"
    unset VERSION || true

    When call resolve

    The status should be success
    The stdout should include "Using commitSha input abcdef1234567890abcdef1234567890abcdef12"
    The contents of file "$GITHUB_OUTPUT" should include "commit_sha=abcdef1234567890abcdef1234567890abcdef12"
    The contents of file "$GITHUB_OUTPUT" should include "branch=master"
  End

  It 'rejects an explicit commitSha that is not a git SHA'
    export CURL_FORBIDDEN=1
    export COMMIT_SHA="master"

    When call resolve

    The status should be failure
    The stderr should include "not a git SHA"
    The contents of file "$GITHUB_OUTPUT" should not include "commit_sha="
  End

  It 'falls back when the build info branch is not a usable name'
    cat > "$test_dir/build.json" <<'EOF'
{"buildInfo":{"vcsRevision":"0123456789abcdef0123456789abcdef01234567","properties":{"buildInfo.env.GITHUB_REF_NAME":"not a branch"}}}
EOF
    export FIXTURE="$test_dir/build.json"
    export VERSION="1.2.3.456"

    When call resolve

    The status should be success
    The stdout should include "Release commit 0123456789abcdef0123456789abcdef01234567 on branch master"
    The stderr should include "not a usable branch name"
    The contents of file "$GITHUB_OUTPUT" should include "commit_sha=0123456789abcdef0123456789abcdef01234567"
    The contents of file "$GITHUB_OUTPUT" should include "branch=master"
  End

  It 'fails when the build info has a branch but no commit'
    cat > "$test_dir/build.json" <<'EOF'
{"buildInfo":{"properties":{"buildInfo.env.GITHUB_REF_NAME":"master"}}}
EOF
    export FIXTURE="$test_dir/build.json"
    export VERSION="1.2.3.456"

    When call resolve

    The status should be failure
    The stdout should include "has no commit"
    The contents of file "$GITHUB_OUTPUT" should not include "commit_sha=master"
  End

  It 'fails when the build info has no commit'
    echo '{"buildInfo":{"properties":{}}}' > "$test_dir/build.json"
    export FIXTURE="$test_dir/build.json"
    export VERSION="1.2.3.456"

    When call resolve

    The status should be failure
    The stdout should include "has no commit"
  End

  It 'fails when Repox does not have the build'
    echo '{}' > "$test_dir/build.json"
    export FIXTURE="$test_dir/build.json"
    export MOCK_HTTP_CODE=404
    export VERSION="1.2.3.456"

    When call resolve

    The status should be failure
    The stdout should include "HTTP 404"
  End

  It 'rejects a version with no build number'
    export VERSION="1.2.3"
    export FIXTURE="$test_dir/build.json"
    echo '{}' > "$FIXTURE"

    When call resolve

    The status should be failure
    The stdout should include "must follow"
  End
End
