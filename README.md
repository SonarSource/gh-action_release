# SonarSource GitHub release tooling

This tooling implements the release process for all SonarSource projects. It must be used when you publish a GitHub release.

It implements 3 reusable workflows that must be used depending on the kind of projects:

* [release-publish.yml](.github/workflows/release-publish.yml): checks for releasability, promotes artifacts to release repositories and publish artifacts to binaries. It shoudl be used by any products that are delivered to customers (SonarQube, analysers and SonarLint)
* [release.yml](.github/workflows/release.yml): checks for releasability and promotes artifacts to release repositories. It shoudl be used by any products that are not delivered to customers
* [maven-central-sync.yml](.github/workflows/maven-central-sync.yml): deploys to Maven central. It should be used by any OSS pojects  

And an action:
* [helm-index](helm-index): releases a helm chart on GitHub

## Usage

### Public projects delivered to customers (SonarLint and Analysers)

```yaml
name: release

on:
  release:
    types:
      - published

jobs:
  release:
    name: Release
    uses: SonarSource/gh-action_release/.github/workflows/release-publish.yml@v5
    with:
      slack_channel: build # optional (the slack channel of the team)
    secrets:
      artifactory-api-key: ${{ secrets.ARTIFACTORY_API_KEY }}
      release-github-token: ${{ secrets.RELEASE_GITHUB_TOKEN }}
      slack-api-token: ${{ secrets.SLACK_API_TOKEN }}
      binaries-aws-deploy: ${{ secrets.BINARIES_AWS_DEPLOY }}
      binaries-aws-access-key-id: ${{ secrets.BINARIES_AWS_ACCESS_KEY_ID }}
      binaries-aws-secret-access-key: ${{ secrets.BINARIES_AWS_SECRET_ACCESS_KEY }}
      binaries-aws-region: ${{ secrets.BINARIES_AWS_REGION }}
      releasability-aws-access-key-id: ${{ secrets.RELEASABILITY_AWS_ACCESS_KEY_ID }}
      releasability-aws-secret-access-key: ${{ secrets.RELEASABILITY_AWS_SECRET_ACCESS_KEY }}
  maven-central-sync:
    needs:
      - release
    name: Maven Central Sync
    uses: SonarSource/gh-action_release/.github/workflows/maven-central-sync.yml@task/dav/build-1184-releasability
    secrets:
      artifactory-cli-config-public-reader: ${{ secrets.REPOX_CLI_CONFIG_PUBLIC_READER }}
      sonatype-oss-hosting-username: ${{ secrets.OSSRH_USERNAME }}
      sonatype-oss-hosting-password: ${{ secrets.OSSRH_PASSWORD }}
      slack-build-webhook-url: ${{ secrets.SLACK_BUILD_WEBHOOK }}
```

### Private projects delivered to customers (SonarQube and Analysers)

```yaml
name: release

on:
  release:
    types:
      - published

jobs:
  release:
    name: Release
    uses: SonarSource/gh-action_release/.github/workflows/release-publish.yml@v5
    with:
      slack_channel: build # optional (the slack channel of the team)
    secrets:
      artifactory-api-key: ${{ secrets.ARTIFACTORY_API_KEY }}
      release-github-token: ${{ secrets.RELEASE_GITHUB_TOKEN }}
      slack-api-token: ${{ secrets.SLACK_API_TOKEN }}
      binaries-aws-deploy: ${{ secrets.BINARIES_AWS_DEPLOY }}
      binaries-aws-access-key-id: ${{ secrets.BINARIES_AWS_ACCESS_KEY_ID }}
      binaries-aws-secret-access-key: ${{ secrets.BINARIES_AWS_SECRET_ACCESS_KEY }}
      binaries-aws-region: ${{ secrets.BINARIES_AWS_REGION }}
      releasability-aws-access-key-id: ${{ secrets.RELEASABILITY_AWS_ACCESS_KEY_ID }}
      releasability-aws-secret-access-key: ${{ secrets.RELEASABILITY_AWS_SECRET_ACCESS_KEY }}
```

### Other public projects

```yaml
name: release

on:
  release:
    types:
      - published

jobs:
  release:
    name: Release
    uses: SonarSource/gh-action_release/.github/workflows/release.yml@v5
    with:
      slack_channel: build # optional (the slack channel of the team)
    secrets:
      artifactory-api-key: ${{ secrets.ARTIFACTORY_API_KEY }}
      release-github-token: ${{ secrets.RELEASE_GITHUB_TOKEN }}
      slack-api-token: ${{ secrets.SLACK_API_TOKEN }}
      releasability-aws-access-key-id: ${{ secrets.RELEASABILITY_AWS_ACCESS_KEY_ID }}
      releasability-aws-secret-access-key: ${{ secrets.RELEASABILITY_AWS_SECRET_ACCESS_KEY }}
  maven-central-sync:
    needs:
      - release
    name: Maven Central Sync
    uses: SonarSource/gh-action_release/.github/workflows/maven-central-sync.yml@task/dav/build-1184-releasability
    secrets:
      artifactory-cli-config-public-reader: ${{ secrets.REPOX_CLI_CONFIG_PUBLIC_READER }}
      sonatype-oss-hosting-username: ${{ secrets.OSSRH_USERNAME }}
      sonatype-oss-hosting-password: ${{ secrets.OSSRH_PASSWORD }}
      slack-build-webhook-url: ${{ secrets.SLACK_BUILD_WEBHOOK }}
```

### Other private projects

```yaml
name: release

on:
  release:
    types:
      - published

jobs:
  release:
    name: Release
    uses: SonarSource/gh-action_release/.github/workflows/release.yml@v5
    with:
      slack_channel: build # optional (the slack channel of the team)
    secrets:
      artifactory-api-key: ${{ secrets.ARTIFACTORY_API_KEY }}
      release-github-token: ${{ secrets.RELEASE_GITHUB_TOKEN }}
      slack-api-token: ${{ secrets.SLACK_API_TOKEN }}
      releasability-aws-access-key-id: ${{ secrets.RELEASABILITY_AWS_ACCESS_KEY_ID }}
      releasability-aws-secret-access-key: ${{ secrets.RELEASABILITY_AWS_SECRET_ACCESS_KEY }}
```

### Helm Chart Release action

See [helm-index/action.yml](helm-index/action.yml)


## Versioning

All the workflow and actions in this repository are released together following semantic versioning.

For convenience, it is recomended to use the [branches](#Branches) following the major releases.

Using the versioned semantic [tags](#Tags) is also possible.

### Branches

The `master` branch shall not be referenced by end-users.

Branches prefixed with a `v` are pointers to the last major versions, ie: [`v5`](https://github.com/SonarSource/gh-action_release/tree/v5).

```yaml
    steps:
      - uses: SonarSource/gh-action_release/.github/workflows/release-publish.yml@v5
```

```yaml
    steps:
      - uses: SonarSource/gh-action_release/helm-index@v5
```

### Tags

```yaml
    steps:
      - uses: SonarSource/gh-action_release/.github/workflows/release-publish.yml@5.0.0
```

```yaml
    steps:
      - uses: SonarSource/gh-action_release/helm-index@5.0.0
```

## Technical documentation

### Releasability checks

The release process will trigger a release using the AWS IAM user and listen to the AWS SQS queue for the results of all checks.

#### Requirements

* the dedicated AWS infrastructure to be deployed (see [documentation](infra/README.md))
* the GitHub secrets `RELEASABILITY_AWS_ACCESS_KEY_ID` and `RELEASABILITY_AWS_SECRET_ACCESS_KEY`

#### Testing environement

You can test any change by:
* deploying the infrastructure on the development account
* add an environment variable to the reusable workflows:
  ```
   uses: SonarSource/gh-action_release/main@<your branch>
    env:
      RELEASABILITY_ENV_TYPE: Dev
  ```
  