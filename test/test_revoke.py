import os
import unittest

from utils.artifactory import Artifactory
from utils.binaries import Binaries
from utils.burgr import Burgr
from utils.ReleaseRequest import ReleaseRequest
from steps.release import release, revoke_release

class TestRevoke(unittest.TestCase):

  def setUp(self) -> None:
    self.artifactory_apikey = os.environ.get('ARTIFACTORY_API_KEY', 'no api key in env')
    self.binaries_host = 'binaries.sonarsource.com'
    self.binaries_ssh_user=os.environ.get('RELEASE_SSH_USER','no ssh user in env')
    self.binaries_ssh_key=os.environ.get('RELEASE_SSH_KEY','no ssh key in env')
    self.burgrx_url = 'https://burgrx.sonarsource.com'
    self.burgrx_user = os.environ.get('BURGRX_USER', 'no burgrx user in env')
    self.burgrx_password = os.environ.get('BURGRX_PASSWORD', 'no burgrx password in env')
    self.sonar_dummy_request = ReleaseRequest('SonarSource', 'sonar-dummy', '460')


  def test_revoke_release(self):
    artifactory = Artifactory(self.artifactory_apikey)
    binaries = Binaries(self.binaries_host, self.binaries_ssh_user, self.binaries_ssh_key)
    burgr = Burgr(self.burgrx_url,self.burgrx_user,self.burgrx_password,self.sonar_dummy_request)
    revoke_release(artifactory,binaries, self.sonar_dummy_request)
    release(artifactory,binaries,self.sonar_dummy_request,burgr,False)
