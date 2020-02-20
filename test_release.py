from main import show_output
from main import get_release_info,revoke_release
from unittest.mock import patch

def test_get_release_id():
  with patch.dict('os.environ', {'GITHUB_REF': '10.3'}):
    release=get_release_info("SonarSource/sonar-dummy")
    print(release['name'])
    assert "23833527"==str(release['id'])


def test_revoke_release():
  with patch.dict('os.environ', {'GITHUB_REF': '10.3'}):
    revoke=revoke_release("SonarSource/sonar-dummy")
    print(str(revoke))
    assert revoke['draft']

def test_show_output():
  show_output("bla bla")