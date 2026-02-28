"""
server.py — Feishu MCP Server entry point

Registers all tools and starts the MCP Server.

Startup (stdio mode, for OpenClaw / NanoBot integration):
  python -m feishu_mcp.server

Example OpenClaw configuration (mcp.json):
  {
    "feishu": {
      "command": "python",
      "args": ["-m", "feishu_mcp.server"],
      "cwd": "/path/to/feishu-miqroera-mcp",
      "env": { "PYTHONPATH": "src" }
    }
  }
"""

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Server("feishu-miqroera-mcp")


# ─────────────────────────────────────────
# Tool definitions (Tool Schema)
# ─────────────────────────────────────────

TOOLS: list[Tool] = [
    # ── Users ──
    Tool(
        name="get_chat_members",
        description="Get the member list of a Feishu group. Returns each member's name and open_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Group ID, starts with oc_"},
            },
            "required": ["chat_id"],
        },
    ),
    Tool(
        name="resolve_users_by_name",
        description="Fuzzy-match users by name within a group. Returns a {name: open_id} mapping. Use this when the user says 'assign a task to A' to find A's open_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Group ID"},
                "names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of names to resolve, e.g. [\"Alice\", \"Bob\"]",
                },
            },
            "required": ["chat_id", "names"],
        },
    ),
    # ── Messages ──
    Tool(
        name="send_message",
        description="Send a message to a Feishu group or user (supports text, rich text, and card).",
        inputSchema={
            "type": "object",
            "properties": {
                "receive_id_type": {
                    "type": "string",
                    "enum": ["chat_id", "open_id", "user_id", "email"],
                    "description": "Receiver ID type",
                },
                "receive_id": {"type": "string", "description": "Receiver ID"},
                "content": {
                    "type": "string",
                    "description": "Message content as a JSON string. Text example: '{\"text\": \"Hello\"}'",
                },
                "msg_type": {
                    "type": "string",
                    "enum": ["text", "post", "interactive"],
                    "description": "Message type; default is text",
                    "default": "text",
                },
            },
            "required": ["receive_id_type", "receive_id", "content"],
        },
    ),
    Tool(
        name="reply_message",
        description="Reply to a specific message in Feishu.",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of the message to reply to (starts with om_)"},
                "content": {"type": "string", "description": "Reply content (JSON string)"},
                "msg_type": {"type": "string", "default": "text"},
            },
            "required": ["message_id", "content"],
        },
    ),
    Tool(
        name="get_message",
        description="Get the full content and metadata of a single Feishu message. For file/image messages, the returned content JSON contains file_key and file_name which can be used with download_message_file.",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Message ID (starts with om_)"},
            },
            "required": ["message_id"],
        },
    ),
    Tool(
        name="get_chat_messages",
        description="List recent messages in a Feishu chat (group or P2P). Useful for finding file/image messages and their file_key. Returns messages sorted by time.",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Chat/group ID (starts with oc_)"},
                "start_time": {"type": "string", "description": "Start time filter (Unix timestamp in seconds), optional"},
                "end_time": {"type": "string", "description": "End time filter (Unix timestamp in seconds), optional"},
                "page_size": {"type": "integer", "description": "Number of messages to return (1-50, default 20)", "default": 20},
                "sort_type": {
                    "type": "string",
                    "enum": ["ByCreateTimeAsc", "ByCreateTimeDesc"],
                    "description": "Sort order, default descending (newest first)",
                    "default": "ByCreateTimeDesc",
                },
            },
            "required": ["chat_id"],
        },
    ),
    Tool(
        name="download_message_file",
        description="Download a file or image attachment from a Feishu chat message to local disk. Use get_message or get_chat_messages first to obtain the message_id and file_key. For file messages, content JSON has {\"file_key\": \"...\", \"file_name\": \"...\"}. Returns the local file path after download.",
        inputSchema={
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID of the message containing the file (starts with om_)"},
                "file_key": {"type": "string", "description": "File key from the message content JSON"},
                "file_type": {
                    "type": "string",
                    "enum": ["file", "image"],
                    "description": "Type of resource: 'file' for documents/PDFs, 'image' for images",
                    "default": "file",
                },
                "file_name": {"type": "string", "description": "Desired filename; if empty, auto-detected from response headers"},
            },
            "required": ["message_id", "file_key"],
        },
    ),
    # ── Calendar ──
    Tool(
        name="get_or_create_group_calendar",
        description="Get a group shared calendar. If the group does not have one yet, create it automatically. Returns calendar_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "chat_id": {"type": "string", "description": "Group ID"},
            },
            "required": ["chat_id"],
        },
    ),
    Tool(
        name="create_calendar_event",
        description="Create a calendar event in Feishu Calendar. Supports online meetings (video conference). After creation, call add_event_attendees to add participants.",
        inputSchema={
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string", "description": "Calendar ID"},
                "summary": {"type": "string", "description": "Event title"},
                "start_time": {
                    "type": "string",
                    "description": "Start time in RFC3339 format, e.g. '2026-03-26T10:00:00+08:00'",
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in RFC3339 format",
                },
                "description": {"type": "string", "description": "Event description", "default": ""},
                "is_online": {
                    "type": "boolean",
                    "description": "Whether to create an online video meeting; default false",
                    "default": False,
                },
            },
            "required": ["calendar_id", "summary", "start_time", "end_time"],
        },
    ),
    Tool(
        name="add_event_attendees",
        description="Add attendees to a Feishu calendar event. Attendees will receive a pop-up card notification asking whether to accept the invitation.",
        inputSchema={
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string"},
                "event_id": {"type": "string", "description": "Event ID"},
                "attendee_open_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee open_ids",
                },
            },
            "required": ["calendar_id", "event_id", "attendee_open_ids"],
        },
    ),
    Tool(
        name="list_calendar_events",
        description="List events in a Feishu calendar.",
        inputSchema={
            "type": "object",
            "properties": {
                "calendar_id": {"type": "string"},
                "start_time": {"type": "string", "description": "Filter start time (RFC3339), optional"},
                "end_time": {"type": "string", "description": "Filter end time (RFC3339), optional"},
            },
            "required": ["calendar_id"],
        },
    ),
    # ── Tasks ──
    Tool(
        name="create_task",
        description="Create a new task in Feishu Tasks. After creation, call assign_task to assign it to a member.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Task description", "default": ""},
                "start_time": {
                    "type": "string",
                    "description": "Start time in RFC3339 format, e.g. '2026-03-20T09:00:00+08:00'",
                },
                "due_time": {
                    "type": "string",
                    "description": "Due time in RFC3339 format",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="assign_task",
        description="Assign a Feishu task to one or more members (assignee role).",
        inputSchema={
            "type": "object",
            "properties": {
                "task_guid": {"type": "string", "description": "Task GUID (returned by create_task)"},
                "assignee_open_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of assignee open_ids",
                },
            },
            "required": ["task_guid", "assignee_open_ids"],
        },
    ),
    Tool(
        name="add_task_to_list",
        description="Add a task to a task list.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_guid": {"type": "string"},
                "tasklist_guid": {"type": "string", "description": "Tasklist GUID"},
            },
            "required": ["task_guid", "tasklist_guid"],
        },
    ),
    Tool(
        name="list_tasks",
        description="List Feishu tasks. Optionally filter by tasklist or assignee.",
        inputSchema={
            "type": "object",
            "properties": {
                "tasklist_guid": {"type": "string", "description": "Tasklist GUID (optional)"},
                "assignee_open_id": {"type": "string", "description": "Assignee open_id (optional)"},
                "completed": {
                    "type": "boolean",
                    "description": "true=completed, false=incomplete, omit=all",
                },
            },
        },
    ),
    # ── Cloud Documents ──
    Tool(
        name="create_document",
        description="Create a new document in Feishu Drive.",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "folder_token": {
                    "type": "string",
                    "description": "Target folder token; omit to place in the root folder",
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="write_document_markdown",
        description="Write Markdown content into a Feishu document. Supports headings, paragraphs, lists, links, code blocks, bold, and more.",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "description": "Document ID"},
                "markdown_content": {"type": "string", "description": "Content in Markdown format"},
            },
            "required": ["document_id", "markdown_content"],
        },
    ),
    Tool(
        name="upload_file",
        description="Upload a local file to Feishu Drive and return the file_token. Supports PDF, images, and any file type. Files ≤20 MB are uploaded directly; files >20 MB use multipart upload automatically.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the local file"},
                "file_name": {"type": "string", "description": "Display name in Drive; defaults to the local filename"},
                "parent_token": {"type": "string", "description": "Target folder token (optional)"},
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="upload_file_and_share",
        description="Upload a local file to Feishu Drive and return a shareable URL in one step (organization-wide link access). Ideal for Agents that need to download a file and send the link to a group without multiple steps.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute path to the local file"},
                "file_name": {"type": "string", "description": "Display name in Drive; defaults to the local filename"},
                "parent_token": {"type": "string", "description": "Target folder token (optional)"},
            },
            "required": ["file_path"],
        },
    ),
    Tool(
        name="insert_file_block",
        description="Insert a downloadable file block at the end of a Feishu document (for embedding PDF attachments etc.).",
        inputSchema={
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "file_token": {"type": "string", "description": "file_token returned by upload_file"},
                "file_name": {"type": "string", "description": "Display name of the file"},
            },
            "required": ["document_id", "file_token", "file_name"],
        },
    ),
    Tool(
        name="create_folder",
        description="Create a new folder in Feishu Drive. If folder_token is empty, the folder is created in the root directory.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Folder name (1–256 bytes)"},
                "folder_token": {
                    "type": "string",
                    "description": "Parent folder token; leave empty to create in the root directory",
                    "default": "",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="set_doc_permission",
        description="Batch-set member permissions (view/edit/full_access) for a Feishu document or file. Supports specifying users (open_id) or groups (chat_id). The bot must already be in the group when using chat_ids.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_token": {"type": "string", "description": "Document/file token"},
                "file_type": {
                    "type": "string",
                    "enum": ["doc", "docx", "file", "bitable", "sheet"],
                    "description": "File type",
                },
                "member_open_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of user open_ids (can be combined with chat_ids)",
                    "default": [],
                },
                "chat_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of group chat_ids (starting with oc_); bot must already be in the group",
                    "default": [],
                },
                "perm_type": {
                    "type": "string",
                    "enum": ["view", "edit", "full_access"],
                    "description": "Permission type",
                    "default": "view",
                },
            },
            "required": ["file_token", "file_type"],
        },
    ),
    Tool(
        name="set_doc_public_access",
        description="Set the external link access level of a Feishu document (view/edit for organization members or the public internet).",
        inputSchema={
            "type": "object",
            "properties": {
                "file_token": {"type": "string"},
                "file_type": {"type": "string"},
                "access_level": {
                    "type": "string",
                    "enum": ["off", "tenant_readable", "tenant_editable", "anyone_readable", "anyone_editable"],
                    "description": "Access level",
                    "default": "tenant_readable",
                },
            },
            "required": ["file_token", "file_type"],
        },
    ),
    Tool(
        name="get_share_link",
        description="Get the share link of a Feishu document.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_token": {"type": "string"},
                "file_type": {"type": "string"},
            },
            "required": ["file_token", "file_type"],
        },
    ),
    Tool(
        name="grant_permission_request",
        description="Handle a cloud document permission request: grant the specified user view access. Typically used in Webhook processing.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_token": {"type": "string"},
                "file_type": {"type": "string"},
                "user_open_id": {"type": "string", "description": "open_id of the requester"},
                "perm_type": {"type": "string", "default": "view"},
            },
            "required": ["file_token", "file_type", "user_open_id"],
        },
    ),
]


# ─────────────────────────────────────────
# MCP handlers
# ─────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Unified tool call entry point; routes to the corresponding function by tool name."""
    try:
        result = await _dispatch(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as e:
        logger.error("Tool %s execution failed: %s", name, e, exc_info=True)
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def _dispatch(name: str, args: dict) -> Any:
    """Dispatch table: tool name → function call."""
    from feishu_mcp.tools import users, messages, calendar, tasks, documents

    dispatch_map = {
        # Users
        "get_chat_members": lambda: users.get_chat_members(args["chat_id"]),
        "resolve_users_by_name": lambda: users.resolve_users_by_name(args["chat_id"], args["names"]),
        # Messages
        "send_message": lambda: messages.send_message(
            args["receive_id_type"], args["receive_id"],
            args["content"], args.get("msg_type", "text"),
        ),
        "reply_message": lambda: messages.reply_message(
            args["message_id"], args["content"], args.get("msg_type", "text"),
        ),
        "get_message": lambda: messages.get_message(args["message_id"]),
        "get_chat_messages": lambda: messages.get_chat_messages(
            args["chat_id"],
            args.get("start_time", ""),
            args.get("end_time", ""),
            args.get("page_size", 20),
            args.get("sort_type", "ByCreateTimeDesc"),
        ),
        "download_message_file": lambda: messages.download_message_file(
            args["message_id"], args["file_key"],
            args.get("file_type", "file"),
            args.get("file_name", ""),
        ),
        "send_card_message": lambda: messages.send_card_message(
            args["receive_id_type"], args["receive_id"], args["card"],
        ),
        # Calendar
        "get_or_create_group_calendar": lambda: calendar.get_or_create_group_calendar(args["chat_id"]),
        "create_calendar_event": lambda: calendar.create_calendar_event(
            args["calendar_id"], args["summary"],
            args["start_time"], args["end_time"],
            args.get("description", ""), args.get("is_online", False),
        ),
        "add_event_attendees": lambda: calendar.add_event_attendees(
            args["calendar_id"], args["event_id"], args["attendee_open_ids"],
        ),
        "list_calendar_events": lambda: calendar.list_calendar_events(
            args["calendar_id"], args.get("start_time"), args.get("end_time"),
        ),
        # Tasks
        "create_task": lambda: tasks.create_task(
            args["title"], args.get("description", ""),
            args.get("start_time"), args.get("due_time"),
        ),
        "assign_task": lambda: tasks.assign_task(args["task_guid"], args["assignee_open_ids"]),
        "add_task_to_list": lambda: tasks.add_task_to_list(args["task_guid"], args["tasklist_guid"]),
        "list_tasks": lambda: tasks.list_tasks(
            args.get("tasklist_guid"), args.get("assignee_open_id"), args.get("completed"),
        ),
        # Cloud Documents
        "create_folder": lambda: documents.create_folder(
            args["name"], args.get("folder_token", ""),
        ),
        "create_document": lambda: documents.create_document(
            args["title"], args.get("folder_token"),
        ),
        "write_document_markdown": lambda: documents.write_document_markdown(
            args["document_id"], args["markdown_content"],
        ),
        "upload_file": lambda: documents.upload_file(
            args["file_path"], args.get("file_name"), args.get("parent_token"),
        ),
        "upload_file_and_share": lambda: documents.upload_file_and_share(
            args["file_path"], args.get("file_name"), args.get("parent_token"),
        ),
        "insert_file_block": lambda: documents.insert_file_block(
            args["document_id"], args["file_token"], args["file_name"],
        ),
        "set_doc_permission": lambda: documents.set_doc_permission(
            args["file_token"], args["file_type"],
            args.get("member_open_ids"), args.get("chat_ids"),
            args.get("perm_type", "view"),
        ),
        "set_doc_public_access": lambda: documents.set_doc_public_access(
            args["file_token"], args["file_type"], args.get("access_level", "tenant_readable"),
        ),
        "get_share_link": lambda: documents.get_share_link(args["file_token"], args["file_type"]),
        "grant_permission_request": lambda: documents.grant_permission_request(
            args["file_token"], args["file_type"],
            args["user_open_id"], args.get("perm_type", "view"),
        ),
    }

    if name not in dispatch_map:
        raise ValueError(f"Unknown tool: {name}")

    return dispatch_map[name]()


# ─────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────

def main():
    import asyncio
    logger.info("Feishu MCP Server starting (stdio mode)...")
    asyncio.run(_run())


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
