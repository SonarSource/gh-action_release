# SonarSource Release Action

GitHub Action implementing the common release steps for SonarSource projects. It's recommended to use when publishing a GitHub release.

## Usage

Add `.github/workflows/release.yml` to the repository
```yaml
name: Release

# Trigger when publishing a new GitHub release
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

- `publishToBinaries` (default: *false*): enable the publication to binaries (Used only if the binaries are delivered to customers - binaries is an AWS S3 bucket)
- `publishJavadoc` (default: *false*): enable the publication of the javadoc to https://javadocs.sonarsource.org/
  > Note: When the project is releasing a public release, `publicRelease: true` has to be set.
- `javadocDestinationDirectory` (default: *use repository name*): define the subdir to use in https://javadocs.sonarsource.org/
- `publicRelease` (default: *false*): define if the release is public or private (used by `publishJavadoc`)
- `binariesS3Bucket` (default: *downloads-cdn-eu-central-1-prod*): target bucket
- `mavenCentralSync` (default: *false*): enable synchronization to Maven Central, **for OSS projects only**
- `mavenCentralSyncExclusions` (default: *none*): exclude some artifacts from synchronization
- `publishToPyPI` (default: *false*): Publish pypi artifacts to https://pypi.org/, **for OSS projects only**
- `publishToTestPyPI` (default: *false*): Publish pypi artifacts to https://test.pypi.org/, **for OSS projects only**
- `skipPythonReleasabilityChecks` (default: *false*): Skip releasability checks **for Python projects only**
- `slackChannel` (default: *build*): notification Slack channel
- `artifactoryRoleSuffix` (default: *promoter*): Artifactory promoter suffix
- `dryRun` (default: *false*): perform a dry run execution
- `pushToDatadog` (default: *true*): push results to Datadog for monitoring

## Releasability check

To perform a releasability check for a given version without performing an actual release, run the [releasability_check workflow](https://github.com/SonarSource/gh-action_releasability/actions/workflows/releasability_checks.yml).
The releasability checks execute the lambdas deployed from the https://github.com/SonarSource/ops-releasability project.

## Requirements

### Onboarding to ops-releasability

The repository needs to be onboarded to [ops-releasability/projects.json](https://github.com/SonarSource/ops-releasability/blob/master/infra/projects.json).

### Onboarding to Vault

[The repository needs to be onboarded to the Vault](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/2466316312/HashiCorp+Vault#Onboarding-a-Repository-on-Vault).

#### Required permissions

```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-promoter
development/kv/data/slack
development/kv/data/repox
development/kv/data/datadog
```

#### Additional permissions if using `publishToBinaries`

```
development/aws/sts/downloads
```

#### Additional permissions if using `publishJavadoc`

```
development/aws/sts/javadocs
```

#### Additional permissions if using `mavenCentralSync`

```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
development/kv/data/ossrh
```

#### Additional permissions if using `publishToPyPI`
```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
development/kv/data/pypi
```

#### Additional permissions if using `publishToTestPyPI`

```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
development/kv/data/pypi-test
```

## Versioning

### Tags

All the actions in this repository are released together following semantic versioning,
ie: [`5.0.0`](https://github.com/SonarSource/gh-action_release/releases/tag/5.0.0).

### Branches

Branches prefixed with a `v` are pointers to the last major versions, ie: [`v5`](https://github.com/SonarSource/gh-action_release/tree/v5).

> Note: the `master` branch is used for development and can not be referenced directly. Use a `v` branch or a tag instead.

## Development

The development is done on `master` and the `branch-*` maintenance branches.

### Dry Run

For testing purpose you may want to use this gh-action without really releasing.
There comes the dry run.

What the dry run will do and not do:

* Will not promote any artifacts in repox
* Will not push binaries
* Will not publish to slack

Instead, it will actually print the sequence of operations that would have
been performed based on the provided inputs defined in `with:` section.

### Releasing

To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow will create the GitHub Release.

To update the v-branch run the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will update the v-branch to the specified tag.


For more deails see [RELEASE.md](./RELEASE.md)

## References

[Xtranet/RE/Artifact Management#GitHub Actions](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/872153170/Artifact+Management#GitHub-Actions)

[Semantic Versioning 2.0.0](https://semver.org/)

[GitHub: About Custom Actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions)

[GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
