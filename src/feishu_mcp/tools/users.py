"""
tools/users.py — User resolution utilities

Provides:
- get_chat_members: fetch group member list (open_id + display name)
- resolve_users_by_name: fuzzy match members by name within a group, return open_id list
"""

import logging
from typing import Any

import httpx

from feishu_mcp.auth import get_auth_headers

logger = logging.getLogger(__name__)
FEISHU_BASE_URL = "https://open.feishu.cn"


def _feishu_get(path: str, params: dict | None = None) -> dict:
    """GET request to Feishu API with automatic tenant token injection."""
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers(), params=params or {})
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def get_chat_members(chat_id: str) -> list[dict[str, str]]:
    """
    Fetch the member list of a Feishu group.

    Args:
        chat_id: Group ID (starts with oc_)

    Returns:
        list of {"name": str, "open_id": str, "user_id": str}
    """
    members: list[dict[str, str]] = []
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {"member_id_type": "open_id", "page_size": 100}
        if page_token:
            params["page_token"] = page_token

        data = _feishu_get(f"/open-apis/im/v1/chats/{chat_id}/members", params)
        items = data.get("data", {}).get("items", [])
        for item in items:
            members.append(
                {
                    "name": item.get("name", ""),
                    "open_id": item.get("member_id", ""),
                    "user_id": item.get("user_id", ""),
                }
            )

        has_more = data.get("data", {}).get("has_more", False)
        page_token = data.get("data", {}).get("page_token")
        if not has_more or not page_token:
            break

    logger.info("Fetched %d members from group %s", len(members), chat_id)
    return members


def resolve_users_by_name(chat_id: str, names: list[str]) -> dict[str, str | None]:
    """
    Fuzzy-match group members by display name; returns a {name: open_id} mapping.

    Matching strategy (tried in order):
    1. Exact match
    2. Substring match (query contains member name, or vice versa)
    3. If still not found, return None (caller decides whether to error or prompt user)

    Args:
        chat_id: Group ID
        names: List of names to resolve, e.g. ["Alice", "Bob"]

    Returns:
        dict mapping each original name to open_id or None (when not found)
    """
    members = get_chat_members(chat_id)
    result: dict[str, str | None] = {}

    for name in names:
        name_stripped = name.strip()
        matched: str | None = None

        # Strategy 1: exact match
        for m in members:
            if m["name"] == name_stripped:
                matched = m["open_id"]
                break

        # Strategy 2: substring match
        if not matched:
            candidates = [
                m for m in members
                if name_stripped in m["name"] or m["name"] in name_stripped
            ]
            if len(candidates) == 1:
                matched = candidates[0]["open_id"]
            elif len(candidates) > 1:
                # Multiple candidates; log a warning and use the first (could be improved later with an interactive card)
                logger.warning(
                    "Name '%s' matched multiple group members: %s, using the first",
                    name_stripped,
                    [c["name"] for c in candidates],
                )
                matched = candidates[0]["open_id"]

        if not matched:
            logger.warning("No member named '%s' found in group %s", name_stripped, chat_id)

        result[name_stripped] = matched

    return result
