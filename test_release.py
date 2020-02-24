from main import get_release_info, revoke_release
from unittest.mock import patch
import re

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

def test_version():
  #version_regexp = re.compile(r'^(\d*)\.(\d*)\.(\d*)\.(\d*)$')
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
      #print('Sample[%d]: %s' % (i, True if version_regexp.match(sample) else False))
      print(f"{versions[i]} {True if version_regexp.match(sample) else False}")