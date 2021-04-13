import unittest
from unittest.mock import Mock
from utils.bintray import Bintray
from vars import bintray_api_url, bintray_user, bintray_apikey, central_user, central_password

def mock_chat_post_message(channel=None, text=None):
  return {
    'message': {
      'text': text
    }
  }

slack_client = Mock()
slack_client.chat_postMessage = Mock(side_effect = mock_chat_post_message)

class TestSlack(unittest.TestCase):

  def test_slack(self):
    message = "test message"
    channel = "#test-github-action"
    bintray = Bintray(bintray_api_url, bintray_user, bintray_apikey, central_user, central_password, slack_client)
    response = bintray.alert_slack(message, channel)
    assert response["message"]["text"] == message
    slack_client.chat_postMessage.assert_called_with(channel=channel, text=message)

if __name__ == '__main__':
    unittest.main()
