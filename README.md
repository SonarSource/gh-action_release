# SonarSource GitHub release action

This action implements the release process for all SonarSource projects. It must be used when you publish a GitHub release.

## Usage

### Release, Promotion and Publication

## Full example 

:warning: The `maven-central-sync` is required for OSS projects only, to disable it remove mavenCentralSync or set it to False

```yaml
---
  name: sonar-release
  # This workflow is triggered when publishing a new github release
  # yamllint disable-line rule:truthy
  on:
    release:
      types:
        - published
    workflow_dispatch:
  
  env:
    PYTHONUNBUFFERED: 1
  
  jobs:
    release:
      permissions:
        id-token: write
        contents: write
      uses: SonarSource/gh-action_release/.github/workflows/main.yaml@v5
      with:
        publishToBinaries: true
        mavenCentralSync: true

```

## Versioning

Using the versioned semantic [tags](#Tags) is recommended for security and reliability.

See [GitHub: Using tags for release management](https://docs.github.com/en/actions/creating-actions/about-custom-actions#using-tags-for-release-management)
and [GitHub: Keeping your actions up to date with Dependabot](https://docs.github.com/en/code-security/supply-chain-security/keeping-your-dependencies-updated-automatically/keeping-your-actions-up-to-date-with-dependabot)
.

For convenience, it is possible to use the [branches](#Branches) following the major releases.

### Tags

All the actions in this repository are released together following semantic versioning,
ie: [`5.0`](https://github.com/SonarSource/gh-action_release/releases/tag/5.0).

```yaml
    steps:
      - uses: SonarSource/gh-action_release/main@5.0
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
