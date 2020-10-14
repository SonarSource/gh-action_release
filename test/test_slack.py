import unittest
from utils.bintray import Bintray
from slack.errors import SlackApiError

from vars import githup_api_url, github_token, github_event_path, burgrx_url, burgrx_user, burgrx_password, \
  artifactory_apikey, distribute_target, bintray_api_url, bintray_user, bintray_apikey, central_user, central_password, \
  binaries_ssh_key, binaries_host, binaries_ssh_user, binaries_path_prefix, passphrase, run_rules_cov, distribute, repo, ref, publish_to_binaries, \
  slack_client

class TestSlack(unittest.TestCase):

  def test_slack(self):
    bintray = Bintray(bintray_api_url, bintray_user, bintray_apikey, central_user, central_password)
    response = bintray.alert_slack("test message","#test-github-action")    
    assert response["message"]["text"] == "test message"

if __name__ == '__main__':
    unittest.main()
