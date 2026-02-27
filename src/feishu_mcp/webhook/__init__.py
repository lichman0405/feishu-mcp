"""webhook package"""

import hashlib
import hmac
import json
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

load_dotenv()
logger = logging.getLogger(__name__)

app = FastAPI(title="Feishu Webhook Event Receiver")

VERIFICATION_TOKEN = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
ENCRYPT_KEY = os.getenv("FEISHU_ENCRYPT_KEY", "")


# ─────────────────────────────────────────
# Signature verification
# ─────────────────────────────────────────

def _verify_signature(timestamp: str, nonce: str, encrypt_key: str, body: bytes, signature: str) -> bool:
    """Verify the Feishu event signature (using HMAC-SHA256)."""
    if not encrypt_key:
        return True  # Skip verification when encrypt_key is not set (dev environment only)
    raw = (timestamp + nonce + encrypt_key + body.decode("utf-8")).encode("utf-8")
    expected = hashlib.sha256(raw).hexdigest()
    return hmac.compare_digest(expected, signature)


# ─────────────────────────────────────────
# Main route: Feishu event callback
# ─────────────────────────────────────────

@app.post("/webhook/feishu")
async def receive_event(request: Request):
    """Unified entry point for Feishu event pushes."""
    body = await request.body()
    timestamp = request.headers.get("X-Lark-Request-Timestamp", "")
    nonce = request.headers.get("X-Lark-Request-Nonce", "")
    signature = request.headers.get("X-Lark-Signature", "")

    # Signature verification
    if not _verify_signature(timestamp, nonce, ENCRYPT_KEY, body, signature):
        logger.warning("Signature verification failed, rejecting request")
        return Response(status_code=401, content="Unauthorized")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return Response(status_code=400, content="Invalid JSON")

    # Feishu URL Challenge verification (when setting up the callback URL for the first time)
    if "challenge" in payload:
        logger.info("Received Challenge verification request, responding...")
        return {"challenge": payload["challenge"]}

    event_type = (
        payload.get("header", {}).get("event_type")
        or payload.get("event", {}).get("type")
        or "unknown"
    )
    logger.info("Received Feishu event: type=%s", event_type)

    # ─── Event routing ───
    if event_type == "im.message.receive_v1":
        await _handle_message_receive(payload)
    elif "drive.file.permission" in event_type:
        await _handle_drive_permission(payload)
    else:
        logger.debug("Unhandled event type: %s", event_type)

    return {"code": 0}


# ─────────────────────────────────────────
# Event handlers
# ─────────────────────────────────────────

async def _handle_message_receive(payload: dict):
    """
    Handle @bot message events.

    Feishu pushed message structure (v2 schema):
    payload.event.message.content → JSON string containing message text
    payload.event.sender.sender_id.open_id → sender open_id
    payload.event.message.chat_id → group ID
    payload.event.message.message_id → message ID (used for replies)
    """
    event = payload.get("event", {})
    message = event.get("message", {})
    sender = event.get("sender", {}).get("sender_id", {})

    chat_id = message.get("chat_id", "")
    message_id = message.get("message_id", "")
    sender_open_id = sender.get("open_id", "")

    # Parse message text
    try:
        content = json.loads(message.get("content", "{}"))
        text = content.get("text", "").strip()
    except Exception:
        text = ""

    logger.info(
        "Received message | chat_id=%s | sender=%s | text=%s",
        chat_id, sender_open_id, text[:50]
    )

    # TODO: pass (chat_id, message_id, sender_open_id, text) to the Agent for processing
    # For now just log; later connect to Agent message queue or trigger tool calls directly
    # Example: await agent_router.process(chat_id, message_id, sender_open_id, text)


async def _handle_drive_permission(payload: dict):
    """
    Handle cloud document permission request event.
    Auto-grant read-only access to the requester and send a notification message.
    """
    event = payload.get("event", {})
    file_token = event.get("file_token", "")
    file_type = event.get("file_type", "docx")
    operator = event.get("operator", {})
    user_open_id = operator.get("open_id", "")

    if not file_token or not user_open_id:
        logger.warning("drive permission event missing fields: %s", payload)
        return

    logger.info("Processing permission request: file=%s, user=%s", file_token, user_open_id)

    try:
        from feishu_mcp.tools.documents import grant_permission_request
        from feishu_mcp.tools.messages import send_message, build_text_with_at

        grant_permission_request(file_token, file_type, user_open_id, "view")

        # Send a private DM notification to the requester
        send_message(
            "open_id",
            user_open_id,
            build_text_with_at("You have been granted view access to the document. Click the link to visit."),
        )
        logger.info("Permission granted and notification sent to user %s", user_open_id)
    except Exception as e:
        logger.error("Failed to process permission request: %s", e)


# ─────────────────────────────────────────
# Health check
# ─────────────────────────────────────────
