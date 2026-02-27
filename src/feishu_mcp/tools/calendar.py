"""
tools/calendar.py — Calendar utilities

Provides:
- get_or_create_group_calendar: get or create a shared calendar for a group
- create_calendar_event: create an event (with optional video meeting)
- add_event_attendees: add attendees (triggers Feishu invitation popup)
- list_calendar_events: list events on a calendar

⚠️ Token note:
  - Using tenant_access_token: organizer is the Bot (allowed, but assign_hosts unavailable)
  - To use a real user as organizer: set FEISHU_USER_ACCESS_TOKEN in .env (see auth.py)
"""

import logging
from typing import Optional

import httpx

from feishu_mcp.auth import get_auth_headers

logger = logging.getLogger(__name__)
FEISHU_BASE_URL = "https://open.feishu.cn"


def _get(path: str, params: dict | None = None, use_user_token: bool = False) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers(use_user_token), params=params or {})
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def _post(path: str, payload: dict, use_user_token: bool = False) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, headers=get_auth_headers(use_user_token), json=payload)
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def get_or_create_group_calendar(chat_id: str) -> str:
    """
    Get the shared calendar ID associated with a group. Creates one if it doesn't exist.

    Feishu calendar types:
    - primary: personal main calendar
    - shared:  shared calendar (group calendars are this type)
    - google / exchange: external sync calendars

    Args:
        chat_id: Group ID (starts with oc_)

    Returns:
        calendar_id (e.g. feishu.cn_xxxxxx@group.calendar.feishu.cn)
    """
    # First try listing calendars the app can access, find type=shared with chat_id in summary
    data = _get("/open-apis/calendar/v4/calendars", params={"page_size": 50})
    calendars = data.get("data", {}).get("calendar_list", [])

    # Try to find an existing shared calendar whose summary contains the chat_id
    for cal in calendars:
        if cal.get("type") == "shared" and chat_id in cal.get("summary", ""):
            logger.info("Found existing group calendar: %s", cal["calendar_id"])
            return cal["calendar_id"]

    # Not found — create a new shared calendar named: GroupCalendar-{chat_id}
    logger.info("No shared calendar found for group %s, creating one...", chat_id)
    create_data = _post(
        "/open-apis/calendar/v4/calendars",
        payload={
            "summary": f"GroupCalendar-{chat_id}",
            "description": f"Automatically created by MCP bot for group {chat_id}",
            "permissions": "public",
        },
    )
    calendar_id = create_data["data"]["calendar"]["calendar_id"]
    logger.info("Group calendar created: %s", calendar_id)
    return calendar_id


def create_calendar_event(
    calendar_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    is_online: bool = False,
    use_user_token: bool = True,
) -> dict:
    """
    Create an event on the specified calendar.

    Args:
        calendar_id: Calendar ID
        summary: Event title
        start_time: Start time in RFC3339 format, e.g. "2026-03-26T10:00:00+08:00"
        end_time: End time in RFC3339 format
        description: Event description (supports HTML tags)
        is_online: Whether to create an online video meeting
        use_user_token: Use user_access_token (True = real user as organizer, recommended)

    Returns:
        dict containing event_id and other fields
    """
    payload: dict = {
        "summary": summary,
        "description": description,
        "start_time": {"timestamp": _rfc3339_to_timestamp(start_time), "timezone": "Asia/Shanghai"},
        "end_time": {"timestamp": _rfc3339_to_timestamp(end_time), "timezone": "Asia/Shanghai"},
        "attendee_ability": "can_see_others",
        "need_notification": True,
    }

    if is_online:
        payload["vchat"] = {
                "vc_type": "vc",  # Feishu video conference
        }

    data = _post(
        f"/open-apis/calendar/v4/calendars/{calendar_id}/events",
        payload=payload,
        use_user_token=use_user_token,
    )
    event = data["data"]["event"]
    logger.info("Calendar event created: event_id=%s, summary=%s", event["event_id"], summary)
    return event


def add_event_attendees(
    calendar_id: str,
    event_id: str,
    attendee_open_ids: list[str],
    use_user_token: bool = True,
) -> dict:
    """
    Add attendees to a calendar event. Feishu automatically sends an acceptance popup to each attendee.

    Args:
        calendar_id: Calendar ID
        event_id: Event ID
        attendee_open_ids: List of attendee open_ids
        use_user_token: Use user identity (recommended True for better UX)

    Returns:
        dict containing the result
    """
    attendees = [
        {"type": "user", "user_id": uid}
        for uid in attendee_open_ids
    ]
    payload = {
        "attendees": attendees,
        "need_notification": True,  # Trigger invitation popup
    }
    data = _post(
        f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}/attendees",
        payload=payload,
        use_user_token=use_user_token,
    )
    logger.info("Added %d attendee(s) to event", len(attendee_open_ids))
    return data.get("data", {})


def list_calendar_events(
    calendar_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
) -> list[dict]:
    """
    List events on a calendar.

    Args:
        calendar_id: Calendar ID
        start_time: Filter start time (RFC3339), optional
        end_time: Filter end time (RFC3339), optional

    Returns:
        List of events
    """
    params: dict = {"page_size": 50}
    if start_time:
        params["start_time"] = _rfc3339_to_timestamp(start_time)
    if end_time:
        params["end_time"] = _rfc3339_to_timestamp(end_time)

    data = _get(f"/open-apis/calendar/v4/calendars/{calendar_id}/events", params=params)
    return data.get("data", {}).get("items", [])


def _rfc3339_to_timestamp(dt_str: str) -> str:
    """
    Convert an RFC3339 string to a Unix timestamp string (required by the Feishu Calendar API).
    E.g. "2026-03-26T10:00:00+08:00" -> "1774825200"
    """
    from datetime import datetime, timezone, timedelta
    import re

    # Parse timezone offset
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
        # Assume local time (Shanghai UTC+8)
        tz = timezone(timedelta(hours=8))
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=tz)

    return str(int(dt.timestamp()))
