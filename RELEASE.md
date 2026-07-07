# Releasing the Release Action 🤯 😵‍💫

## TLDR;
To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow will create the GitHub Release.

To update the v-branch run the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will update the v-branch to the specified tag.

## Explanation
Due to the issue with GitHub Reusable Workflows referencing files in the same repository, the release process needs to pin the self-references to a stable SHA before tagging. This is done in a detached commit so the branch is never modified.

#### Tag and Release

This is available on GitHub: https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml

```bash
scripts/release.sh <branch> <version> [true|false]
```

This script will:

1. capture the branch tip SHA (`original_sha`)
2. in detached HEAD, replace all `@<branch>` and `ref: ${{ github.ref }}` self-references with `@<original_sha>`
3. commit and tag that detached commit as `<version>`
4. push only the tag (the branch is left untouched)
5. create a **draft** Release on GitHub (default) with auto-generated notes
6. post a summary to the workflow run with the release URL, release notes, and next steps

After the workflow completes:

1. **Review and complete the release notes** — the summary includes a template with sections (New Features, Improvements, Bug Fixes, Documentation); fill in and remove empty sections
2. **Publish the draft release** once the notes are finalized
3. **Communicate the release** on [#ops-platform-releases](https://sonarsource.enterprise.slack.com/archives/C0A6RL3L9BP) using the `/platform-comms` skill

#### Update the v* Branch

Available as a workflow at: https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml

```bash
scripts/updatevbranch.sh <version>
```
