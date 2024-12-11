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


def fill(rows):
    max_row_len = 2
    for row in rows:
        max_row_len = max(max_row_len, len(row))

    for row in rows:
        if len(row) < max_row_len:
            for _ in range(max_row_len-len(row)):
                row.append(0)
    return rows


def transpose(rows):
    n = len(rows)
    m = len(rows[0])

    transposed_rows = [[0]*n for _ in range(m)]
    for i in range(m):
        for j in range(n):
            transposed_rows[i][j] = rows[j][i]

    return transposed_rows


def get_rows(stars, start, end, compact=False):
    day_emojis = [None, '1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    rows = []
    for day in range(start, end+1):
        row = []
        num_gold = stars[str(day)]['gold']
        if not compact:
            for _ in range(num_gold):
                row.append('⭐️')
        else:
            row.append('⭐️')
            if num_gold > 4:
                row.append('⭐️')
            if num_gold > 8:
                row.append('⭐️')
            # row.append(day_emojis[num_gold])

        num_silver = stars[str(day)]['silver']
        for _ in range(num_silver):
            row.append('🥈')

        rows.append(row)

    return transpose(fill(rows))


def get_table(stars, members, start=1, end=10, compact=False):
    grid = get_rows(stars, start, end, compact)
    start_idx = start - 1
    end_idx = end - 1
    day_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'][start_idx%10:end_idx%10+1]
    table = [day_numbers]
    table.extend(grid)
    return table


def get_string(table):
    lines = []
    for row in table:
        line = ''.join(c if c != 0 else '⬛️' for c in row)
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

    tables = [
        get_table(stars, members, start=1, end=10, compact=True),
        get_table(stars, members, start=11, end=11)
    ]

    string = '\n\n'.join(get_string(table) for table in tables)

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


