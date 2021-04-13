import unittest
import re
import os

from unittest.mock import patch
from utils.github import GitHub
from vars import githup_api_url, github_token

class TestGitHub(unittest.TestCase):

  def setUp(self) -> None:
    self.github = GitHub("http://localhost", github_token, "test/payload.json")

  def test_branch(self):
    self.assertEqual(self.github.current_branch(), "branch-1.0")

  def test_release_info(self):
    self.assertIsNone(self.github.release_info("123"))
    self.assertEqual(self.github.release_info("v1.0")["tag_name"], "v1.0")
    self.assertEqual(self.github.release_info()["tag_name"], "v1.0")

  def test_repository(self):
    self.assertEqual(self.github.repository_info()["full_name"], "malena-ebert-sonarsource/gh-action-test")
    self.assertEqual(self.github.repository_full_name(), "malena-ebert-sonarsource/gh-action-test")

  # def test_revoke_release(self):
  #   with patch.dict('os.environ', {'GITHUB_REF': '10.0.0.422'}):
  #     revoke = self.github.revoke_release("SonarSource/sonar-dummy", "10.0.0.422")
  #     print(str(revoke))
  #     assert revoke['draft']

  def test_version(self):
    # version_regexp = re.compile(r'^(\d*)\.(\d*)\.(\d*)\.(\d*)$')
    version_regexp = re.compile(r'^\d+(\.\d+){2,3}$')
    versions = ['dsvfsdf',
                '1.a.3',
                '1.2.4',
                '10.0.0.1234',
                '1.4..5.6',
                '0.3.1',
                'a.b.c.d',
                '1,2,3']
    for i, sample in enumerate(versions):
      # print('Sample[%d]: %s' % (i, True if version_regexp.match(sample) else False))
      print(f"{versions[i]} {True if version_regexp.match(sample) else False}")


if __name__ == '__main__':
    unittest.main()
