# Sonarqube and Languages Team release action

## Usage

Create a release in github with the full version number as a tag, it will automatically trigger the action.
If the release fail, everything is rollbacked and the release is reverted to draft.
You can retrigger the release by publishing the draft

### Example workflow

```yaml
name: sonar-release
# This workflow is triggered when publishing a new github release
on: 
  release:
    types:
      - published

env:
  PYTHONUNBUFFERED: 1
  
jobs:
  sonar_release:
    runs-on: ubuntu-latest
    name: Start release process
    steps:
      - name: LT release
        id: lt_release
        with:
          publish_to_binaries: false
          distribute_target: "SQ-test"
          run_rules_cov: false
          slack_channel: test-github-action
        env:
          ARTIFACTORY_API_KEY: ${{ secrets.ARTIFACTORY_API_KEY }}
          BINTRAY_USER: ${{ secrets.BINTRAY_USER }}
          BINTRAY_TOKEN: ${{ secrets.BINTRAY_TOKEN }}
          BURGRX_USER: ${{ secrets.BURGRX_USER }}
          BURGRX_PASSWORD: ${{ secrets.BURGRX_PASSWORD }}
          CENTRAL_USER: ${{ secrets.CENTRAL_USER }}
          CENTRAL_PASSWORD: ${{ secrets.CENTRAL_PASSWORD }}
          CIRRUS_TOKEN: ${{ secrets.CIRRUS_TOKEN }}
          GPG_PASSPHRASE: ${{ secrets.GPG_PASSPHRASE }}
          PATH_PREFIX: ${{ secrets.BINARIES_PATH_PREFIX }}
          GITHUB_TOKEN: ${{ secrets.RELEASE_GITHUB_TOKEN }}
          RELEASE_SSH_USER: ${{ secrets.RELEASE_SSH_USER }}
          RELEASE_SSH_KEY: ${{ secrets.RELEASE_SSH_KEY }}
          SLACK_API_TOKEN: ${{secrets.SLACK_API_TOKEN }}  
        # Put your action repo here
        uses: SonarSource/gh-action_LT_release@tom/slack

      - name: Check outputs
        if: always()
        run: |
          echo "${{ steps.lt_release.outputs.releasability }}"
          echo "${{ steps.lt_release.outputs.release }}"
```

### Inputs

| Input                                             | Description                                        |
|------------------------------------------------------|-----------------------------------------------|
| `distribute` _(optional)_ _(true/false)_ | enable distribution to maven central (only for OSS projects) |
| `publish_to_binaries` _(optional)_  _(true/false)_| enable publication of artifacts to binaries.sonarsource.com  |
| `attach_artifacts_to_github_release` _(optional)_ _(true/false)_| attach artifacts to the github release tag (this currently does not work)|
| `run_rules_cov` _(optional)_ _(true/false)_| run the rules-cov program at the end of the release (only for languages plugins) |
| `slack_channel` _(optional)_ _(true/false)_| enable slack notification on the specified channel  |
| `distribute_target` _(optional)_ _(true/false)_| enable bintray distribution to the specified target repository |


