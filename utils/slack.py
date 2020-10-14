from slack.errors import SlackApiError
from vars import slack_client

def alert_slack(msg,channel):
    try:
      return slack_client.chat_postMessage(
        channel=channel,
        text=msg)
    except SlackApiError as e:
      print(f"Could not notify slack: {e.response['error']}")
