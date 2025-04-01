# -*- coding: utf-8 -*-
"""todoist.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1EY8WvJVtPiW0jrznwb5Aoq3HtDWvBFOA
"""

import os
import pytz

os.environ['TODOIST_API_TOKEN'] = '7ae315989d9aa4d5b592b13f9d6ca5df8be44e6d'

import requests

from datetime import datetime, timezone

api_token = os.environ['TODOIST_API_TOKEN']

headers = {
    'Authorization' : f'Bearer {api_token}'
}

#Fetch all active tasks
response = requests.get('https://api.todoist.com/rest/v2/tasks', headers=headers)
tasks = response.json()

from datetime import datetime
from dateutil import parser
from zoneinfo import ZoneInfo  # Python 3.9+

def get_time_remaining(due_datetime_str):
    # Parse the due datetime string
    due_time = parser.isoparse(due_datetime_str)

    # Manually assign Eastern Time zone if it's naive
    if due_time.tzinfo is None:
        due_time = due_time.replace(tzinfo=ZoneInfo("America/New_York"))

    # Get current time in Eastern Time
    now = datetime.now(ZoneInfo("America/New_York"))

    # Calculate time difference
    time_left = due_time - now

    if time_left.total_seconds() <= 0:
        return "⏳ Overdue"

    hours, remainder = divmod(time_left.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)

    return f"⏳ {int(hours)}h {int(minutes)}m"

for task in tasks:
    if task.get("due") and task["due"].get("datetime"):
        task_id = task["id"]
        original_content = task["content"]

        # Remove any existing countdown
        clean_content = original_content.split("⏳")[0].strip()

        countdown = get_time_remaining(task["due"]["datetime"])
        new_content = f"{clean_content} {countdown}"

        # Only update if content has changed
        if new_content != original_content:
            print(f"Updating: {clean_content} → {new_content}")
            requests.post(
                f'https://api.todoist.com/rest/v2/tasks/{task_id}',
                headers=headers,
                json={"content": new_content}
            )




#rint(task["due"]["datetime"])

#print(get_time_remaining("2025-03-31T22:15:00"))
