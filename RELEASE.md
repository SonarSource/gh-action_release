# Releasing the Release Action 🤯 😵‍💫

## TLDR;
To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow will create the GitHub Release.

To update the v-branch run the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will update the v-branch to the specified tag.

## Explanation
Due to the issue with GitHub Reusable Workflows referencing files in the same repository, the release process needs to pin the self-references to a stable SHA before tagging. This is done in a detached commit so the branch is never modified.

#### Tag and Release

This is available on GitHub: https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml

```bash
scripts/release.sh <branch> <version>
```

This script will:

1. capture the branch tip SHA (`original_sha`)
2. in detached HEAD, replace all `@<branch>` and `ref: ${{ github.ref }}` self-references with `@<original_sha>`
3. commit and tag that detached commit as `<version>`
4. push only the tag (the branch is left untouched)
5. create a Release on GitHub

Example:

```
$ scripts/release.sh branch-2 2.0.0
$ git show -s --pretty="%H %s %D" 2.0.0
2082aca0c8aa7cb64320b3713391d3d1056aaec6 chore: release 2.0.0 (tag: 2.0.0)
```

#### Update the v* Branch

Available as a workflow at: https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml

```bash
scripts/updatevbranch.sh <version>
```

Example:

```
$ scripts/updatevbranch.sh 2.0.0
$ git show -s --pretty=format:'%H%d' 2.0.0
2082aca0c8aa7cb64320b3713391d3d1056aaec6 (tag: 2.0.0, origin/v2)
```
