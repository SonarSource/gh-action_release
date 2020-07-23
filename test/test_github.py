import unittest

from utils.github import GitHub


class TestGitHub(unittest.TestCase):

  def setUp(self) -> None:
    self.github = GitHub("http://localhost", "ABCE", "payload.json")

  def test_branch(self):
    self.assertEqual(self.github.current_branch(), "branch-1.0")

  def test_release_info(self):
    self.assertIsNone(self.github.release_info("123"))
    self.assertEqual(self.github.release_info("v1.0")["tag_name"], "v1.0")
    self.assertEqual(self.github.release_info()["tag_name"], "v1.0")

  def test_repository(self):
    self.assertEqual(self.github.repository_info()["full_name"], "malena-ebert-sonarsource/gh-action-test")
    self.assertEqual(self.github.repository_full_name(), "malena-ebert-sonarsource/gh-action-test")

if __name__ == '__main__':
    unittest.main()
