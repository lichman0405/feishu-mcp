"""
webhook/longconn.py — Feishu Long-Connection Event Listener

Uses lark-oapi WebSocket long connection; no public IP or ngrok required.
The connection is initiated from your machine to Feishu servers.
In the Feishu developer console, choose "Long Connection" mode.

Startup:
  python -m feishu_mcp.webhook.longconn

Or import as a module:
  from feishu_mcp.webhook.longconn import start_listener

Console configuration (one-time setup):
  Feishu Open Platform → Events & Callbacks → Event Config
  → Select "Receive events via long connection (recommended)"
  → Save (no URL or Challenge verification required)
  → Under "Subscribed Events" add im.message.receive_v1
  → Publish version
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_credentials() -> tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise RuntimeError("Please set FEISHU_APP_ID and FEISHU_APP_SECRET in .env")
    return app_id, app_secret


# ─────────────────────────────────────────
# Event handler functions
# ─────────────────────────────────────────

def handle_message_receive(data) -> None:
    """
    Handle im.message.receive_v1 event (bot received a group/private message).

    data.event.message.content → JSON string containing message text
    data.event.sender.sender_id.open_id → sender open_id
    data.event.message.chat_id → group ID
    data.event.message.message_id → message ID (used for replies)
    """
    try:
        import lark_oapi as lark

        # lark-oapi deserializes event data into an object; raw dict is also accessible
        raw = lark.JSON.marshal(data)
        payload = json.loads(raw)
        event = payload.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {}).get("sender_id", {})

        chat_id = message.get("chat_id", "")
        message_id = message.get("message_id", "")
        sender_open_id = sender.get("open_id", "")
        msg_type = message.get("message_type", "text")

        try:
            content = json.loads(message.get("content", "{}"))
            text = content.get("text", "").strip()
        except Exception:
            text = ""

        logger.info(
            "[message event] chat_id=%s | sender=%s | type=%s | text=%s",
            chat_id, sender_open_id, msg_type, text[:80],
        )
        print(
            f"[received message] chat={chat_id} | from={sender_open_id}\n"
            f"  content: {text or '[non-text message]'}",
            flush=True,
        )

        # TODO: plug in Agent processing logic here
        # Example: auto-reply
        # from feishu_mcp.tools.messages import reply_message
        # reply_message(message_id, json.dumps({"text": "Received!"}), "text")

    except Exception as e:
        logger.error("handle_message_receive error: %s", e, exc_info=True)


def handle_task_updated(data) -> None:
    """
    Handle task.task.updated_v1 event (task status/content changed).
    Currently only logs; business logic can be extended here.
    """
    try:
        import lark_oapi as lark
        raw = lark.JSON.marshal(data)
        payload = json.loads(raw)
        event = payload.get("event", {})
        task_guid = event.get("task_guid", "")
        logger.info("[task updated event] task_guid=%s", task_guid)
    except Exception as e:
        logger.error("handle_task_updated error: %s", e, exc_info=True)


def handle_drive_permission(data) -> None:
    """Handle cloud document permission request event: auto-grant access and notify the requester."""
    try:
        import lark_oapi as lark

        raw = lark.JSON.marshal(data)
        payload = json.loads(raw)
        event = payload.get("event", {})
        file_token = event.get("file_token", "")
        file_type = event.get("file_type", "docx")
        user_open_id = event.get("operator", {}).get("open_id", "")

        if not file_token or not user_open_id:
            return

        logger.info("[permission request] file=%s user=%s", file_token, user_open_id)

        from feishu_mcp.tools.documents import grant_permission_request
        from feishu_mcp.tools.messages import send_message, build_text_with_at

        grant_permission_request(file_token, file_type, user_open_id, "view")
        send_message(
            "open_id",
            user_open_id,
            build_text_with_at("You have been granted view access to the document. Click the link to visit."),
        )
        logger.info("View permission granted to user %s", user_open_id)

    except Exception as e:
        logger.error("handle_drive_permission error: %s", e, exc_info=True)


# ─────────────────────────────────────────
# Long-connection client
# ─────────────────────────────────────────

def build_event_handler():
    """Build the lark-oapi event dispatcher and register all event handler functions."""
    import lark_oapi as lark

    handler = (
        lark.EventDispatcherHandler.builder("", "")
        # Message event
        .register_p2_im_message_receive_v1(handle_message_receive)
        # Task events (register to suppress 'processor not found' warnings)
        .register_p2_task_task_updated_v1(handle_task_updated)
        .register_p2_task_task_comment_updated_v1(handle_task_updated)
        .register_p2_task_task_update_tenant_v1(handle_task_updated)
        .build()
    )
    return handler


def start_listener(block: bool = True) -> None:
    """
    Start the Feishu long-connection event listener.

    Args:
        block: Whether to block the current thread (True = foreground, False = background thread)
    """
    import lark_oapi as lark

    app_id, app_secret = _get_credentials()
    handler = build_event_handler()

    client = lark.ws.Client(
        app_id,
        app_secret,
        event_handler=handler,
        log_level=lark.LogLevel.INFO,
    )

    logger.info("Starting Feishu long-connection listener app_id=%s", app_id)
    print(f"[long-connection] Connecting to Feishu server (app={app_id[:12]}...), press Ctrl+C to exit", flush=True)

    if block:
        client.start()  # blocking
    else:
        import threading
        t = threading.Thread(target=client.start, daemon=True)
        t.start()
        return t


# ─────────────────────────────────────────
# Direct run entry point
# ─────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        start_listener(block=True)
    except KeyboardInterrupt:
        print("\n[long-connection] stopped", flush=True)
        sys.exit(0)
