# SonarSource GitHub release action

This action implements the release process for all SonarSource projects.
It must be used when you publish a GitHub release.

It implements 4 steps that must be used depending on the kind of projects:
* [main](main): checks for releasability, promotes artifacts to release repositories and publish artifacts to binaries (if enabled)
* [download-build](download-build) and [maven-central-sync](maven-central-sync): deploys to Maven central
* [helm-index](helm-index): releases a helm chart on GitHub

## Usage

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
      - name: Release
        id: release
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
          BURGRX_USER: ${{ secrets.BURGRX_USER }}
          BURGRX_PASSWORD: ${{ secrets.BURGRX_PASSWORD }}
          CIRRUS_TOKEN: ${{ secrets.CIRRUS_TOKEN }}
          PATH_PREFIX: ${{ secrets.BINARIES_PATH_PREFIX }}
          GITHUB_TOKEN: ${{ secrets.RELEASE_GITHUB_TOKEN }}
          RELEASE_SSH_USER: ${{ secrets.RELEASE_SSH_USER }}
          RELEASE_SSH_KEY: ${{ secrets.RELEASE_SSH_KEY }}
          SLACK_API_TOKEN: ${{secrets.SLACK_API_TOKEN }}
        uses: SonarSource/gh-action_release/main@v4
        with:
          publish_to_binaries: true # Used only if the binaries is delivered to costumers
          slack_channel: builders-guild
      - name: Release action results
        if: always()
        run: |
          echo "${{ steps.lt_release.outputs.releasability }}"
          echo "${{ steps.lt_release.outputs.release }}"

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
