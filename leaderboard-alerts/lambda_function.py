import os
import requests

import json

from datetime import datetime, timedelta

import pandas as pd

import boto3

from slack_sdk import WebClient


s3 = boto3.client('s3')

BUCKET = 'storage9'

KEY = 'advent_of_code_leaderboard.json'


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
CHANNEL_ID = 'general'  # Replace with the ID of your Slack channel


def put(key, value):
    s3.put_object(Bucket=BUCKET, Key=key, Body=value)


def get(key):
    """If there is no key entry then return None"""

    try:
        object = s3.get_object(Bucket=BUCKET, Key=key)
    except Exception as e:
        print(e)
        return None

    value = object['Body'].read().decode('utf-8')
    return value


def get_leaderboard():
    session_cookie = os.environ['SESSION_COOKIE']
    leaderboard_id = os.environ['LEADERBOARD_ID']
    response = requests.get(
        f'https://adventofcode.com/2024/leaderboard/private/view/{leaderboard_id}.json',
        headers={'Cookie': session_cookie}
    )
    result = response.json()
    return result


def get_records(leaderboard):
    est_now = datetime.utcnow() - timedelta(hours=5)
    CURRENT_DAY = est_now.day

    members = leaderboard['members']

    rows = []
    for member_id, member in members.items():
        completion_days = member['completion_day_level']

        for day in range(1, CURRENT_DAY+1):
            for star_level, info in completion_days.get(str(day), {}).items():
                row = {
                    'id': member_id,
                    'name': member["name"],
                    'day': day,
                    'star': star_level,
                    'get_star_ts': info["get_star_ts"]
                }
                rows.append(row)

    return rows


def make_df(records):
    df = pd.DataFrame(records)
    return df


def lambda_handler(event, context):
    # Get df
    leaderboard = get_leaderboard()
    records = get_records(leaderboard)
    df = make_df(records)

    # Get old df
    df_json = get(KEY)
    old_df = pd.read_json(df_json)

    # Compare old df to df
    new_rows = df[df.get_star_ts > old_df.get_star_ts.max()]
    if not new_rows.empty:
        for _, row in new_rows.iterrows():
            star_emoji = '⭐️' if row.star == '1' else '★'
            message = f'{row["name"]} got a Star {star_emoji} for day {row.day}! Woohoo! 🥳'
            response = slack_client.chat_postMessage(channel=CHANNEL_ID, text=message)
            print(response)

        put(KEY, df.to_json())

    print(df)

    return {
        'statusCode': 200
    }

