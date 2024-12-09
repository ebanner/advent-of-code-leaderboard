import json

from bs4 import BeautifulSoup

import requests

import boto3
from botocore.exceptions import ClientError

import os
import requests

from dotenv import load_dotenv
load_dotenv()

from slack_sdk import WebClient

from datetime import datetime, timedelta


s3 = boto3.client('s3')

BUCKET = 'storage9'

CURRENT_DAY = datetime.today().day


SLACKBOT_TOKEN_NAME = "VIRTUAL_COFFEE_SLACKBOT_TOKEN" #"EDWARDS_SLACKBOT_DEV_WORKSPACE_TOKEN"
CHANNEL_ID = 'C01CZ6A66DP' #'C083KCULCMB' #'U04CYG7MEKB' #'U06RD19T690'

LEADERBOARD_THREAD_TS_KEY_NAME = f'{CURRENT_DAY}-{CHANNEL_ID}-{SLACKBOT_TOKEN_NAME}'


def put(key, value):
    s3.put_object(Bucket=BUCKET, Key=key, Body=value)


def get(key):
    """If there is no key entry then return None"""

    object = s3.get_object(Bucket=BUCKET, Key=key)

    value = object['Body'].read().decode('utf-8')
    return value


def get_slack_token():
    secret_name = SLACKBOT_TOKEN_NAME
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


def get_rows(stars):
    day_emojis = [
        '⬛️1️⃣',
        '⬛️2️⃣',
        '⬛️3️⃣',
        '⬛️4️⃣',
        '⬛️5️⃣',
        '⬛️6️⃣',
        '⬛️7️⃣',
        '⬛️8️⃣',
        '⬛️9️⃣',
        '⬛️🔟',
        '1️⃣1️⃣',
        '1️⃣2️⃣',
        '1️⃣3️⃣',
        '1️⃣4️⃣',
        '1️⃣5️⃣',
        '1️⃣6️⃣',
        '1️⃣7️⃣',
        '1️⃣8️⃣',
        '1️⃣9️⃣',
        '2️⃣0️⃣',
        '2️⃣1️⃣',
        '2️⃣2️⃣',
        '2️⃣3️⃣',
        '2️⃣4️⃣',
        '2️⃣5️⃣',
    ][:CURRENT_DAY]
    rows = []
    for day, day_emoji in zip(range(1, CURRENT_DAY+1), day_emojis):
        day_stars = stars[str(day)]
        row = [day_emoji] + [' '] + ['⭐️']*day_stars['gold'] + ['🥈']*day_stars['silver']
        rows.append(row)

    return reversed(rows)


def get_string(rows):
    slack_leaderboard = []
    for row in rows:
        row_str = ''.join(row)
        slack_leaderboard.append(row_str)

    slack_leaderboard_str = '\n'.join(slack_leaderboard)
    return slack_leaderboard_str


def get_blocks(title, string):
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*:christmas_tree: Advent of Code — <https://adventofcode.com/2024/day/{CURRENT_DAY}|{title}>*"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*VC Collaborative Leaderboard*\n\n{string}"
            }
        }
    ]

    return blocks


def get_leaderboard_thread_ts():
    try:
        leaderboard_thread_ts = get(LEADERBOARD_THREAD_TS_KEY_NAME)
        return leaderboard_thread_ts
    except:
        return None


def get_title():
    response = requests.get(f'https://adventofcode.com/2024/day/{CURRENT_DAY}')
    html_string = response.text

    soup = BeautifulSoup(html_string, "html.parser")
    day_desc = soup.find("article", class_="day-desc")
    if day_desc:
        h2 = day_desc.find("h2")
        title = h2.text
        if title:
            _, title, _ = title.split('---')
            title = title.strip()
            return title
        else:
            return None


if __name__ == '__main__':
    leaderboard = get_leaderboard()

    members = leaderboard['members']

    stars = get_stars(leaderboard, members)
    rows = get_rows(stars)
    string = get_string(rows)

    title = get_title()
    blocks = get_blocks(title, string)

    leaderboard_thread_ts = get_leaderboard_thread_ts()    
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
        put(LEADERBOARD_THREAD_TS_KEY_NAME, response['ts'])


