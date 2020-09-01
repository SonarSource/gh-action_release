import os
import unittest

from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.ReleaseRequest import ReleaseRequest
from steps.release import revoke_release, publish_all_artifacts_to_binaries

from vars import githup_api_url, github_token, github_event_path, burgrx_url, burgrx_user, burgrx_password, \
  artifactory_apikey, distribute_target, bintray_api_url, bintray_user, bintray_apikey, central_user, central_password, \
  binaries_ssh_key, binaries_host, binaries_ssh_user, binaries_path_prefix, passphrase, run_rules_cov, distribute, repo, ref, publish_to_binaries, \
  slack_client


class TestRevoke(unittest.TestCase):

  def setUp(self) -> None:
    self.sonar_dummy_request = ReleaseRequest('SonarSource', 'sonar-dummy', '460')


  def test_revoke_release(self):
    artifactory = Artifactory(artifactory_apikey)
    binaries = Binaries(binaries_host, binaries_ssh_user, binaries_ssh_key, binaries_path_prefix, passphrase)
    revoke_release(artifactory,binaries, self.sonar_dummy_request)

    buildinfo = artifactory.receive_build_info(self.sonar_dummy_request)
    artifactory.promote(self.sonar_dummy_request, buildinfo)
    publish_all_artifacts_to_binaries(artifactory, binaries, self.sonar_dummy_request, buildinfo)
