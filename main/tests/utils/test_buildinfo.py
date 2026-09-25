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


def test_get_public_module_artifacts_lists_every_module_regardless_of_artifacts_to_publish():
    # A module can have no artifactsToPublish entry of its own and still need to be considered
    # for Maven Central.
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [
                {
                    'id': 'org.sonarsource.java:sonar-java-plugin:8.43.0.47668',
                    'properties': {'artifactsToPublish': 'org.sonarsource.java:sonar-java-plugin:jar'}
                },
                {'id': 'org.sonarsource.java:java-frontend:8.43.0.47668'},
                {'id': 'org.sonarsource.java:check-list:8.43.0.47668'},
            ]
        }
    })
    assert build_info.get_public_module_artifacts() == [
        'org.sonarsource.java:sonar-java-plugin:jar',
        'org.sonarsource.java:java-frontend:jar',
        'org.sonarsource.java:check-list:jar',
    ]


def test_get_public_module_artifacts_deduplicates_and_ignores_malformed_or_missing_ids():
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [
                {'id': 'org.sonarsource.dummy:dummy-maven:1.0'},
                {'id': 'org.sonarsource.dummy:dummy-maven:1.0'},
                {'id': 'malformed'},
                {},
            ]
        }
    })
    assert build_info.get_public_module_artifacts() == ['org.sonarsource.dummy:dummy-maven:jar']


def test_get_public_module_artifacts_uses_the_modules_own_declared_type_not_a_jar_guess():
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-tool:1.0',
                'artifacts': [{'name': 'dummy-tool-1.0.zip', 'type': 'zip'}]
            }]
        }
    })
    assert build_info.get_public_module_artifacts() == ['org.sonarsource.dummy:dummy-tool:zip']


def test_get_public_module_artifacts_keeps_classified_companions_but_skips_pom_sources_javadoc():
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-maven:1.0',
                'artifacts': [
                    {'name': 'dummy-maven-1.0.jar', 'type': 'jar'},
                    {'name': 'dummy-maven-1.0.pom', 'type': 'pom'},
                    {'name': 'dummy-maven-1.0-sources.jar', 'type': 'jar'},
                    {'name': 'dummy-maven-1.0-javadoc.jar', 'type': 'jar'},
                    {'name': 'dummy-maven-1.0-tests.jar', 'type': 'jar'},
                ]
            }]
        }
    })
    assert build_info.get_public_module_artifacts() == [
        'org.sonarsource.dummy:dummy-maven:jar',
        'org.sonarsource.dummy:dummy-maven:jar:tests',
    ]


def test_get_public_module_artifacts_keeps_a_pom_only_module_such_as_a_bom():
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-bom:1.0',
                'artifacts': [{'name': 'dummy-bom-1.0.pom', 'type': 'pom'}]
            }]
        }
    })
    assert build_info.get_public_module_artifacts() == ['org.sonarsource.dummy:dummy-bom:pom']


def test_get_public_module_artifacts_ignores_build_infos_mangled_type_field():
    # Real JFrog extractors write a mangled type string for jar artifacts (e.g. 'test-jar',
    # 'javadoc-jar'), not a plain extension - extension and qualifier must come from the filename.
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-maven:1.0',
                'artifacts': [
                    {'name': 'dummy-maven-1.0.jar', 'type': 'jar'},
                    {'name': 'dummy-maven-1.0.pom', 'type': 'pom'},
                    {'name': 'dummy-maven-1.0-sources.jar', 'type': 'java-source-jar'},
                    {'name': 'dummy-maven-1.0-javadoc.jar', 'type': 'javadoc-jar'},
                    {'name': 'dummy-maven-1.0-tests.jar', 'type': 'test-jar'},
                ]
            }]
        }
    })
    assert build_info.get_public_module_artifacts() == [
        'org.sonarsource.dummy:dummy-maven:jar',
        'org.sonarsource.dummy:dummy-maven:jar:tests',
    ]


def test_get_public_module_artifacts_keeps_sources_and_javadoc_when_module_has_no_plain_jar():
    # A module packaged as something other than a plain jar (here a zip) that still attaches
    # sources/javadoc jars must keep them: the Central download loop only re-fetches those on its
    # own for a genuine jar-typed entry, which this module doesn't have.
    build_info = BuildInfo({
        'buildInfo': {
            'modules': [{
                'id': 'org.sonarsource.dummy:dummy-tool:1.0',
                'artifacts': [
                    {'name': 'dummy-tool-1.0.zip'},
                    {'name': 'dummy-tool-1.0-sources.jar'},
                    {'name': 'dummy-tool-1.0-javadoc.jar'},
                ]
            }]
        }
    })
    assert build_info.get_public_module_artifacts() == [
        'org.sonarsource.dummy:dummy-tool:zip',
        'org.sonarsource.dummy:dummy-tool:jar:sources',
        'org.sonarsource.dummy:dummy-tool:jar:javadoc',
    ]
