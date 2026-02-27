"""
tools/__init__.py — Tool registry

All MCP tools are exported here; server.py imports directly from this module.
"""

from feishu_mcp.tools.users import (
    get_chat_members,
    resolve_users_by_name,
)
from feishu_mcp.tools.messages import (
    send_message,
    reply_message,
    send_card_message,
)
from feishu_mcp.tools.calendar import (
    get_or_create_group_calendar,
    create_calendar_event,
    add_event_attendees,
    list_calendar_events,
)
from feishu_mcp.tools.tasks import (
    create_task,
    assign_task,
    add_task_to_list,
    list_tasks,
)
from feishu_mcp.tools.documents import (
    create_folder,
    create_document,
    write_document_markdown,
    upload_file,
    upload_file_and_share,
    insert_file_block,
    set_doc_permission,
    set_doc_public_access,
    get_share_link,
    grant_permission_request,
)

__all__ = [
    # users
    "get_chat_members",
    "resolve_users_by_name",
    # messages
    "send_message",
    "reply_message",
    "send_card_message",
    # calendar
    "get_or_create_group_calendar",
    "create_calendar_event",
    "add_event_attendees",
    "list_calendar_events",
    # tasks
    "create_task",
    "assign_task",
    "add_task_to_list",
    "list_tasks",
    # cloud docs
    "create_folder",
    "create_document",
    "write_document_markdown",
    "upload_file",
    "upload_file_and_share",
    "insert_file_block",
    "set_doc_permission",
    "set_doc_public_access",
    "get_share_link",
    "grant_permission_request",
]
