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
      publishToCratesIo: false # for OSS projects only, publish Rust crates to https://crates.io/
      skipPythonReleasabilityChecks: false # skip releasability checks for Python projects
      skipJavascriptReleasabilityChecks: false # skip releasability checks for Javascript projects
      slackChannel: build # define the Slack channel to use for notifications
      artifactoryRoleSuffix: promoter # define the Artifactory promoter role suffix
      dryRun: false # perform a dry run execution
      createDraftRelease: true # create the draft release if it does not already exist
      pushToDatadog: true # push results to Datadog for monitoring
      isDummyProject: false # set to true if this is a dummy project (e.g. sonar-dummy)
```

Notes:

- `publishToBinaries`: Only if the binaries are delivered to customers - "binaries" is an AWS S3 bucket. The `ARTIFACTORY_DEPLOY_REPO` environment variable is required in the release Build Info. The CycloneDX
  SBOM is also uploaded next to the artifacts. Products that do not publish an SBOM to Repox are
  silently skipped.

- `publishToCratesIo`: See [Publishing to crates.io](#publishing-to-cratesio) — unlike every other
  publication target, this one **re-packages from source** instead of promoting a built artifact, and
  it is the only one that also runs under `dryRun`.

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

- `createDraftRelease`: To require a pre-created draft release set `createDraftRelease: false`. If the draft release for `version` does not already exist, the workflow fails.

- `isDummyProject`: The _dummy_ projects are treated differently regarding alerts and metrics. E.g.: in Datadog, the stats from dummy
  projects are excluded from some dashboards.

- `runnerLabel`: Optional runner-label override for every job. When omitted, existing callers keep their current runners (`github-ubuntu-latest-s`, or `sonar-xs` for publishing). Callers in organizations without those labels can pass one their runners register, such as `warp-custom-ubuntu-24-04`.

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

## Publishing to crates.io

`publishToCratesIo: true` publishes the project's crate to [crates.io](https://crates.io/) with a Vault-sourced
`CARGO_REGISTRY_TOKEN` (`development/kv/data/crates-io`, key `token`).

**This target is not a promotion.** Every other publication step downloads the artifact that was built, QA'd and
promoted through Repox. `cargo publish` has no "upload this pre-built `.crate`" mode — it always re-packages from
source — so this job checks out the calling repository at the released commit and rebuilds. The bytes on crates.io
are therefore equivalent to, but not identical with, the `.crate` promoted in Repox. A published crate version is
**public and immutable**: it cannot be overwritten, and yanking hides it without removing it.

**Version.** The `version` input carries a build number; crates.io requires SemVer. The job strips the build number
and publishes the `Major.Minor.Patch[-Mx]` prefix, accepting either separator — `1.2.3.456` and `1.2.3-456` both
publish as `1.2.3`. The dash form is what Cargo projects use, since a dot is not a legal separator in a crate
version. The version is stamped into both `Cargo.toml` and `Cargo.lock` before publishing.

**Requirements before enabling:**
1. A single-crate repository. The job stamps the first `[package]` version in `Cargo.toml`; a workspace with
   several publishable crates is not supported.
2. `Cargo.toml` declares `publish = ["crates-io"]`, a non-empty `description`, and either an SPDX `license`
   expression or a packaged `license-file`.
3. The crate name is owned by the `sonartech` crates.io account, or is unclaimed — the first publish takes
   ownership. Add a team owner immediately after the first publish:
   `cargo owner --add github:SonarSource:<team> <crate>`.
4. Vault permission for `development/kv/data/crates-io` (see below).
5. The build uploads its crate with a synthetic Maven module ID — see the next section.

### Rehearsing with `dryRun`

A crates.io version is public and immutable, so this is the one publication target that still runs when
`dryRun: true`. It resolves the version, stamps the manifest, packages the crate and compiles it in isolation,
then stops short of the upload (`cargo publish --dry-run`). A bad version string, a missing manifest field or a
file that does not build on its own fails there instead of on the publish that cannot be taken back.

`dryRun: true` runs it **regardless of `publishToCratesIo`**, so a rehearsal cannot silently skip the one
irreversible step. Callers that publish no crate at all are not affected: the job checks out the repository,
finds no `Cargo.toml`, and exits early with a notice. On a real run a missing `Cargo.toml` is an error instead,
since the only way to get there is for the caller to have set `publishToCratesIo`.

A dry run fetches only the Repox reader token, never the crates.io one, and stays silent on Slack. It therefore
works before `development/kv/data/crates-io` has been granted, which makes it the right first step when
onboarding a repository.

### Releasability and non-Maven builds

Releasability's `CheckManifestValues` reads every Repox build-info module ID through `ArtifactoryId.create`, which
requires `groupId:artifactId:version` and throws `IllegalArgumentException: <id> could not be parsed` otherwise.
`jf rt upload` without `--module` defaults the module ID to the build name, so a project with no Maven/Gradle
build-info collector fails this check on its bare project name.

The fix belongs in the calling repository's build, not here: pass a synthetic GAV, as `sonarqube-cli` does.

```bash
jf rt upload --flat=true --fail-no-op \
  --build-name="$BUILD_NAME" --build-number="$BUILD_NUMBER" \
  --module="org.sonarsource.scanner.cargo:cargo-sonar-scanner:${PROJECT_VERSION}" \
  ...
```

Every `jf rt upload` contributing to the build info needs it, or the ones that lack it register a second module
under the build name and the check throws anyway. An `org.sonarsource.*` group ID also makes the check pass rather
than merely parse: it filters on `isCommercial()` (group ID starting `com.sonarsource.`), so the module is
excluded and the check returns PASSED.

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

### Manual Maven Central re-sync

If `mavenCentralSync` was disabled at release time and the artifacts need to be pushed to Maven Central after the fact, run `scripts/manual-maven-central-sync.sh <build-name> <build-number>` locally — it mirrors the CI flow (JFrog download + Central Portal upload) without re-running the full release. See [Manual Sync — Maven Central](https://xtranet-sonarsource.atlassian.net/wiki/spaces/Platform/pages/2401697818) for the full procedure and prerequisites.

## Releasability check

To perform a releasability check for a given version without performing an actual release, run
the [releasability_check workflow](https://github.com/SonarSource/gh-action_releasability/actions/workflows/releasability_checks.yml).
The releasability checks execute the lambdas deployed from the https://github.com/SonarSource/ops-releasability project.

## Requirements

### Onboarding to ops-releasability

The repository needs to be onboarded
to [ops-releasability/projects.json](https://github.com/SonarSource/ops-releasability/blob/master/infra/projects.json)
using the `owner/repo` catalog key for the calling GitHub organization.

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

#### Additional permissions if using `publishToCratesIo`

```
development/artifactory/token/{REPO_OWNER_NAME_DASH}-private-reader
development/kv/data/crates-io
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

To create a release run the [Release workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/release.yml). The workflow
will create a **draft** GitHub Release, then post a summary with the release URL, generated notes (with a template to fill in),
and next steps: review and complete the notes, publish the draft, and communicate on
[#ops-platform-releases](https://sonarsource.enterprise.slack.com/archives/C0A6RL3L9BP) using the `/platform-comms` skill.

To update the v-branch run
the [Update v-branch workflow](https://github.com/SonarSource/gh-action_release/actions/workflows/update-v-branch.yml). The workflow will
update the v-branch to the specified tag.

For more details see [RELEASE.md](./RELEASE.md)

## References

[Xtranet/RE/Artifact Management#GitHub Actions](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/872153170/Artifact+Management#GitHub-Actions)

[Semantic Versioning 2.0.0](https://semver.org/)

[GitHub: About Custom Actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions)

[GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
