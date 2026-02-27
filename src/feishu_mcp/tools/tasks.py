"""
tools/tasks.py — Task utilities (all using task v2 API)

Provides:
- create_task: create a task
- assign_task: assign a task to members
- add_task_to_list: add a task to a tasklist
- list_tasks: list tasks

Feishu task v2 API docs:
https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/task/create
"""

import logging
from typing import Optional

import httpx

from feishu_mcp.auth import get_auth_headers

logger = logging.getLogger(__name__)
FEISHU_BASE_URL = "https://open.feishu.cn"


def _post(path: str, payload: dict, params: dict | None = None) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            url,
            headers=get_auth_headers(),
            json=payload,
            params=params or {},
        )
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def _get(path: str, params: dict | None = None) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers(), params=params or {})
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def create_task(
    title: str,
    description: str = "",
    start_time: Optional[str] = None,
    due_time: Optional[str] = None,
) -> dict:
    """
    Create a new task.

    Args:
        title: Task title
        description: Task description (plain text, max 65536 chars)
        start_time: Task start time, Unix timestamp string or RFC3339 format
        due_time: Task due time, Unix timestamp string or RFC3339 format

    Returns:
        dict containing task_guid, title, etc.
    """
    payload: dict = {
        "summary": title,
        "description": description,
    }

    if start_time:
        payload["start"] = {"timestamp": _to_timestamp(start_time)}
    if due_time:
        payload["due"] = {"timestamp": _to_timestamp(due_time)}

    data = _post(
        "/open-apis/task/v2/tasks",
        payload=payload,
        params={"user_id_type": "open_id"},
    )
    task = data["data"]["task"]
    logger.info("Task created: task_guid=%s, title=%s", task["guid"], title)
    return task


def assign_task(task_guid: str, assignee_open_ids: list[str]) -> dict:
    """
    Assign a task to one or more members.

    Args:
        task_guid: Task GUID
        assignee_open_ids: List of assignee open_ids

    Returns:
        dict containing updated member info
    """
    members = [
        {
            "id": uid,
            "type": "user",
            "role": "assignee",
        }
        for uid in assignee_open_ids
    ]
    data = _post(
        f"/open-apis/task/v2/tasks/{task_guid}/add_members",
        payload={"members": members},
        params={"user_id_type": "open_id"},
    )
    logger.info("Task %s assigned to %d member(s)", task_guid, len(assignee_open_ids))
    return data.get("data", {})


def add_task_to_list(task_guid: str, tasklist_guid: str) -> dict:
    """
    Add a task to a tasklist (default section is root of the list).

    Args:
        task_guid: Task GUID
        tasklist_guid: Tasklist GUID

    Returns:
        dict containing operation result
    """
    data = _post(
        f"/open-apis/task/v2/tasks/{task_guid}/add_tasklist",
        payload={"tasklist_guid": tasklist_guid},
        params={"user_id_type": "open_id"},
    )
    logger.info("Task %s added to list %s", task_guid, tasklist_guid)
    return data.get("data", {})


def list_tasks(
    tasklist_guid: Optional[str] = None,
    assignee_open_id: Optional[str] = None,
    completed: Optional[bool] = None,
) -> list[dict]:
    """
    List tasks.

    Args:
        tasklist_guid: If specified, list tasks in this tasklist
        assignee_open_id: If specified, only return tasks assigned to this user
        completed: True=completed, False=incomplete, None=all

    Returns:
        List of tasks
    """
    if tasklist_guid:
        params: dict = {"page_size": 50, "user_id_type": "open_id"}
        if completed is not None:
            params["completed"] = str(completed).lower()
        data = _get(f"/open-apis/task/v2/tasklists/{tasklist_guid}/tasks", params)
        return data.get("data", {}).get("items", [])

    # No tasklist: list all tasks visible to this app
    params = {"page_size": 50, "user_id_type": "open_id"}
    if completed is not None:
        params["completed"] = str(completed).lower()
    data = _get("/open-apis/task/v2/tasks", params)
    tasks = data.get("data", {}).get("items", [])

    if assignee_open_id:
        tasks = [
            t for t in tasks
            if any(
                m.get("id") == assignee_open_id and m.get("role") == "assignee"
                for m in t.get("members", [])
            )
        ]
    return tasks


def _to_timestamp(dt_str: str) -> str:
    """
    Normalize an RFC3339 string or Unix timestamp string to a Unix timestamp string (milliseconds).
    Feishu task v2 due/start timestamp unit is milliseconds.
    """
    # Already pure digits: return as-is (pad to milliseconds if needed)
    if dt_str.isdigit():
        ts = int(dt_str)
        return str(ts * 1000 if ts < 1e12 else ts)

    from datetime import datetime, timezone, timedelta
    import re

    match = re.match(r"(.+?)([+-]\d{2}:\d{2})$", dt_str)
    if match:
        dt_part, tz_part = match.group(1), match.group(2)
        sign = 1 if tz_part[0] == "+" else -1
        h, m = int(tz_part[1:3]), int(tz_part[4:6])
        tz = timezone(timedelta(hours=sign * h, minutes=sign * m))
        dt = datetime.fromisoformat(dt_part).replace(tzinfo=tz)
    elif dt_str.endswith("Z"):
        dt = datetime.fromisoformat(dt_str[:-1]).replace(tzinfo=timezone.utc)
    else:
        tz = timezone(timedelta(hours=8))
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=tz)

    return str(int(dt.timestamp() * 1000))
