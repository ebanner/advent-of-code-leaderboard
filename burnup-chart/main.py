import os

import requests

import pandas as pd

import gspread
from gspread_dataframe import set_with_dataframe

from dotenv import load_dotenv
load_dotenv()


def get_leaderboard():
    session_cookie = os.environ['Cookie']
    leaderboard_id = os.environ['LEADERBOARD_ID']
    aoc_url = f'https://adventofcode.com/2024/leaderboard/private/view/{leaderboard_id}.json'
    response = requests.get(aoc_url, headers={'Cookie': session_cookie})
    leaderboard = response.json()

    print(leaderboard)

    return leaderboard


def get_df(leaderboard):
    def get_df_for_user(completion_day_level, user_id):
        rows = []
        for day, day_progress in completion_day_level.items():
            try:
                ts = day_progress['1']['get_star_ts']
                row = (user_id, day, ts)
                rows.append(row)
            except:
                pass

            try:
                ts = day_progress['2']['get_star_ts']
                row = (user_id, day, ts)
                rows.append(row)
            except:
                pass

        df = pd.DataFrame(rows, columns=['user_id', 'day', 'ts'])
        df = df.sort_values(by='ts').reset_index(drop=True)
        df['star_number'] = range(1, len(df)+1)
        df = df[['user_id', 'day', 'star_number', 'ts']]
        return df


    df = pd.DataFrame(columns=['user_id', 'day', 'star_number', 'ts'])
    for user_id, data in leaderboard['members'].items():
        completion_day_level = data['completion_day_level']
        user_df = get_df_for_user(completion_day_level, user_id)
        df = pd.concat([df, user_df])

    user_id_to_name = {user_id: data['name'] for user_id, data in leaderboard['members'].items()}
    df['name'] = df['user_id'].map(user_id_to_name)
    df = df[['user_id', 'name', 'day', 'star_number', 'ts']]

    print(df)

    return df


def write_google_sheet(df):
    gsheets_client = gspread.service_account(filename='service_account.json')
    spreadsheet = gsheets_client.open('aoc.csv')
    worksheet = spreadsheet.worksheet('Sheet1')
    set_with_dataframe(worksheet, df)
    print("Data written successfully!")


if __name__ == '__main__':
    leaderboard = get_leaderboard()
    df = get_df(leaderboard)
    write_google_sheet(df)

