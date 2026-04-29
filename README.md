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
      useNpmTrustedPublisher: false # use npm Trusted Publishers (OIDC) instead of Vault token for npm publish
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

## Migrating from v6 to v7 (draft-first, `workflow_dispatch`)

v7 introduces a **draft-first** release flow that fully complies with GitHub's Release Immutability feature. The release is kept as a draft
until every downstream publication step succeeds, at which point it is atomically published (and becomes immutable). Failures leave the
draft intact so you can fix the root cause and retry with the same version — no rebuild.

### What changed

| Area             | v6                                                                           | v7                                                                                 |
|------------------|------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| Trigger          | `release: types: [published]`<br/>User publishes a release in the GitHub UI. | `workflow_dispatch` with `version` input<br/>User or CI runs the release workflow. |
| Release creation | Before workflow execution.                                                   | Workflow creates or reuses the draft release.                                      |
| Failure handling | Release and tag deleted (or kept since `v6.8.1`)                             | Draft saved; re-run the failed workflow to retry.                                  |

### Migration Steps

1. Update `.github/workflows/release.yml`:

It was already possible to trigger v6 with `workflow_dispatch` and a `version` input, but the `release: published` trigger was the default
and the `version` input was optional. For v7, the trigger is switched to `workflow_dispatch` and `version` is required.

```yaml
# Before (v6)
on:
  release:
    types: [ published ]

jobs:
  release:
    uses: SonarSource/gh-action_release/.github/workflows/main.yaml@v6
```

```yaml
# After (v7)
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Full version including build number, e.g. 1.2.3.456'
        required: true

jobs:
  release:
    uses: SonarSource/gh-action_release/.github/workflows/main.yaml@v7
    with:
      version: ${{ inputs.version }}
```

Three changes: the `on:` block (drop `release: types: [published]`, make `version` required), the `with:` block (add `version` pass-through), and the `@v6` → `@v7` pin.

2. How to trigger a release:

- **UI**: Go to **Actions → Release → Run workflow**, enter the `version` (e.g. `1.2.3.456`).
- **CLI**: `gh workflow run release.yml -f version=1.2.3.456`
- **Retry**: Re-run the failed workflow from the GitHub Actions UI ("Re-run jobs").

3. Attaching assets to the draft release:

If your repo has workflows that attach assets (e.g. SBOMs, installers) to the GitHub release, those must run **before** v7 publishes the draft. Create the draft first, attach assets using the draft's `release-id`, then call v7 (which reuses the draft and publishes it atomically). See [`gh-action_sbom`](https://github.com/SonarSource/gh-action_sbom) for an example with SBOMs.

- `isDummyProject`: The _dummy_ projects are treated differently regarding alerts and metrics. E.g.: in Datadog, the stats from dummy
  projects are excluded from some dashboards.

## Custom .npmrc File for NpmJS

When releasing a npm project using this action, you can specify a custom .npmrc file. To do this, place your .npmrc file in the
.github/workflows/ directory of the repository you wish to release. The action will automatically use this configuration.

## npm Trusted Publishers (OIDC)

Setting `useNpmTrustedPublisher: true` switches npm publishing from the Vault-stored static token to [npm Trusted Publishers](https://docs.npmjs.com/trusted-publishers) (GitHub Actions OIDC). The package is published with `--provenance`, linking it to the source commit and workflow.

**Requirements before enabling:**
1. Configure a Trusted Publisher on [npmjs.org](https://www.npmjs.com/) for each package, referencing the exact product repo, workflow filename, and environment `release`.
2. Create a `release` environment in the product repo on GitHub (Settings → Environments) and configure branch rules.
3. The calling workflow must have `id-token: write` permission (already standard for Vault-based workflows).
4. The Vault permission `development/kv/data/npmjs` is no longer needed when using Trusted Publishers.

## Recovering from a failed release

Since v6.8.1, when a release workflow fails (releasability checks, Artifactory promotion, etc.) the GitHub release and its tag are **left intact**. This preserves the ability to retry without triggering a full rebuild (~3h for some projects).

### What happens on failure

- The GitHub release stays as a draft (visible in the Releases tab).
- The Git tag stays in place.
- JFrog/S3 artifacts **are** revoked (no broken artifacts are available to downstream consumers).
- You will see a `::warning::` annotation in the Actions log and a Slack message with retry instructions.

### Retrying without rebuilding

1. Fix the root cause (e.g. merge the missing Jira fix-version, resolve the releasability check).
2. Re-run the failed workflow from the GitHub Actions UI ("Re-run jobs"). No new build is needed.

### Abandoning a failed release

If you decide not to retry with the same version:

```sh
gh release delete <tag> --cleanup-tag --yes --repo <org/repo>
```

> **Note:** After deleting the release, the tag name is protected by GitHub's resurrection protection — it cannot be reused for a new release. A new build (and new tag) is required.

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
