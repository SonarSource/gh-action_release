# GH Action release

The release workflow consists of 3 SonarSource maintained actions:

* [main](main)
* [download-build](download-build)
* [maven-central-sync](maven-central-sync)

## Usage
```yaml
jobs:
  release:
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
        uses: SonarSource/gh-action_release/download-build@v3
        with:
          build-number: ${{ steps.get_version.outputs.build }}
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
      - name: Maven Central Sync
        id: maven-central-sync
        continue-on-error: true
        uses: SonarSource/gh-action_release/maven-central-sync@v3
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