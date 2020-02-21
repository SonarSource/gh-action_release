from main import show_output
from main import get_release_id, revoke_release
from unittest.mock import patch


def test_get_release_id():
    release_id = get_release_id("SonarSource/sonar-dummy", "10.3")
    assert "23844035" == str(release_id)


def test_get_release_id_ref_tags():
    release_id = get_release_id("SonarSource/sonar-dummy", "refs/tags/10.3")
    assert "23844035" == str(release_id)


def test_revoke_release():
    with patch.dict('os.environ', {'GITHUB_REF': '10.3'}):
        revoke = revoke_release("SonarSource/sonar-dummy")
        print(str(revoke))
        assert revoke['draft']


def test_show_output():
    show_output("bla bla")
