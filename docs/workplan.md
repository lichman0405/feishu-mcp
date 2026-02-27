# Feishu MCP Server — Work Plan

> Project: `feishu-miqroera-mcp`
> Language: Python 3.11+
> Updated: 2026-02-27

---

## Difficulty Assessment

**Overall difficulty: Medium-high.**

| Module | Difficulty | Main Challenges |
|--------|-----------|----------------|
| Project scaffold + MCP configuration | ⭐⭐ | Learning the mcp Python SDK |
| Token management (tenant/user) | ⭐⭐⭐ | user_access_token involves OAuth2 authorization flow |
| Messaging | ⭐⭐ | API is straightforward and well-structured |
| Calendar (create event + attendees) | ⭐⭐⭐ | Need to handle group calendar lookup/creation; strict token requirements |
| Tasks (task v2) | ⭐⭐ | v2 API docs are newer and well-structured |
| Cloud documents (write rich text blocks) | ⭐⭐⭐⭐ | Block API has complex nested structure; permissions have multiple layers |
| Webhook event receiving | ⭐⭐⭐ | Requires public internet exposure (ngrok); event signature verification |
| Name → open_id resolution | ⭐⭐⭐ | Fuzzy name matching in Chinese; needs multi-strategy fallback |

---

## About Context7 Feishu API Docs

**Yes, recommended.** Context7 has the following valuable Feishu documentation libraries:

| Library ID | Content | Useful? |
|-----------|---------|---------|
| `/larksuite/lark-openapi-mcp` | Official MCP tool list (with complete IM/Calendar/Tasks/Docs API signatures) | ✅ **Very useful** |
| `/larksuite/oapi-sdk-python` | Official Feishu Python SDK (`lark-oapi`) code examples | ✅ Useful |

**Usage strategy:**
- Before implementing each module, use Context7 to query API parameter structures and examples for that module
- Especially the Block API (cloud document writing) nested structure — must reference the docs

---

## Technology Choice: Python vs TypeScript

**Conclusion: Use Python — completely fine.**

| Dimension | TypeScript | Python |
|-----------|-----------|--------|
| MCP SDK | `@modelcontextprotocol/sdk` (official first choice) | `mcp[cli]` (officially maintained, equally stable) |
| Feishu SDK | `@larksuiteoapi/node-sdk` | `lark-oapi` (official Feishu Python SDK) |
| Team familiarity | Low | High |
| Debug efficiency | Low | High |
| Dependency management | node_modules (complex) | pip + `.venv` (simple) |
| **Recommendation** | — | **✅ Choose Python** |

> The only advantage of TypeScript is more official examples. But the lark-oapi Python SDK covers all required APIs, and the MCP Python SDK is fully capable. Using a familiar language gives 3–5× better development and maintenance efficiency.

---

## Dependencies

```toml
# pyproject.toml
[project]
name = "feishu-miqroera-mcp"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "mcp[cli]>=1.0.0",          # MCP Python SDK (stdio + SSE)
    "lark-oapi>=1.3.0",          # Official Feishu Python SDK
    "httpx>=0.27.0",             # HTTP client (direct API calls)
    "python-dotenv>=1.0.0",      # .env environment variables
    "fastapi>=0.111.0",          # Webhook HTTP server
    "uvicorn>=0.30.0",           # ASGI server (runs FastAPI)
    "pydantic>=2.7.0",           # Data validation
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

---

## Work Plan and Progress

### Stage 0: Environment Setup ✅ Completed (2026-02-27)

**Goal:** Development environment ready; can run a Hello World-level MCP Server

**Tasks:**

- [x] **0.1** Create Python virtual environment
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  pip install mcp[cli] lark-oapi python-dotenv fastapi uvicorn pydantic
  ```

- [x] **0.2** Create project directory scaffold
  ```
  src/feishu_mcp/__init__.py
  src/feishu_mcp/server.py
  src/feishu_mcp/auth.py
  src/feishu_mcp/tools/__init__.py
  ```

- [x] **0.3** Create `.env.example` and `.gitignore`

- [x] **0.4** Create self-built app on the Feishu Developer Console, obtain `App ID` and `App Secret`
  - Enable Bot capability
  - Apply for base permissions (see requirements.md Section 3)

- [x] **0.5** Implement `auth.py`: wrap `tenant_access_token` retrieval (auto-cache with 2h validity)

**Acceptance criteria:**
- `python -m feishu_mcp.server` starts and outputs MCP Server ready message
- `auth.py` successfully retrieves `tenant_access_token` and prints the first 10 characters

---

### Stage 1: Messaging Module + User Resolution 🔵 First Milestone

**Goal:** Agent can send/receive messages in a group and look up group members by name

**Tasks:**

- [x] **1.1** Implement `tools/users.py`
  - `get_chat_members(chat_id)` → returns `[{name, open_id, user_id}]`
  - `resolve_users_by_name(chat_id, names)` → fuzzy name match, returns `open_id` list
  - Strategy: cache group member list first, then do name matching; fallback to `GET /search/v1/user`

- [x] **1.2** Implement `tools/messages.py`
  - `send_message(receive_id_type, receive_id, msg_type, content)` → send text/rich text
  - `reply_message(message_id, content, msg_type)` → reply to a message

- [x] **1.3** Register the above tools in `server.py`

**Acceptance criteria:**
- Call `send_message` via MCP Inspector; group receives the message ✅
- Call `resolve_users_by_name`; can find the open_id of a group member ✅
- Call `reply_message`; successfully replies to a message ✅

---

### Stage 2: Calendar Module 🔵 Second Milestone

**Goal:** Agent can create events in the group shared calendar and send invite popups to attendees

**Tasks:**

- [x] **2.1** Understand and implement group calendar lookup logic
  - `get_or_create_group_calendar(chat_id)`
  - Call `GET /calendar/v4/calendars`, filter by `type=group`
  - If not found, call `POST /calendar/v4/calendars` to create a shared calendar

- [x] **2.2** Implement `tools/calendar.py`
  - `create_calendar_event(calendar_id, summary, start_time, end_time, description, is_online)`
    - Set `vchat: {vc_type: "vc"}` when `is_online=True`
  - `add_event_attendees(calendar_id, event_id, attendee_open_ids)`
    - Add attendees of type `attendee_type=user`
    - Attendees automatically receive a "Accept/Decline" invite popup
  - `list_calendar_events(calendar_id, start_time, end_time)` → list events

- [x] **2.3** Handle Token requirements
  - If using `tenant_access_token` for `create_calendar_event`, the organizer is the Bot
    - Set `attendee_ability: "can_see_others"` and add the real organizer as an attendee
    - Or guide user through OAuth authorization to obtain `user_access_token` (recommended long-term)

- [x] **2.4** Register calendar tools in `server.py`

**Acceptance criteria:**
- After calling the tool chain, the event appears in the Feishu Calendar app ✅
- Attendees receive an "Accept/Decline" invite popup ✅
- Online meeting has a VC link ✅

---

### Stage 3: Task Module 🔵 Third Milestone

**Goal:** Agent can create tasks and assign them to group members

**Tasks:**

- [x] **3.1** Implement `tools/tasks.py` (all using task/v2 API)
  - `create_task(title, description, start_time, due_time)` → returns `task_guid`
  - `assign_task(task_guid, assignee_open_ids)` → calls `POST /task/v2/tasks/:task_guid/add_members`; `role = "assignee"`
  - `list_tasks(tasklist_guid, assignee_open_id)` → list tasks

- [x] **3.2** Register task tools in `server.py`

**Acceptance criteria:**
- The new task appears in the assignee's Feishu Tasks app ✅
- Task has correct title, description, and start/due time ✅
- Requester sees a confirmation message in the group ✅

---

### Stage 4: Cloud Document Module 🔵 Fourth Milestone

**Goal:** Agent can create cloud documents, write rich text content, upload files, and manage permissions

**Tasks:**

- [x] **4.1** Implement `tools/documents.py` — document creation and content writing
  - `create_document(title, folder_token)` → returns `document_id`
  - `write_document_markdown(document_id, markdown_content)` → converts Markdown to Feishu Block structure (paragraphs, headings, lists, code blocks, links)
  - Calls `POST /docx/v1/documents/:id/blocks/batch_create`

- [x] **4.2** Implement file upload
  - `upload_file(local_path, file_name, parent_token)` → calls `POST /drive/v1/files/upload_all` (files ≤20MB); returns `file_token`

- [x] **4.3** Implement `insert_file_block(document_id, file_token, file_name)` — insert a downloadable file block at the end of a document

- [x] **4.4** Implement permission management
  - `set_doc_permission(file_token, file_type, member_open_ids, perm_type)` — `perm_type`: `"view"` / `"edit"` / `"full_access"`
  - `set_doc_public_access(file_token, file_type, access_level)` — set "anyone with the link can view/edit"
  - `get_share_link(file_token, file_type)` → returns external URL

- [x] **4.5** Register document tools in `server.py`

**Acceptance criteria:**
- A new document appears in Drive with correctly rendered content (headings/paragraphs/links/lists) ✅
- PDF attachment is accessible as a clickable download inside the document ✅
- Group members have edit permission ✅
- External link is accessible ✅

---

### Stage 5: Webhook Event Handling 🔵 Fifth Milestone

**Goal:** MCP Server can receive Feishu push events (messages, permission requests)

**Tasks:**

- [x] **5.1** Implement Webhook HTTP endpoint using FastAPI (`webhook/handler.py`)
  - Feishu event signature verification (`X-Lark-Signature` validation)
  - Challenge-Response validation (for initial Webhook URL configuration)
  - Route dispatch: dispatch by `event.type` to different handlers

- [x] **5.2** Implement event handlers
  - `on_message_receive`: receive @bot messages → trigger Agent flow
  - `on_drive_permission_request`: receive cloud document permission request → call `grant_permission_request`

- [x] **5.3** Local debug configuration
  - Use ngrok / Cloudflare Tunnel to expose local port to internet
  - Configure Webhook callback URL in the Feishu Developer Console

- [x] **5.4** Run `server.py` (MCP) and `webhook/handler.py` (FastAPI) together
  - MCP uses stdio mode (for Agent)
  - FastAPI runs with uvicorn in the background (listening for Feishu events)

**Acceptance criteria:**
- `@bot hello` in a group → bot receives and replies ✅
- Cloud document permission request event triggers → auto-grants and notifies requester ✅

---

### Stage 6: End-to-End Integration Testing 🔵 Sixth Milestone

**Goal:** All three User Stories run end-to-end successfully

**Tasks:**

- [x] **6.1** Story 1 E2E test — calendar event creation and attendee invitations
- [x] **6.2** Story 2 E2E test — task creation and assignment
- [x] **6.3** Story 3 E2E test — document creation, content writing, file upload, permissions
- [x] **6.4** Integrate with OpenClaw or NanoBot using MCP protocol
- [x] **6.5** Write README.md with installation and configuration guide

**Acceptance criteria:**
- All three Stories can be completed autonomously by the Agent without manual intervention ✅
- README is reproducible step-by-step ✅

---

## Risks and Mitigation

| Risk | Mitigation |
|------|-----------|
| `user_access_token` acquisition is complex (requires OAuth2) | Use `tenant_access_token` in Stage 0 to run through basic functionality; the calendar organizer issue can use Bot identity temporarily (allows attendees to initiate the meeting) |
| Feishu Block API has complex nested structure | Before development, query `/larksuite/lark-openapi-mcp` docs on Context7; write a simple markdown→block converter; support paragraphs/headings/lists/links first |
| Local Webhook needs a public internet address | Use `ngrok http 8080` for a quick temporary URL; deploy to a server with a public IP for production |
| Name resolution ambiguity (same-name users) | When multiple results are found, send a Card message to the user asking them to choose manually |
| API permission approval is slow | Apply for all permissions in the Developer Console in advance; work on modules that don't require those permissions while waiting for approval |

---

## Recommended Development Order (Minimum Viable Path)

```
Stage 0 (env) -> Stage 1 (messaging) -> Stage 3 (tasks) -> Stage 2 (calendar) -> Stage 4 (docs basic) -> Stage 5 (webhook) -> Stage 4 (docs full) -> Stage 6 (integration)
```

> Calendar comes after tasks because the token issue for calendar is more complex; completing the simpler task module first builds confidence.
> Cloud documents are split into two stages: create+write first (core of Story 3), then permissions+attachments (enhancements for Story 3).