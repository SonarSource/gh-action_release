# Maven Central Sync

## Staging Profile ID
The endpoint `https://s01.oss.sonatype.org/service/local/staging/profiles` will return a xml where you can lookup the IDs for staging profiles.
```xml
<stagingProfiles>
    <data>
        <stagingProfile>
            <id>13c1877339a4cf</id>
            <name>org.sonarsource</name>
            ...
        </stagingProfile>
    </data>
</stagingProfiles>
```

## Usage
```yaml
jobs:
  release:
    steps:
      - name: Setup JFrog CLI
        uses: jfrog/setup-jfrog-cli@v1
        env:
          JF_ARTIFACTORY_1: ${{ secrets.JF_ARTIFACTORY_SECRET_1 }}
      - name: Get the version
        id: get_version
        run: |
          IFS=. read major minor patch build <<< "${{ github.event.release.tag_name }}"
          echo ::set-output name=build::"${build}"
      - name: Create local repository directory
        id: local_repo
        run: echo ::set-output name=dir::"$(mktemp -d -f repo.XXXXXXXX)"
      - name: Download Artifacts
        id: jfrog
        run: |
          cd ${{ steps.local_repo.outputs.dir }} && jfrog rt download --fail-no-op --build "${{ github.event.repository.name }}/${{ steps.get_version.outputs.build }}" sonarsource-public-releases/
      - name: Maven Central Sync
        uses: SonarSource/gh-action_LT_release/maven-central-sync@v3
        with:
          local-repo-dir: ${{ steps.local_repo.outputs.dir }}
        env:
          OSSRH_USERNAME: ${{ secrets.OSSRH_USERNAME }}
          OSSRH_PASSWORD: ${{ secrets.OSSRH_PASSWORD }}
```