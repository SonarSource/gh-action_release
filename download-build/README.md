# Download REPOX build

This action downloads all artifacts addressed by one build and one repository.
The checksums of all files are stored beside.

The resulting directory fits to the requirements to publish to maven central.

## Usage

### Download artifacts in tree dir format (required to deploy to maven central)

```yaml
on:
  branch:
    - master

jobs:
  pre-commit:
    name: "pre-commit"
    runs-on: ubuntu-latest
    steps:
      - uses: SonarSource/gh-action_release/download-build@v6
        with:
          exclusions: '-'
```

### Download artifacts in flat format (used for javadoc deployment)

```yaml
on:
  branch:
    - master

jobs:
  pre-commit:
    name: "pre-commit"
    runs-on: ubuntu-latest
    steps:
      - uses: SonarSource/gh-action_release/download-build@v6
        with:
          flat-download: true
```

## Options

| Option name          | Description                                                                                                                | Default                       |
|----------------------|----------------------------------------------------------------------------------------------------------------------------|-------------------------------|
| `dryRun`             | Used to simulate a run of the action without effectively doing anything.                                                   | `false`                       |
| `local-repo-dir`     | Empty directory to store the artifacts                                                                                     | (required)                    |
| `remote-repo`        | REPOX Repository to download from                                                                                          | `sonarsource-public-releases` |
| `build-number`       | Build number                                                                                                               | (required)                    |
| `exclusions`         | Exclude pattern from downloaded files                                                                                      | `-`                           |
| `flat-download`      | Set to true if you do not wish to have the Artifactory repository path structure created locally for your downloaded files | `false`                       |
| `download-checksums` | Set to false if you want to skip downloading the checksums                                                                 | `true`                        |
