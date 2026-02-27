"""
tools/messages.py — Messaging utilities

Provides:
- send_message: send text / rich-text / card messages to a group or user (supports @mentions)
- reply_message: reply to a specific message
- send_card_message: send an interactive card message
"""

import json
import logging

import httpx

from feishu_mcp.auth import get_auth_headers

logger = logging.getLogger(__name__)
FEISHU_BASE_URL = "https://open.feishu.cn"


def _post(path: str, payload: dict, use_user_token: bool = False) -> dict:
    url = f"{FEISHU_BASE_URL}{path}"
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, headers=get_auth_headers(use_user_token), json=payload)
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{path}]: code={data['code']}, msg={data.get('msg')}")
    return data


def send_message(
    receive_id_type: str,
    receive_id: str,
    content: str,
    msg_type: str = "text",
) -> dict:
    """
    Send a message to a group or user.

    Args:
        receive_id_type: "chat_id" | "open_id" | "user_id" | "union_id" | "email"
        receive_id: ID value corresponding to receive_id_type
        content: Message content as a JSON string.
            - text example: '{"text": "hello <at user_id=\\"ou_xxx\\">@Alice</at>"}'
            - post format: see Feishu rich-text docs
        msg_type: "text" | "post" | "interactive" | "image" etc., default "text"

    Returns:
        Feishu API response data including message_id
    """
    params = {"receive_id_type": receive_id_type}
    payload = {
        "receive_id": receive_id,
        "msg_type": msg_type,
        "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
    }
    url = f"{FEISHU_BASE_URL}/open-apis/im/v1/messages"
    with httpx.Client(timeout=15) as client:
        resp = client.post(
            url, headers=get_auth_headers(), params=params, json=payload
        )
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"send_message failed: code={data['code']}, msg={data.get('msg')}"
        )
    logger.info("Message sent successfully: message_id=%s", data["data"]["message_id"])
    return data["data"]


def reply_message(
    message_id: str,
    content: str,
    msg_type: str = "text",
) -> dict:
    """
    Reply to a specific message (posted under the original message thread).

    Args:
        message_id: ID of the message to reply to (starts with om_)
        content: Reply content as a JSON string
        msg_type: Message type, default "text"

    Returns:
        Feishu API response data including the new message_id
    """
    payload = {
        "msg_type": msg_type,
        "content": content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
    }
    data = _post(f"/open-apis/im/v1/messages/{message_id}/reply", payload)
    logger.info("Reply sent successfully: message_id=%s", data["data"]["message_id"])
    return data["data"]


def send_card_message(
    receive_id_type: str,
    receive_id: str,
    card: dict | str,
) -> dict:
    """
    Send a Feishu interactive card message.

    Args:
        receive_id_type: Receiver ID type
        receive_id: Group or user ID
        card: Card JSON as a dict or pre-serialized string

    Returns:
        Feishu API response data
    """
    content = json.dumps(card, ensure_ascii=False) if isinstance(card, dict) else card
    return send_message(receive_id_type, receive_id, content, msg_type="interactive")


def build_text_with_at(text: str, at_open_ids: list[str] | None = None) -> str:
    """
    Build a text message content string with @mention tags.

    Args:
        text: Main message text
        at_open_ids: List of open_ids to mention; pass ["all"] to mention everyone

    Returns:
        JSON string suitable for use as the content parameter of send_message
    """
    at_parts = ""
    if at_open_ids:
        at_parts = " ".join(f'<at id="{uid}"></at>' for uid in at_open_ids)
        at_parts = at_parts + " "
    return json.dumps({"text": at_parts + text}, ensure_ascii=False)
