#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


TODOIST_TASKS_URL = "https://api.todoist.com/rest/v2/tasks"
EASTERN = ZoneInfo("America/New_York")


def die(msg: str, code: int = 1) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def todoist_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def safe_json(resp: requests.Response, label: str) -> object:
    """
    Avoids JSONDecodeError and gives real diagnostics.
    """
    ct = resp.headers.get("content-type", "")
    print(f"{label}: status={resp.status_code} content-type={ct}")

    if not resp.ok:
        print(f"{label}: body (first 1200 chars):\n{resp.text[:1200]}", file=sys.stderr)
        resp.raise_for_status()

    try:
        return resp.json()
    except Exception:
        print(f"{label}: non-json body (first 1200 chars):\n{resp.text[:1200]}", file=sys.stderr)
        raise


def parse_rfc3339(dt_str: str) -> datetime:
    """
    Todoist due datetime is RFC3339. Sometimes ends with 'Z'.
    """
    # Python fromisoformat doesn't accept trailing 'Z', so swap it.
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def get_time_remaining(due_datetime_str: str) -> str:
    due_utc = parse_rfc3339(due_datetime_str)

    # Ensure timezone-aware
    if due_utc.tzinfo is None:
        due_utc = due_utc.replace(tzinfo=timezone.utc)

    # Convert to Eastern
    due_local = due_utc.astimezone(EASTERN)
    now_local = datetime.now(EASTERN)

    time_left = due_local - now_local
    if time_left.total_seconds() <= 0:
        return "⏳ Overdue"

    total_seconds = int(time_left.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    return f"⏳ {hours}h {minutes}m"


def strip_existing_countdown(content: str) -> str:
    # Remove anything from the first hourglass onward
    if "⏳" in content:
        return content.split("⏳", 1)[0].strip()
    return content.strip()


def main() -> int:
    # Use GitHub secret named TODOIST_TOKEN (recommended)
    token = (os.getenv("TODOIST_TOKEN") or os.getenv("TODOIST_API_TOKEN") or "").strip()
    if not token:
        die("Missing TODOIST_TOKEN (or TODOIST_API_TOKEN). Add as GitHub Actions secret and pass to env.")

    headers = todoist_headers(token)

    # Fetch all active tasks
    resp = requests.get(TODOIST_TASKS_URL, headers=headers, timeout=30)
    tasks = safe_json(resp, "GET /tasks")

    if not isinstance(tasks, list):
        die(f"Unexpected response shape for tasks: {type(tasks)}")

    updated = 0
    skipped = 0

    for task in tasks:
        due = task.get("due") or {}
        due_dt = due.get("datetime")
        if not due_dt:
            skipped += 1
            continue

        task_id = task.get("id")
        original_content = task.get("content") or ""

        clean_content = strip_existing_countdown(original_content)
        countdown = get_time_remaining(due_dt)
        new_content = f"{clean_content} {countdown}".strip()

        if new_content == original_content.strip():
            skipped += 1
            continue

        print(f"Updating task {task_id}: '{clean_content}' -> '{new_content}'")

        u = requests.post(
            f"https://api.todoist.com/rest/v2/tasks/{task_id}",
            headers=headers,
            json={"content": new_content},
            timeout=30,
        )

        # If update fails, show why
        if not u.ok:
            print(f"UPDATE failed for {task_id}: status={u.status_code}", file=sys.stderr)
            print(u.text[:1200], file=sys.stderr)
            u.raise_for_status()

        updated += 1

    print(f"Done. Updated={updated}, skipped={skipped}, total={len(tasks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
