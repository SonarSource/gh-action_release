import unittest

from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.ReleaseRequest import ReleaseRequest

from vars import artifactory_apikey, binaries_ssh_key, binaries_host, binaries_ssh_user, binaries_path_prefix, passphrase


class TestRevoke(unittest.TestCase):

  def setUp(self) -> None:
    self.sonar_dummy_request = ReleaseRequest('SonarSource', 'sonar-dummy', '460')

  @unittest.skipIf(binaries_ssh_key == 'no ssh key in env', 'No SSH key in environment')
  def test_revoke_release(self):
    artifactory = Artifactory(artifactory_apikey)
    binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key, binaries_path_prefix, passphrase)
#    revoke_release(artifactory,binaries, self.sonar_dummy_request)

    buildinfo = artifactory.receive_build_info(self.sonar_dummy_request)
#    artifactory.promote(self.sonar_dummy_request, buildinfo)
#    publish_all_artifacts_to_binaries(artifactory, binaries, self.sonar_dummy_request, buildinfo)
