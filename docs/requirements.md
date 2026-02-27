# Feishu MCP Server — Requirements Document

> Project: `feishu-miqroera-mcp`
> Version: v0.1
> Date: 2026-02-27

---

## 1. Background

Enable AI Agents (e.g. OpenClaw, NanoBot, or any MCP-compatible agent) to invoke Feishu capabilities directly inside group chats, covering four business modules: **messaging, calendar, tasks, and cloud documents** — enabling "natural-language-driven Feishu workflows inside a group."

The existing official Feishu MCP tools are minimal; this project fills in the missing high-value tools.

---

## 2. Technology Choices

| Item | Choice | Reason |
|------|--------|--------|
| Language | **Python 3.11+** | Team-familiar; official MCP Python SDK is complete; lark-oapi SDK is mature |
| MCP SDK | `mcp[cli]` (official Python SDK) | Maintained by Anthropic; supports stdio / SSE |
| Feishu SDK | `lark-oapi` | Official Feishu Python SDK; covers all APIs; auto-refreshes tokens |
| Virtual env | `.venv` (python -m venv) | Local dependency isolation |
| Transport | stdio (local) / SSE (server deployment) | stdio for OpenClaw/NanoBot local integration; SSE for remote deployment |
| Package manager | `uv` or `pip` + `requirements.txt` | Simple and maintainable |

---

## 3. Feishu App Configuration

### 3.1 App Type
- **Enterprise self-built app** (not a marketplace app)
- Bot capability must be enabled

### 3.2 Required Permissions (Scopes)

| Module | Permissions |
|--------|-------------|
| Messaging | `im:message`, `im:message:send_as_bot`, `im:chat`, `im:chat.members:read` |
| Directory | `contact:user.base:readonly`, `contact:user.id:readonly` |
| Calendar | `calendar:calendar`, `calendar:calendar:readonly` |
| Tasks | `task:task`, `task:task:write` |
| Cloud docs | `docs:doc`, `docs:doc:readonly`, `drive:drive`, `drive:file`, `bitable:app` |
| Drive permissions | `drive:permission` |

### 3.3 Token Strategy

> Warning: Key note (common source of errors)

| Operation | Required Token Type | Reason |
|-----------|-------------------|--------|
| Send messages, create documents, upload files | `tenant_access_token` | Operates as the app identity |
| Create events as organizer | `user_access_token` | Event organizer cannot be a Bot; otherwise error 193101 |
| Add event attendees (triggers invite popup) | `user_access_token` or `tenant_access_token` | Both work; tenant recommended |
| Create and assign tasks | `user_access_token` (recommended) or `tenant_access_token` | Both supported by v2 API |
| Set document permissions | `tenant_access_token` | App identity is sufficient for permission management |

---

## 4. Core User Stories

### Story 1: Create a calendar event and invite attendees in a group

**Trigger:** A user @mentions the bot in a group with a natural-language meeting request.

**Example input:**
> @bot Please schedule a 1-hour online meeting for me, A, B, and C on March 26 at 10 AM on the topic "Customer Feedback Integration Meeting"

**Bot execution chain:**

```
1. Parse intent: attendee list [me, A, B, C], time, duration 1h, topic, online meeting
2. resolve_users_by_name: group member names -> open_id list
3. get_group_calendar: get group shared calendar ID (create if not found)
4. create_calendar_event:
   - summary = "Customer Feedback Integration Meeting"
   - start_time = "2026-03-26T10:00:00+08:00"
   - end_time   = "2026-03-26T11:00:00+08:00"
   - vchat = { vc_type: "vc" }  <- online meeting
5. add_event_attendees: add all attendees
   -> attendees automatically receive a Feishu "Accept / Decline" invite popup
6. send_group_message: @mention requester, notify that event is created, attach link
```

**Expected outcome:**
- Event appears on the group shared calendar
- All attendees' personal calendars sync the event
- All attendees receive an "Accept / Decline" invite popup

---

### Story 2: Assign a task to a specific group member

**Trigger:** A user @mentions the bot in a group with a natural-language task assignment.

**Example input:**
> @bot Assign a task "Review colleague's work report" to A, starting March 20 at 9 AM, due March 22 at 5 PM

**Bot execution chain:**

```
1. Parse intent: assignee=A, task title, start time, due time
2. resolve_users_by_name: A -> open_id
3. create_task:
   - title = "Review colleague's work report"
   - start = "2026-03-20T09:00:00+08:00"
   - due   = "2026-03-22T17:00:00+08:00"
4. add_task_members: role=assignee, add A's open_id
5. send_group_message: @mention requester and A, notify task is created, attach task link
```

---

### Story 3: Research report with cloud document, attachment, and permissions

**Trigger:** A user @mentions the bot in a group requesting a research report.

**Example input:**
> @bot Research "2026 LLM inference optimization techniques", generate a report with conclusions, references (with links), and key paper PDFs; store it in the group cloud space and make it accessible to all group members

**Bot execution chain:**

```
1. Parse intent: research topic, report structure, permission scope=group members
2. Agent conducts research (external knowledge / web search)
3. create_document: create document in group Drive, title=report name
4. write_document_content: write Markdown content (conclusions, sections, references with links)
5. upload_files: upload PDFs to Drive, get file_token
6. insert_file_block: insert PDF as downloadable file block in the document
7. set_permissions: grant group members collaborator access
8. get_share_link: generate shareable URL
9. send_group_message: @mention requester, attach report link

Permission request handling (event-driven, requires Webhook):
10. Listen for drive.file.edit permission request event
11. Agent decides -> grant_permission: grant read-only access to requester
12. Notify requester that access has been granted
```

---

## 5. MCP Tools List (Complete)

### 5.1 General / User Resolution

| Tool Name | Description | Input Parameters |
|-----------|-------------|-----------------|
| `get_chat_members` | Get group member list (with open_id, name) | `chat_id` |
| `resolve_users_by_name` | Fuzzy-match users by name within the group, return open_id | `chat_id`, `names: list[str]` |

### 5.2 Messaging

| Tool Name | Description | Input Parameters |
|-----------|-------------|-----------------|
| `send_message` | Send a message to a group or user (text/card/rich text) | `receive_id_type`, `receive_id`, `msg_type`, `content` |
| `reply_message` | Reply to a specific message | `message_id`, `content`, `msg_type` |

### 5.3 Calendar

| Tool Name | Description | Input Parameters |
|-----------|-------------|-----------------|
| `get_or_create_group_calendar` | Get group shared calendar, create if not found | `chat_id` |
| `create_calendar_event` | Create an event (supports online meeting) | `calendar_id`, `summary`, `start_time`, `end_time`, `description?`, `is_online?` |
| `add_event_attendees` | Add attendees to an event (triggers invite popup) | `calendar_id`, `event_id`, `attendee_ids: list[str]` |
| `list_calendar_events` | List events in a calendar | `calendar_id`, `start_time?`, `end_time?` |

### 5.4 Tasks

| Tool Name | Description | Input Parameters |
|-----------|-------------|-----------------|
| `create_task` | Create a task | `title`, `description?`, `start_time?`, `due_time?` |
| `assign_task` | Assign task to member(s) | `task_guid`, `assignee_ids: list[str]` |
| `add_task_to_list` | Link task to a tasklist | `task_guid`, `tasklist_guid` |
| `list_tasks` | List tasks | `tasklist_guid?`, `assignee_id?` |

### 5.5 Cloud Documents

| Tool Name | Description | Input Parameters |
|-----------|-------------|-----------------|
| `create_document` | Create a document in Drive | `title`, `folder_token?` |
| `write_document_markdown` | Write Markdown content into a document | `document_id`, `markdown_content` |
| `upload_file` | Upload a file to Drive | `file_path`, `file_name`, `parent_token?` |
| `insert_file_block` | Insert a downloadable file block into a document | `document_id`, `file_token`, `file_name` |
| `set_doc_permission` | Set member permissions on a document/file | `file_token`, `file_type`, `member_ids: list[str]`, `perm_type` |
| `set_doc_public_access` | Set external link access permission | `file_token`, `file_type`, `access_level` |
| `get_share_link` | Generate a document sharing link | `file_token`, `file_type` |
| `grant_permission_request` | Handle permission request, grant access to requester | `file_token`, `file_type`, `user_id`, `perm_type` |

---

## 6. Event Subscriptions (Webhook)

The MCP Server needs an HTTP endpoint to receive Feishu push events:

| Event | Purpose |
|-------|---------|
| `im.message.receive_v1` | Receive @bot messages, trigger Agent flow |
| `drive.file.permission_member_added_v1` | Monitor cloud document permission requests |
| `calendar.calendar_event.changed_v4` | Optional: event change notifications |

> **Local development tip**: Use [ngrok](https://ngrok.com) or [Cloudflare Tunnel](https://www.cloudflare.com/products/tunnel/) to expose your local port to the internet for Feishu Webhook callbacks.

---

## 7. Environment Variables

```env
# Feishu app credentials
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional: for scenarios requiring user_access_token (calendar event organizer)
FEISHU_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxx

# Webhook server port
WEBHOOK_PORT=8080

# MCP Server transport mode: stdio or sse
MCP_TRANSPORT=stdio
```