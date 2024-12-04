import json

import boto3
from botocore.exceptions import ClientError

import os
import requests

from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient

from datetime import datetime, timedelta


CURRENT_DAY = datetime.today().day


def get_slack_token():
    secret_name = "EDWARDS_SLACKBOT_DEV_WORKSPACE_TOKEN"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']

    result = json.loads(secret)

    return result[secret_name]


slack_token = get_slack_token()
slack_client = WebClient(token=slack_token)
CHANNEL_ID = 'C083KCULCMB' # advent-of-code channel ID


def get_leaderboard():
    session_cookie = os.environ['SESSION_COOKIE']
    leaderboard_id = os.environ['LEADERBOARD_ID']
    response = requests.get(
        f'https://adventofcode.com/2024/leaderboard/private/view/{leaderboard_id}.json',
        headers={'Cookie': session_cookie}
    )
    result = response.json()
    return result


def get_stars(leaderboard, members):
    stars = {}
    for day in range(1, CURRENT_DAY+1):
        day = str(day)
        stars[day] = {'gold': 0, 'silver': 0}
        for member in members:
            day_progress = members[member]['completion_day_level'].get(day, {})
            if '1' in day_progress and '2' in day_progress:
                stars[day]['gold'] += 1
            elif '1' in day_progress:
                stars[day]['silver'] += 1
            else:
                pass

    return stars


def get_grid(stars, members):
    num_members = len(members)

    grid = [[0]*CURRENT_DAY for _ in range(num_members)]

    for day in range(1, CURRENT_DAY+1):
        j = day-1
        num_gold = stars[str(day)]['gold']
        for i in range(num_gold):
            grid[i][j] = '⭐️'

        num_silver = stars[str(day)]['silver']
        for i in range(num_silver):
            grid[num_gold+i][j] = ' ★'

    return grid


def get_table(stars, members):
    grid = get_grid(stars, members)
    day_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][:CURRENT_DAY]
    table = [day_numbers]
    table.extend(grid)
    return table


def get_string(table):
    lines = []
    for row in table:
        line = ''.join(c if c != 0 else ' ' for c in row)
        if line.isspace():
            break
        lines.append(line)
    string = '\n'.join(lines)
    return string


def get_blocks(string):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:christmas_tree: Advent of Code — <https://adventofcode.com/2024/day/{CURRENT_DAY}|Day {CURRENT_DAY}>*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f" "
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*VC Collaborative Leaderboard*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f" "
            }
        },
        {
            "type": "rich_text",
            "elements": [
                {
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "text",
                            "text": string
                        },
                    ]
                }
            ]
        },
    ]

    return blocks


def get_leaderboard_thread_ts():
    # Fetch today's messages
    now = datetime.utcnow()
    start_timestamp = datetime(now.year, now.month, now.day).timestamp()
    response = slack_client.conversations_history(channel=CHANNEL_ID, oldest=start_timestamp)
    messages = response['messages']

    leaderboard_thread_ts = None
    for message in messages:
        if ':one::two::three::four:' in message['text']:
            leaderboard_thread_ts = message['ts']
            return leaderboard_thread_ts
    else:
        return None


if __name__ == '__main__':
    leaderboard = get_leaderboard()

    members = leaderboard['members']

    stars = get_stars(leaderboard, members)
    table = get_table(stars, members)
    string = get_string(table)

    leaderboard_thread_ts = get_leaderboard_thread_ts()    
    blocks = get_blocks(string)
    if leaderboard_thread_ts:
        response = slack_client.chat_update(
            channel=CHANNEL_ID,
            ts=leaderboard_thread_ts,
            blocks=blocks
        )
    else:
        response = slack_client.chat_postMessage(
            channel=CHANNEL_ID,
            blocks=blocks,
        )

    print(response)

