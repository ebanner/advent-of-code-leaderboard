import os
import requests

from dotenv import load_dotenv
load_dotenv()


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

    day = 1

    for j in range(1, day+1):
        num_gold = stars[str(j)]['gold']
        for i in range(num_gold):
            grid[i][j-1] = '⭐️'

        num_silver = stars[str(j)]['silver']
        for i in range(num_silver):
            grid[num_gold+i+1][j-1] = '★'

    return grid


def get_table(stars, members):
    grid = get_grid(stars, members)
    day_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'][:CURRENT_DAY]
    table = day_numbers
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


if __name__ == '__main__':
    leaderboard = get_leaderboard()

    members = leaderboard['members']

    stars = get_stars(leaderboard, members)
    table = get_table(stars, members)
    string = get_string(table)
    print(string)

