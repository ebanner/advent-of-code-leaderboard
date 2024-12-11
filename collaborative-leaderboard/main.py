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

CURRENT_DAY = 11
if CURRENT_DAY > 25:
    print('Advent of Code is over!')
    exit(1)


SLACKBOT_TOKEN_NAME = "EDWARDS_SLACKBOT_DEV_WORKSPACE_TOKEN" #"VIRTUAL_COFFEE_SLACKBOT_TOKEN" 
CHANNEL_ID = 'C083KCULCMB' #'C01CZ6A66DP' #'U04CYG7MEKB' #'U06RD19T690'

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


def get_grid(stars, members, start, end):
    num_members = len(members)

    grid = [[0]*(end-start+1) for _ in range(num_members)]

    for day in range(start, end+1):
        j = day-start
        num_gold = stars[str(day)]['gold']
        for i in range(num_gold):
            grid[i][j] = '⭐️'

        num_silver = stars[str(day)]['silver']
        for i in range(num_silver):
            grid[num_gold+i][j] = '🥈'

    return grid


def get_table(stars, members, start=1, end=10):
    if end < start:
        return None
    grid = get_grid(stars, members, start, end)
    day_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟', '1️⃣', '2️⃣', '3️⃣'][start-1:end]
    table = [day_numbers]
    if start > 10:
        table.append(['1️⃣']*(end-start+1))
        table = list(reversed(table))
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
    stars['10'] = {'gold': 3, 'silver': 2}
    stars['11'] = {'gold': 3, 'silver': 2}

    tables = []
    table = get_table(stars, members, start=1, end=10)
    tables.append(table)
    table = get_table(stars, members, start=11, end=CURRENT_DAY)
    if table != None:
        tables.append(table)

    string = '\n\n\n'.join([get_string(table) for table in tables])

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


