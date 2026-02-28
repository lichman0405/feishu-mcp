"""
tools/messages.py — Messaging utilities

Provides:
- send_message: send text / rich-text / card messages to a group or user (supports @mentions)
- reply_message: reply to a specific message
- send_card_message: send an interactive card message
- get_message: retrieve a single message's content and metadata
- get_chat_messages: list recent messages in a chat
- download_message_file: download a file/image attachment from a message to local disk
"""

import json
import logging
import os
import tempfile
from pathlib import Path

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


# ─────────────────────────────────────────
# Message reading & file download
# ─────────────────────────────────────────

def get_message(message_id: str) -> dict:
    """
    Retrieve a single message's full content and metadata.

    Args:
        message_id: Message ID (starts with om_)

    Returns:
        dict containing message_id, msg_type, content (JSON string),
        sender, chat_id, etc. For file messages, content contains file_key and file_name.
    """
    url = f"{FEISHU_BASE_URL}/open-apis/im/v1/messages/{message_id}"
    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers())
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"get_message failed: code={data['code']}, msg={data.get('msg')}"
        )
    items = data.get("data", {}).get("items", [])
    if not items:
        raise RuntimeError(f"Message not found: {message_id}")
    msg = items[0]
    logger.info("Retrieved message: message_id=%s, type=%s", message_id, msg.get("msg_type"))
    return msg


def get_chat_messages(
    chat_id: str,
    start_time: str = "",
    end_time: str = "",
    page_size: int = 20,
    sort_type: str = "ByCreateTimeDesc",
) -> list[dict]:
    """
    List recent messages in a chat (group or P2P).

    Args:
        chat_id: Chat/group ID (starts with oc_)
        start_time: Start time filter (Unix timestamp in seconds), optional
        end_time: End time filter (Unix timestamp in seconds), optional
        page_size: Number of messages to return (1-50, default 20)
        sort_type: "ByCreateTimeAsc" or "ByCreateTimeDesc" (default desc)

    Returns:
        List of message dicts, each containing message_id, msg_type, content, sender, etc.
    """
    url = f"{FEISHU_BASE_URL}/open-apis/im/v1/messages"
    params: dict = {
        "container_id_type": "chat",
        "container_id": chat_id,
        "page_size": str(min(page_size, 50)),
        "sort_type": sort_type,
    }
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time

    with httpx.Client(timeout=15) as client:
        resp = client.get(url, headers=get_auth_headers(), params=params)
        resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"get_chat_messages failed: code={data['code']}, msg={data.get('msg')}"
        )
    items = data.get("data", {}).get("items", [])
    logger.info("Retrieved %d messages from chat %s", len(items), chat_id)
    return items


def download_message_file(
    message_id: str,
    file_key: str,
    file_type: str = "file",
    file_name: str = "",
) -> dict:
    """
    Download a file or image attachment from a Feishu chat message to local disk.

    When a user uploads a file (PDF, image, etc.) in a Feishu group, this tool
    downloads it using the message_id and file_key. Use get_message or
    get_chat_messages first to obtain the file_key from the message content.

    Args:
        message_id: ID of the message that contains the file (starts with om_)
        file_key: File key from the message content JSON
        file_type: "file" for documents/PDFs, "image" for images
        file_name: Desired filename for the download; if empty, derived from file_key

    Returns:
        dict: {
            "file_path": "/tmp/feishu_downloads/xxx.pdf",  # local path to the downloaded file
            "file_name": "science.pdf",
            "size": 1003520,
        }
    """
    url = f"{FEISHU_BASE_URL}/open-apis/im/v1/messages/{message_id}/resources/{file_key}"
    params = {"type": file_type}

    with httpx.Client(timeout=120, follow_redirects=True) as client:
        resp = client.get(url, headers=get_auth_headers(), params=params)
        resp.raise_for_status()

    # Determine filename
    if not file_name:
        # Try Content-Disposition header
        cd = resp.headers.get("Content-Disposition", "")
        if "filename=" in cd:
            file_name = cd.split("filename=")[-1].strip('" ')
        else:
            ext = ".bin"
            ct = resp.headers.get("Content-Type", "")
            if "pdf" in ct:
                ext = ".pdf"
            elif "image/png" in ct:
                ext = ".png"
            elif "image/jpeg" in ct or "image/jpg" in ct:
                ext = ".jpg"
            elif "word" in ct or "docx" in ct:
                ext = ".docx"
            elif "excel" in ct or "xlsx" in ct:
                ext = ".xlsx"
            file_name = f"{file_key}{ext}"

    # Save to a persistent temp directory
    download_dir = os.path.join(tempfile.gettempdir(), "feishu_downloads")
    os.makedirs(download_dir, exist_ok=True)
    file_path = os.path.join(download_dir, file_name)

    with open(file_path, "wb") as f:
        f.write(resp.content)

    size = len(resp.content)
    logger.info(
        "Downloaded message file: message_id=%s, file_key=%s → %s (%d bytes)",
        message_id, file_key, file_path, size,
    )
    return {
        "file_path": file_path,
        "file_name": file_name,
        "size": size,
    }
