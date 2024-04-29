# Releasing the Release Action 🤯 😵‍💫

## TLDR;
To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow will create the GitHub Release.

To update the v-branch run the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will update the v-branch to the specified tag.

## Explanation
Due to the issue with GitHub Reusable Workflows referencing files in the same repository, the release process needs to create 2 commits to be able to have a tag referencing all worflows with the same version.

#### Tag and Release

This is available on GitHub: https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml

```bash
scripts/release.sh <branch> <version>
```

This script will:

1. commit references the future tag
2. commit references the previous commit
3. tag this second commit
4. revert previous commits
5. create a Release on GitHub

Example:

```
$ scripts/release.sh branch-2 2.0.0
$ git log --graph --pretty="%H %s %d" branch-2 -3 --reverse
* 1c42d553f38c91d92aaff793a67d48d62255f9be chore: update self-references to 2.0.0
* 2082aca0c8aa7cb64320b3713391d3d1056aaec6 chore: update self-references to 1c42d553f38c91d92aaff793a67d48d62255f9be  (tag: 2.0.0)
* 0000554720dc90f987a86a43531b8595f27ea53e chore: update self-references to branch-2  (origin/pull/158, origin/branch-2)
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
