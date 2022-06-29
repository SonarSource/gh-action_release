# SonarSource GitHub release action

This action implements the release process for all SonarSource projects. It must be used when you publish a GitHub release.

It implements 3 steps that must be used depending on the kind of projects:

* [main](main): checks for releasability, promotes artifacts to release repositories and publish artifacts to binaries (if enabled)
* [download-build](download-build) and [maven-central-sync](maven-central-sync): deploys to Maven central

## Usage

### Release, Promotion and Publication

#### With Publication of Binaries

```yaml
    steps:
      - name: Configure AWS Credentials # Required for pushing the binaries
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.BINARIES_AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.BINARIES_AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.BINARIES_AWS_REGION }}
      - name: Release
        id: release
        uses: SonarSource/gh-action_release/main@v4
        with:
          publish_to_binaries: true # optional, default: true
          slack_channel: build # optional
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
          BINARIES_AWS_DEPLOY: ${{ secrets.BINARIES_AWS_DEPLOY }} # Required for pushing the binaries
          BURGRX_USER: ${{ secrets.BURGRX_USER }}
          BURGRX_PASSWORD: ${{ secrets.BURGRX_PASSWORD }}
          GITHUB_TOKEN: ${{ secrets.RELEASE_GITHUB_TOKEN }}
          SLACK_API_TOKEN: ${{ secrets.SLACK_API_TOKEN }}
      - name: Release action results
        if: always()
        run: |
          echo "${{ steps.release.outputs.releasability }}"
          echo "${{ steps.release.outputs.promote }}"
          echo "${{ steps.release.outputs.publish_to_binaries }}"
          echo "${{ steps.release.outputs.release }}"
```

#### Without Publication of Binaries

```yaml
    steps:
      - name: Release
        id: release
        uses: SonarSource/gh-action_release/main@v4
        with:
          publish_to_binaries: false
          slack_channel: build # optional
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
          BURGRX_USER: ${{ secrets.BURGRX_USER }}
          BURGRX_PASSWORD: ${{ secrets.BURGRX_PASSWORD }}
          GITHUB_TOKEN: ${{ secrets.RELEASE_GITHUB_TOKEN }}
          SLACK_API_TOKEN: ${{ secrets.SLACK_API_TOKEN }}
      - name: Release action results
        if: always()
        run: |
          echo "${{ steps.release.outputs.releasability }}"
          echo "${{ steps.release.outputs.promote }}"
          echo "${{ steps.release.outputs.publish_to_binaries }}"
          echo "${{ steps.release.outputs.release }}"
```

### Deploy to Maven Central

:warning: The `maven-central-sync` is required for OSS projects only

```yaml
    needs:
      - release
    steps:
      - name: Setup JFrog CLI
        uses: jfrog/setup-jfrog-cli@v2
        env:
          JF_ARTIFACTORY_1: ${{ secrets.REPOX_CLI_CONFIG_PUBLIC_READER }}
      - name: Get the version
        id: get_version
        run: |
          IFS=. read major minor patch build <<< "${{ github.event.release.tag_name }}"
          echo ::set-output name=build::"${build}"
      - name: Create local repository directory
        id: local_repo
        run: echo ::set-output name=dir::"$(mktemp -d repo.XXXXXXXX)"
      - name: Download Artifacts
        uses: SonarSource/gh-action_release/download-build@v4
        with:
          build-number: ${{ steps.get_version.outputs.build }}
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
      - name: Maven Central Sync
        id: maven-central-sync
        continue-on-error: true
        uses: SonarSource/gh-action_release/maven-central-sync@v4
        with:
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
        env:
          OSSRH_USERNAME: ${{ secrets.OSSRH_USERNAME }}
          OSSRH_PASSWORD: ${{ secrets.OSSRH_PASSWORD }}
      - name: Notify on failure
        if: ${{ failure() || steps.maven-central-sync.outcome == 'failure' }}
        uses: 8398a7/action-slack@v3
        with:
          text: 'Maven sync failed'
          status: failure
          fields: repo,author,eventName
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_BUILD_WEBHOOK }}
```

## Full example

:warning: The `maven-central-sync` is required for OSS projects only

```yaml
name: sonar-release

on:
  release:
    types:
      - published

jobs:
  release:
    runs-on: ubuntu-latest
    name: Release
    steps:
      - name: Configure AWS Credentials # Required for pushing the binaries
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.BINARIES_AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.BINARIES_AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.BINARIES_AWS_REGION }}
      - name: Release
        id: release
        uses: SonarSource/gh-action_release/main@v4
        with:
          publish_to_binaries: true # optional, default: true
          slack_channel: build # optional
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
          BINARIES_AWS_DEPLOY: ${{ secrets.BINARIES_AWS_DEPLOY }} # Required for pushing the binaries
          BURGRX_USER: ${{ secrets.BURGRX_USER }}
          BURGRX_PASSWORD: ${{ secrets.BURGRX_PASSWORD }}
          GITHUB_TOKEN: ${{ secrets.RELEASE_GITHUB_TOKEN }}
          SLACK_API_TOKEN: ${{ secrets.SLACK_API_TOKEN }}
      - name: Release action results
        if: always()
        run: |
          echo "${{ steps.release.outputs.releasability }}"
          echo "${{ steps.release.outputs.promote }}"
          echo "${{ steps.release.outputs.publish_to_binaries }}"
          echo "${{ steps.release.outputs.release }}"

  maven-central-sync: # Only required for OSS projects
    runs-on: ubuntu-latest
    name: Maven Central Sync
    needs:
      - release
    steps:
      - name: Setup JFrog CLI
        uses: jfrog/setup-jfrog-cli@v1
      - name: JFrog config
        run: jfrog rt config repox --url https://repox.jfrog.io/artifactory/ --apikey $ARTIFACTORY_API_KEY --basic-auth-only
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
      - name: Get the version
        id: get_version
        run: |
          IFS=. read major minor patch build <<< "${{ github.event.release.tag_name }}"
          echo ::set-output name=build::"${build}"
      - name: Create local repository directory
        id: local_repo
        run: echo ::set-output name=dir::"$(mktemp -d repo.XXXXXXXX)"
      - name: Download Artifacts
        uses: SonarSource/gh-action_release/download-build@v4
        with:
          build-number: ${{ steps.get_version.outputs.build }}
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
      - name: Maven Central Sync
        id: maven-central-sync
        continue-on-error: true
        uses: SonarSource/gh-action_release/maven-central-sync@v4
        with:
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
        env:
          OSSRH_USERNAME: ${{ secrets.OSSRH_USERNAME }}
          OSSRH_PASSWORD: ${{ secrets.OSSRH_PASSWORD }}
      - name: Notify on failure
        if: ${{ failure() || steps.maven-central-sync.outcome == 'failure' }}
        uses: 8398a7/action-slack@v3
        with:
          text: 'Maven sync failed'
          status: failure
          fields: repo,author,eventName
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_BUILD_WEBHOOK }}
```

## Versioning

Using the versioned semantic [tags](#Tags) is recommended for security and reliability.

See [GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
and [GitHub: Keeping your actions up to date with Dependabot](https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/keeping-your-actions-up-to-date-with-dependabot)
.

For convenience, it is possible to use the [branches](#Branches) following the major releases.

### Tags

All the actions in this repository are released together following semantic versioning,
ie: [`4.2.0`](https://github.com/SonarSource/gh-action_release/releases/tag/4.2.0).

```yaml
    steps:
      - uses: SonarSource/gh-action_release/main@4.2.0
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

Create a release from a maintained branches, then update the `v*` shortcut:

```shell
git fetch --tags
git update-ref -m "reset: update branch v4 to tag 4.2.5" refs/heads/v4 4.2.5
git push origin v4
```

## References

[Xtranet/RE/Artifact Management#GitHub Actions](https://xtranet-sonarsource.atlassian.net/wiki/spaces/RE/pages/872153170/Artifact+Management#GitHub-Actions)

[Semantic Versioning 2.0.0](https://semver.org/)

[GitHub: About Custom Actions](https://docs.github.com/en/actions/creating-actions/about-custom-actions)
