import os
import requests

from dotenv import load_dotenv
load_dotenv()

import pandas as pd


CURRENT_DAY = 1


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
    DAY = 1

    members = leaderboard['members']

    rows = []
    for member_id, member in members.items():
        completion_days = member['completion_day_level']

        for day in range(1, DAY+1):
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


if __name__ == '__main__':
    leaderboard = get_leaderboard()
    records = get_records(leaderboard)
    df = make_df(records)
    print(df)

