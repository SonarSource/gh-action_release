from main import get_release_info, revoke_release
from unittest.mock import patch


def test_get_release_id():
    release_info = get_release_info("SonarSource/sonar-dummy", "10.3")
    assert "23844035" == str(release_info.get('id'))


def test_get_release_id_ref_tags():
    release_info = get_release_info("SonarSource/sonar-dummy", "refs/tags/10.3")
    assert "23844035" == str(release_info.get('id'))


def test_revoke_release():
    with patch.dict('os.environ', {'GITHUB_REF': '10.3'}):
        revoke = revoke_release("SonarSource/sonar-dummy")
        print(str(revoke))
        assert revoke['draft']
