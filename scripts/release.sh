#!/bin/bash
# Release a new version of the action
# Usage: scripts/release.sh <branch> <version> [true|false]
set -xeuo pipefail

: "${GITHUB_STEP_SUMMARY:?}"
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

draft=${3:-true}
if [[ "$draft" == "true" ]]; then
  draft_flag="--draft"
else
  draft_flag=""
fi

git push origin "$version"
# shellcheck disable=SC2086
gh release create "$version" \
  -t "$version" \
  --target "$(git show -s --pretty=format:'%H' "$version")" \
  --verify-tag \
  --generate-notes \
  ${draft_flag}

release_json=$(gh release view "$version" --json url,body)
release_url=$(jq -r '.url' <<< "$release_json")
release_notes=$(jq -r '.body' <<< "$release_json")

publish_step=""
if [[ "$draft" == "true" ]]; then
  publish_step="1. **Publish the draft release** once the notes are finalized"
fi

cat >> "$GITHUB_STEP_SUMMARY" <<EOF
## Release $version

URL: $release_url

<details><summary>Release Notes</summary>

${release_notes}

</details>

---

## Next Steps

1. **Review and complete the release notes** at $release_url
    - Replace \`## What's Changed\` line with the following:
    \`\`\`
    ## What's Changed

    ### New Features
    - _Curated highlights from release notes: new features, important new options_

    ### Improvements
    - _Curated highlights from release notes: improvement and upgrades_

    ### Bug Fixes
    - _Curated highlights from release notes_

    ### Documentation
    - _Curated highlights from release notes_
    \`\`\`
    - Fill in the sections: New Features, Improvements, Bug Fixes, Documentation
    - Add usage examples or references if applicable
    - Remove empty sections
${publish_step}
1. **Communicate the release** on [#ops-platform-releases](https://sonarsource.enterprise.slack.com/archives/C0A6RL3L9BP)
    using the \`/platform-comms\` skill from engxp-squad plugin:
    \`\`\`
    /engxp-squad:platform-comms https://github.com/SonarSource/gh-action_release/releases/tag/$version
    \`\`\`
EOF
