from pytest import fixture

from release.utils.buildinfo import BuildInfo


@fixture
def build_info_with_artefacts():
    return BuildInfo({
        'buildInfo': {
            'properties': {
                'buildInfo.env.ARTIFACTS_TO_PUBLISH': 'ARTIFACTS_TO_PUBLISH'
            },
            'modules': [{
                'properties': {
                    'artifactsToPublish': 'org.sonarsource.test:test1:jar,org.sonarsource.test:test2:jar'
                }
            }]
        }
    })


@fixture
def build_info_with_artefacts_by_env():
    return BuildInfo({
        'buildInfo': {
            'properties': {
                'buildInfo.env.ARTIFACTS_TO_PUBLISH': 'ARTIFACTS_TO_PUBLISH'
            }
        }
    })


@fixture
def build_info_with_no_artefacts():
    return BuildInfo({
        "buildInfo": {
            'properties': {},
            "modules": [{}]
        }
    })


def test_get_artifacts_to_publish(build_info_with_artefacts):
    artifacts = build_info_with_artefacts.get_artifacts_to_publish()
    assert artifacts is not None
    assert 'org.sonarsource.test:test1:jar,org.sonarsource.test:test2:jar' == artifacts
    assert 'org.sonarsource.test' == build_info_with_artefacts.get_package()


def test_get_artifacts_to_publish_returns_property_when_no_module_property(build_info_with_artefacts_by_env):
    assert 'ARTIFACTS_TO_PUBLISH' == build_info_with_artefacts_by_env.get_artifacts_to_publish()


def test_get_artifacts_to_publish_prints_message_when_no_artifacts(build_info_with_no_artefacts, capsys):
    assert build_info_with_no_artefacts.get_artifacts_to_publish() is None
    captured = capsys.readouterr().out.split('\n')
    assert "No artifacts to publish" == captured[0]


@fixture
def build_info_with_artefacts_across_modules():
    return BuildInfo({
        'buildInfo': {
            'properties': {
                'buildInfo.env.ARTIFACTS_TO_PUBLISH': 'ARTIFACTS_TO_PUBLISH'
            },
            'modules': [
                {
                    'properties': {
                        'artifactsToPublish': 'org.sonarsource.dotnet:sonar-csharp-plugin:jar,org.sonarsource.dotnet:sonar-vbnet-plugin:jar'
                    }
                },
                {
                    'properties': {
                        'artifactsToPublish': 'org.sonarsource.dotnet:sonar-csharp-plugin:jar,org.sonarsource.dotnet:sonar-vbnet-plugin:jar,com.sonarsource.dotnet:sonar-csharp-enterprise-plugin:jar,com.sonarsource.dotnet:sonar-vbnet-enterprise-plugin:jar'
                    }
                }
            ]
        }
    })


def test_get_artifacts_to_publish_merges_all_modules(build_info_with_artefacts_across_modules):
    artifacts = build_info_with_artefacts_across_modules.get_artifacts_to_publish()
    artifact_list = artifacts.split(',')
    assert len(artifact_list) == 4
    assert 'org.sonarsource.dotnet:sonar-csharp-plugin:jar' in artifact_list
    assert 'org.sonarsource.dotnet:sonar-vbnet-plugin:jar' in artifact_list
    assert 'com.sonarsource.dotnet:sonar-csharp-enterprise-plugin:jar' in artifact_list
    assert 'com.sonarsource.dotnet:sonar-vbnet-enterprise-plugin:jar' in artifact_list


def test_get_artifacts_to_publish_deduplicates_across_modules(build_info_with_artefacts_across_modules):
    artifacts = build_info_with_artefacts_across_modules.get_artifacts_to_publish()
    artifact_list = artifacts.split(',')
    assert len(artifact_list) == len(set(artifact_list))
