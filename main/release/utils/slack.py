from dryable import Dryable
from release.vars import slack_channel, slack_client
from slack_sdk.errors import SlackApiError


@Dryable(logging_msg='{function}({args}{kwargs})')
def notify_slack(msg):
    if slack_channel is not None:
        try:
            return slack_client.chat_postMessage(
                channel=slack_channel,
                text=msg)
        except SlackApiError as e:
            print(f"Could not notify slack: {e.response['error']}")
