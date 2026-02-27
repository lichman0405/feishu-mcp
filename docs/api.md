# API Reference

> Complete reference for all 22 tools in feishu-miqroera-mcp

---

## Table of Contents

- [User Tools](#user-tools)
  - [get_chat_members](#get_chat_members)
  - [resolve_users_by_name](#resolve_users_by_name)
- [Message Tools](#message-tools)
  - [send_message](#send_message)
  - [reply_message](#reply_message)
- [Calendar Tools](#calendar-tools)
  - [get_or_create_group_calendar](#get_or_create_group_calendar)
  - [create_calendar_event](#create_calendar_event)
  - [add_event_attendees](#add_event_attendees)
  - [list_calendar_events](#list_calendar_events)
- [Task Tools](#task-tools)
  - [create_task](#create_task)
  - [assign_task](#assign_task)
  - [add_task_to_list](#add_task_to_list)
  - [list_tasks](#list_tasks)
- [Drive & Document Tools](#drive--document-tools)
  - [create_folder](#create_folder)
  - [create_document](#create_document)
  - [write_document_markdown](#write_document_markdown)
  - [upload_file](#upload_file)
  - [upload_file_and_share](#upload_file_and_share)
  - [insert_file_block](#insert_file_block)
  - [set_doc_permission](#set_doc_permission)
  - [set_doc_public_access](#set_doc_public_access)
  - [get_share_link](#get_share_link)
  - [grant_permission_request](#grant_permission_request)
- [Permission Management](#permission-management)

---

## Message Tools

### `send_message`

Send a message to a Feishu group or user.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `receive_id` | string | ✅ | Receiver ID (chat_id or open_id) |
| `receive_id_type` | string | ✅ | ID type: `chat_id` \| `open_id` \| `user_id` |
| `content` | string | ✅ | Message content (plain text or JSON rich text) |
| `msg_type` | string | ❌ | Message type, default `text`. Options: `text` \| `post` \| `interactive` |

**Returns**

```json
{
  "message_id": "om_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "chat_id": "oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Example (AI Agent call)**

```
Send a message to group oc_xxx: "Meeting at 3 PM today, please attend on time"
```

---

### `reply_message`

Reply to an existing message (preserves the message thread).

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|--------------|
| `message_id` | string | ✅ | ID of the message to reply to |
| `content` | string | ✅ | Reply content |
| `msg_type` | string | ❌ | Message type, default `text` |

**Returns**

```json
{
  "message_id": "om_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

---

## User Tools

### `get_chat_members`

Get all member information for the specified group.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | string | ✅ | Group ID (starts with `oc_`) |

**Returns**

```json
[
  {
    "name": "Zhang San",
    "open_id": "ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "user_id": "xxxxxxx"
  }
]
```

---

### `resolve_users_by_name`

Fuzzy-match users by name within the specified group (useful for @mentions or confirming open_id before assigning tasks).

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | string | ✅ | Group ID |
| `names` | array[string] | ✅ | List of names to look up, e.g. `["Zhang San", "Li Si"]` |

**Returns**

```json
{
  "Zhang San": "ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "Li Si": "ou_yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
}
```

---

## Task Tools

### `create_task`

Create a new task in Feishu Tasks (Task v2).

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | ✅ | Task title |
| `description` | string | ❌ | Task description (Markdown) |
| `start_time` | string | ❌ | Start time (RFC3339 format, e.g. `2026-02-01T09:00:00+08:00`) |
| `due_time` | string | ❌ | Due time (RFC3339 format) |

**Returns**

```json
{
  "task_guid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "url": "https://applink.feishu.cn/client/todo/detail?guid=xxx"
}
```

---

### `assign_task`

Assign an owner to an existing task.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_guid` | string | ✅ | Task GUID (returned by `create_task`) |
| `assignee_open_ids` | array[string] | ✅ | List of assignee open_ids |

---

### `add_task_to_list`

Add a task to the specified tasklist.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_guid` | string | ✅ | Task GUID |
| `tasklist_guid` | string | ✅ | Tasklist GUID |

---

### `list_tasks`

Query the task list; supports filtering by tasklist, assignee, and completion status.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tasklist_guid` | string | ❌ | Filter by tasklist |
| `assignee_open_id` | string | ❌ | Filter by assignee |
| `completed` | boolean | ❌ | `true` returns only completed tasks; `false` returns only incomplete tasks |

---

## Calendar Tools

### `get_or_create_group_calendar`

Get the shared calendar for a group, creating it automatically if it does not exist. Useful for establishing a dedicated calendar for a Feishu group.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chat_id` | string | ✅ | Group ID |
| `calendar_name` | string | ❌ | Calendar name; defaults to the group name |

**Returns**

```json
{
  "calendar_id": "feishu.cn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "created": true
}
```

---

### `create_calendar_event`

Create a calendar event in the specified calendar.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendar_id` | string | ✅ | Calendar ID |
| `summary` | string | ✅ | Event title |
| `start_time` | string | ✅ | Start time in RFC3339 format, e.g. `2026-02-01T14:00:00+08:00` |
| `end_time` | string | ✅ | End time (same format) |
| `description` | string | ❌ | Event description |
| `location` | string | ❌ | Location |

**Returns**

```json
{
  "event_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "url": "https://applink.feishu.cn/client/calendar/event?calendarId=xxx&eventId=xxx"
}
```

---

### `add_event_attendees`

Add attendees to an existing calendar event.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendar_id` | string | ✅ | Calendar ID |
| `event_id` | string | ✅ | Event ID |
| `attendee_open_ids` | array[string] | ✅ | List of attendee open_ids |

---

### `list_calendar_events`

Query the list of events in the specified calendar within a time range.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `calendar_id` | string | ✅ | Calendar ID |
| `start_time` | string | ❌ | Query start time (RFC3339 format) |
| `end_time` | string | ❌ | Query end time (RFC3339 format) |

**Returns**

```json
[
  {
    "event_id": "xxx",
    "summary": "Q1 Planning Meeting",
    "start_time": "2026-02-01T14:00:00+08:00",
    "end_time": "2026-02-01T15:00:00+08:00"
  }
]
```

---

## Drive & Document Tools

### `create_folder`

Create a new folder in Feishu Drive (Cloud Space).

> **Limit**: a single directory level supports at most 1,500 nodes; call rate limit is 5 requests/second.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | ✅ | Folder name (1–256 bytes) |
| `folder_token` | string | ❌ | Parent folder token; leave empty to create in the root directory |

**Returns**

```json
{
  "token": "fldbcddUuPz8VwnpPx5oc2abcef",
  "url": "https://feishu.cn/drive/folder/fldbcddUuPz8VwnpPx5oc2abcef"
}
```

---

### `create_document`

Create a new document in Feishu Drive.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | ✅ | Document title |
| `folder_token` | string | ❌ | Target folder token; leave empty to create in the root directory |

**Returns**

```json
{
  "document_id": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "url": "https://docs.feishu.cn/docs/xxxx"
}
```

---

### `write_document_markdown`

Write Markdown-formatted content into a document. Supports headings, lists, code blocks, bold, italic, and other common syntax.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | ✅ | Document ID |
| `markdown` | string | ✅ | Markdown-formatted content |

**Supported Markdown Syntax**

| Syntax | Rendered as |
|--------|-------------|
| `# Heading` | Heading 1 |
| `## Heading` | Heading 2 |
| `- item` | Unordered list |
| `1. item` | Ordered list |
| `` `code` `` | Inline code |
| ` ```code block``` ` | Code block |
| `**bold**` | Bold |
| `*italic*` | Italic |
| Plain paragraph | Text block |

**Returns**

```json
{
  "success": true,
  "blocks_written": 12
}
```

---

### `upload_file`

Upload a local file to Feishu Drive.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | ✅ | Absolute path to the local file |
| `file_name` | string | ❌ | Target file name; defaults to the original file name |
| `parent_token` | string | ❌ | Target folder token |

**Returns**

```json
{
  "file_token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

> To get a shareable link, use [`upload_file_and_share`](#upload_file_and_share), which automatically handles permission setup and link retrieval after upload.

---

### `upload_file_and_share`

Upload a local file to Feishu Drive and complete the "visible to all" link-sharing setup in one step, returning a shareable link ready to send to a group.

> Equivalent to calling `upload_file` → `set_doc_public_access(type="file", rule="tenant_readable")` → `get_share_link` in sequence. Ideal for AI agents (e.g. NanoBot) that need to share files in a group chat.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | ✅ | Absolute path to the local file |
| `file_name` | string | ❌ | Target file name; defaults to the original file name |
| `parent_token` | string | ❌ | Target folder token |

**Returns**

```json
{
  "file_token": "HlADbRw6vobBrIxIB7Pc2oKCnwN",
  "file_name": "report.txt",
  "share_url": "https://feishu.cn/file/HlADbRw6vobBrIxIB7Pc2oKCnwN"
}
```

**Typical agent usage**

```
# 1. Obtain/generate local file
# 2. Upload and get link in one step
result = upload_file_and_share("/tmp/report.md", "research-report.md")
# 3. Send link to the group
send_message(chat_id, result["share_url"])
```

---

### `insert_file_block`

Insert a downloadable file attachment block at the end of a document. Typically used together with `upload_file`.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `document_id` | string | ✅ | Target document ID |
| `file_token` | string | ✅ | Token of the uploaded file (from `upload_file`) |
| `file_name` | string | ✅ | Display name for the file |

---

### `set_doc_permission`

Add collaborator permissions to a document or file — supports both per-user (open_id) and per-group (chat_id) authorization simultaneously.

> ⚠️ **Important prerequisite for group authorization**: when using `chat_ids`, the bot must already be in the group, otherwise the API returns error `1063003`.  
> Add the bot via "Feishu Group Settings → Group Bots → Add Bot".

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_token` | string | ✅ | Document/file token |
| `file_type` | string | ✅ | `doc` \| `docx` \| `file` \| `bitable` \| `sheet` |
| `member_open_ids` | array[string] | ❌ | List of user open_ids (can be used together with `chat_ids`), default `[]` |
| `chat_ids` | array[string] | ❌ | List of group chat_ids (starting with `oc_`); the entire group gets permission, default `[]` |
| `perm_type` | string | ❌ | `view` (read-only) \| `edit` (editable) \| `full_access` (manageable), default `view` |

**Example: open a document to an entire group**

```
set_doc_permission(
  file_token="doccnXxx",
  file_type="docx",
  chat_ids=["oc_xxxxxxxxxxxxxxxx"],
  perm_type="view"
)
```

---

### `set_doc_public_access`

Set the external link sharing permission (link visibility) for a document — the simplest way to open a document to group members.

| `access_level` | Effect |
|----------------|--------|
| `tenant_readable` | Anyone in the org with the link can read (**recommended for group sharing**) |
| `tenant_editable` | Anyone in the org with the link can edit |
| `anyone_readable` | Anyone on the internet with the link can read |
| `anyone_editable` | Anyone on the internet with the link can edit |
| `off` | Disable external link sharing |

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_token` | string | ✅ | Document token |
| `file_type` | string | ✅ | File type |
| `access_level` | string | ❌ | Access level, default `tenant_readable` |

> **Recommended workflow**: `create_document` → `write_document_markdown` → `set_doc_public_access("tenant_readable")` → `get_share_link` → `send_message` (send the link to the group)

---

### `get_share_link`

Get the sharing link for a document.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_token` | string | ✅ | Document/file token |
| `file_type` | string | ✅ | File type |

**Returns**

```
"https://feishu.cn/docx/xxxxxxxxxxxxxxxx"
```

---

### `grant_permission_request`

Handle a cloud document permission request event by granting permission to the specified user. Typically called inside a Webhook / long-connection event handler.

**Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_token` | string | ✅ | Document/file token |
| `file_type` | string | ✅ | File type |
| `user_open_id` | string | ✅ | open_id of the requester |
| `perm_type` | string | ❌ | Permission to grant, default `view` |

---

## Permission Management

### Access Method Comparison

| Method | Tool | Effect | Constraint |
|--------|------|--------|------------|
| **Link sharing** | `set_doc_public_access` | Anyone in the org with the link can access | No extra setup needed |
| **Group collaborator** | `set_doc_permission(chat_ids=[...])` | Adds the entire group as collaborators with a specific permission | Bot must be in the group |
| **Per-user authorization** | `set_doc_permission(member_open_ids=[...])` | Grants permission to specific users | Users must be in the same org and mutually visible |

---

## Error Handling

All tools raise an exception with the following information when a call fails:

```json
{
  "code": 99991671,
  "msg": "user not found",
  "error": "Feishu API returned an error"
}
```

Common error codes:

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `1063003` | Bot not in the group when adding group collaborator | Add the bot to the target group |
| `1063002` | Insufficient permission to modify collaborators | Ensure the app has been granted "Add Document App" authorization |
| `1063001` | Parameter mismatch (token/type/member_id error) | Check that file_type matches the token |
| `99991671` | User does not exist | Check open_id |
| `230001` | Document does not exist | Check document_id |
| `1062507` | Folder single-level node limit exceeded (1,500) | Create inside a sub-folder |
| `1254043` | Insufficient app permissions | Enable the corresponding permissions on the Feishu Developer Console |
| `99991663` | Token expired | Auto-refresh will handle it; retry |
