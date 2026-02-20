# SonarSource Release Action

GitHub Action implementing the common release steps for SonarSource projects. It's recommended to use when publishing a GitHub release.

## Usage

Add `.github/workflows/release.yml` to the repository.

All the `with` parameters are optional and have default values which are shown below.

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
    uses: SonarSource/gh-action_release/.github/workflows/main.yaml@v6
    with:
      publishToBinaries: false # enable the publication to binaries
      binariesS3Bucket: downloads-cdn-eu-central-1-prod # S3 bucket to use for the binaries
      publishJavadoc: false # enable the publication of the Javadoc to https://javadocs.sonarsource.org/
      publicRelease: false # define if the Javadoc is stored in 'sonarsource-public-releases' (or 'sonarsource-private-releases' if false)
      javadocDestinationDirectory: <repository name> # define the subdir to use in https://javadocs.sonarsource.org/
      mavenCentralSync: false # for OSS projects only, enable synchronization to Maven Central
      mavenCentralSyncExclusions: '' # exclude some artifacts from synchronization
      publishToPyPI: false # for OSS projects only, publish PyPI artifacts to https://pypi.org/
      publishToTestPyPI: false # for OSS projects only, publish PyPI artifacts to https://test.pypi.org/
      publishToNpmJS: false # for OSS projects only, publish npm artifacts to https://www.npmjs.com/
      skipPythonReleasabilityChecks: false # skip releasability checks for Python projects
      skipJavascriptReleasabilityChecks: false # skip releasability checks for Javascript projects
      slackChannel: build # define the Slack channel to use for notifications
      artifactoryRoleSuffix: promoter # define the Artifactory promoter role suffix
      dryRun: false # perform a dry run execution
      pushToDatadog: true # push results to Datadog for monitoring
      isDummyProject: false # set to true if this is a dummy project (e.g. sonar-dummy)
```

Notes:

- `publishToBinaries`: Only if the binaries are delivered to customers - "binaries" is an AWS S3 bucket. The `ARTIFACTORY_DEPLOY_REPO`
  environment variable is required in the release Build Info.
- `isDummyProject`: The _dummy_ projects are treated differently regarding alerts and metrics. E.g.: in Datadog, the stats from dummy
  projects are excluded from some dashboards.

## Custom .npmrc File for NpmJS

When releasing a npm project using this action, you can specify a custom .npmrc file. To do this, place your .npmrc file in the
.github/workflows/ directory of the repository you wish to release. The action will automatically use this configuration.

## Releasability check

To perform a releasability check for a given version without performing an actual release, run
the [releasability_check workflow](https://github.com/SonarSource/gh-action_releasability/actions/workflows/releasability_checks.yml).
The releasability checks execute the lambdas deployed from the https://github.com/SonarSource/ops-releasability project.

## Requirements

### Onboarding to ops-releasability

The repository needs to be onboarded
to [ops-releasability/projects.json](https://github.com/SonarSource/ops-releasability/blob/master/infra/projects.json).

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

#### Additional permissions if using `publishToNpmJS`

```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
development/kv/data/npmjs
```

## Versioning

### Tags

All the actions in this repository are released together following semantic versioning,
ie: [`5.0.0`](https://github.com/SonarSource/gh-action_release/releases/tag/5.0.0).

### Branches

Branches prefixed with a `v` are pointers to the last major versions, ie: [`v6`](https://github.com/SonarSource/gh-action_release/tree/v6).

> Note: Development branches (including `master`) can be referenced from consumer repositories for testing purposes.
> For production use, always reference a `v` branch or a specific tag.

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

⚠️ At the moment, the release requires an exception in the GitHub ruleset:
see [xtranet/Platform/Branch Protection Organization Ruleset - GitHub#Exception Record](https://xtranet-sonarsource.atlassian.net/wiki/spaces/Platform/pages/4008509456/Branch+Protection+Organization+Ruleset+-+GitHub#Exception-Record)

To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow
will create the GitHub Release.

To update the v-branch run
the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will
update the v-branch to the specified tag.

For more deails see [RELEASE.md](./RELEASE.md)

## References

[Xtranet/RE/Artifact Management#GitHub Actions](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/872153170/Artifact+Management#GitHub-Actions)

[Semantic Versioning 2.0.0](https://semver.org/)

[GitHub: About Custom Actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions)

[GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
