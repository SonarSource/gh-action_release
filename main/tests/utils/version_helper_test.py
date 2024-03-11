import unittest

from parameterized import parameterized
from release.steps.ReleaseRequest import ReleaseRequest
from release.utils.version_helper import VersionHelper


class VersionHelperTest(unittest.TestCase):

    @parameterized.expand([
        ('sonarlint-vscode', '1.2.3+4', '1.2.3'),
        ('sonar-java', '1.2.3.4', '1.2.3.4')
    ])
    def test_as_standardized_version_should_return_expected_version(self, project: str, version: str, expected_version: str):
        release_request = ReleaseRequest('SonarSource', project, version, 'buildnumber', 'branch', 'sha1')

        actual_version = VersionHelper.as_standardized_version(release_request)

        assert actual_version == expected_version

