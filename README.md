# SonarSource GitHub release action

This action implements the release process for all SonarSource projects. It must be used when you publish a GitHub release.

## Usage

### Release, Promotion and Publication

```yaml
---
name: sonar-release
# This workflow is triggered when publishing a new github release
# yamllint disable-line rule:truthy
on:
  release:
    types:
      - published

jobs:
  release:
    permissions:
      id-token: write
      contents: write
    uses: SonarSource/gh-action_release/.github/workflows/main.yaml@v5
    with:
      publishToBinaries: true
      mavenCentralSync: true # for OSS projects only
```

Available options:

- publishToBinaries (default: false): enable the publication to binaries
- publishJavadoc (default: false): enable the publication of the javadoc to https://javadocs.sonarsource.org/
- javadocDestinationDirectory (default: use repository name): define the subdir to use in https://javadocs.sonarsource.org/
- binariesS3Bucket (default: downloads-cdn-eu-central-1-prod): target bucket
- mavenCentralSync (default: false): enable synchronization to Maven Central, **for OSS projects only**
- mavenCentralSyncExclusions (default: none): exclude some artifacts from synchronization
- publishToPyPI (default: false): Publish pypi artifacts to https://pypi.org/, **for OSS projects only**
- publishToTestPyPI (default: false): Publish pypi artifacts to https://test.pypi.org/, **for OSS projects only**
- skipPythonReleasabilityChecks (default: false): Skip releasability checks **for Python projects only**
- slackChannel (default: build): notification Slack channel
- artifactoryRoleSuffix (default: promoter): Artifactory promoter suffix
- dryRun (default: false): perform a dry run execution

### Releasability check

If one wants to perform a releasability check for a given version without
performing an actual release, the `releasability-check` workflow can be used.
Here is an example:

``` yaml
---
name: my-releasability-check

on:
  workflow_dispatch:
    inputs:
      version:
        description: Version number to check releasability on
        required: true

jobs:
  release:
    permissions:
      id-token: write
      contents: write
    uses: SonarSource/gh-action_release/.github/workflows/releasability-check.yaml@<id>
```

## Dry Run

For testing purpose you may want to use this gh-action without really releasing.
There comes the dry run.

What the dry run will do and not do:

* Will not communicate with burger
* Will not promote any artifacts in repox
* Will not push binaries
* Will not publish to slack

Instead, it will actually print the sequence of operations that would have
been performed based on the provided inputs defined in `with:` section.

## Versioning

Using the versioned semantic [tags](#Tags) is recommended for security and reliability.

See [GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
and [GitHub: Keeping your actions up to date with Dependabot](https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/keeping-your-actions-up-to-date-with-dependabot)
.

For convenience, it is possible to use the [branches](#Branches) following the major releases.

### Tags

All the actions in this repository are released together following semantic versioning,
ie: [`5.0.0`](https://github.com/SonarSource/gh-action_release/releases/tag/5.0.0).

```yaml
    steps:
      - uses: SonarSource/gh-action_release/main@5.0.0
```

### Branches

The `master` branch shall not be referenced by end-users.

Branches prefixed with a `v` are pointers to the last major versions, ie: [`v4`](https://github.com/SonarSource/gh-action_release/tree/v4).

```yaml
    steps:
      - uses: SonarSource/gh-action_release/main@v4
```

Note: use only branches with precaution and confidence in the provider.

## Development

The development is done on `master` and the `branch-*` maintenance branches.

### Release

Create a release from a maintained branches, then update the `v*` shortcut.

Prepare a pull-request with the self-references updated to the current changeset:

```shell
next_version=5.3.1
git checkout master
git pull
git checkout -b release/update-self-references
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)master,\1${next_version},g"
git commit -m "chore: update self-references to ${next_version}" -a
next_ref=$(git show -s --pretty=format:'%H')
git grep -Hl SonarSource/gh-action_release -- .github/workflows/ | xargs sed -i "s,\(SonarSource/gh-action_release/.*@\)${next_version},\1${next_ref},g"
git commit -m "chore: update self-references to $next_ref" -a
git tag "$next_version"
git checkout master -- .
git commit -m "chore: update self-references to master" -a
gh pr create # TO BE MERGED ON MASTER BEFORE ANY OTHER PR
git push origin "$next_version"
```

Browse to the [releases](https://github.com/SonarSource/gh-action_release/releases) page and create a new release from the new tag created
above.

The `v-` branch update is now automated by the [release.yml](.github/workflows/release.yml) workflow.
The following manual steps are not required anymore:

```shell
git fetch --tags
git update-ref -m "reset: update branch v4 to tag 4.2.5" refs/heads/v4 4.2.5
git push origin v4
```

## Requirements

As of version 5.0.0,
[the repository needs to be onboarded to the Vault](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/2466316312/HashiCorp+Vault#Onboarding-a-Repository-on-Vault).

The following secrets and permissions are required:

- development/artifactory/token/{REPO_OWNER_NAME_DASH}-promoter
- development/kv/data/slack
- development/kv/data/repox
- development/kv/data/burgr
- secrets.GITHUB_TOKEN (provided by the GitHub Action runner)

Additionally,

If using `publishToBinaries` option:

- development/aws/sts/downloads

If using `mavenCentralSync` option:

- development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
- development/kv/data/ossrh

If using `publishToPyPI` option:

- development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
- development/kv/data/pypi

If using `publishToTestPyPI` option:

- development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
- development/kv/data/pypi-test

## References

[Xtranet/RE/Artifact Management#GitHub Actions](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/872153170/Artifact+Management#GitHub-Actions)

[Semantic Versioning 2.0.0](https://semver.org/)

[GitHub: About Custom Actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions)
