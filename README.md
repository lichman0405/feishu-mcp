# feishu-miqroera-mcp

> 🤖 **Feishu MCP Server** — Let AI Agents directly control Feishu: send messages, create calendars, manage tasks, and write cloud documents.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MCP](https://img.shields.io/badge/Protocol-MCP-purple)](https://modelcontextprotocol.io/)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Connect an AI Agent](#connect-an-ai-agent)
  - [NanoBot (recommended)](#nanobot-recommended)
  - [Claude Desktop](#claude-desktop)
  - [Cursor](#cursor)
  - [Cline / Continue / Other MCP-compatible tools](#cline--continue--other-mcp-compatible-tools)
- [Long-Connection Event Listener](#long-connection-event-listener)
- [Docker Deployment](#docker-deployment)
- [Full Tool List](#full-tool-list)
- [Feishu App Permissions](#feishu-app-permissions)
- [Development & Contributing](#development--contributing)

---

## Features

This project implements an **MCP (Model Context Protocol) Server** that wraps Feishu’s core capabilities as structured AI tools, enabling any MCP-compatible AI Agent / LLM toolchain to:

| Capability | Functions |
|------------|-----------|
| 💬 Messages | Send & reply to group messages, @mention members, Markdown format |
| 📅 Calendar | Create/query group calendars, create events, invite attendees |
| ✅ Tasks | Create tasks, assign owners, set due dates |
| 📄 Documents | Create cloud docs, write Markdown content, upload files, one-click share links, set collaborator permissions |
| 👥 Users | Get group member lists, resolve users by name |
| 🔔 Events | Receive Feishu push events via long-connection WebSocket in real time (no public IP required) |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-username/feishu-miqroera-mcp.git
cd feishu-miqroera-mcp

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

### 2. Configure Feishu app credentials

```bash
cp .env.example .env
```

Edit `.env`:

```env
FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> How to get credentials: log in to the [Feishu Open Platform](https://open.feishu.cn/) → create an in-house app → go to the "Credentials & Basic Info" page

### 3. Verify the installation

```bash
# Confirm the MCP server starts correctly (Ctrl+C to exit)
.venv\Scripts\python.exe -m feishu_mcp.server
```

You should see `MCP server running on stdio` indicating success.

---

## Connect an AI Agent

### NanoBot (recommended)

[NanoBot](https://github.com/HKUDS/nanobot) is a lightweight multimodal AI Agent framework with native support for MCP Servers and Feishu channels.

**Step 1: Edit the NanoBot config file**

```bash
# Config file location (auto-created)
~/.nanobot/config.json        # macOS / Linux
%USERPROFILE%\.nanobot\config.json  # Windows
```

**Step 2: Add feishu-mcp to `tools.mcpServers`**

```json
{
  "tools": {
    "mcpServers": {
      "feishu-mcp": {
        "command": "C:/path/to/feishu-miqroera-mcp/.venv/Scripts/python.exe",
        "args": ["-m", "feishu_mcp.server"],
        "env": {
          "FEISHU_APP_ID": "cli_xxxxxxxxxxxxxxxxxx",
          "FEISHU_APP_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        }
      }
    }
  },
  "channels": {
    "feishu": {
      "appId": "cli_xxxxxxxxxxxxxxxxxx",
      "appSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    }
  }
}
```

> **Windows note**: Use forward slashes `/` or double backslashes `\\` in paths

**Step 3: Start NanoBot**

```bash
nanobot run
```

NanoBot will automatically establish a Feishu long connection; the AI can then drive Feishu operations via natural language.

---

### Claude Desktop

**Step 1: Locate the config file**

| OS | Path |
|----|------|
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

**Step 2: Add the MCP Server config**

```json
{
  "mcpServers": {
    "feishu-mcp": {
      "command": "C:/path/to/feishu-miqroera-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "feishu_mcp.server"],
      "env": {
        "FEISHU_APP_ID": "cli_xxxxxxxxxxxxxxxxxx",
        "FEISHU_APP_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

> **macOS** example: `"command": "/Users/yourname/feishu-miqroera-mcp/.venv/bin/python"`

**Step 3: Restart Claude Desktop**

After restarting, look for the 🔧 icon in the chat input area and confirm "feishu-mcp" is loaded.

---

### Cursor

**Step 1: Locate the config file**

```
<project root>/.cursor/mcp.json
```

Or global config:

| OS | Path |
|----|------|
| Windows | `%USERPROFILE%\.cursor\mcp.json` |
| macOS | `~/.cursor/mcp.json` |

**Step 2: Add config**

```json
{
  "mcpServers": {
    "feishu-mcp": {
      "command": "C:/path/to/feishu-miqroera-mcp/.venv/Scripts/python.exe",
      "args": ["-m", "feishu_mcp.server"],
      "env": {
        "FEISHU_APP_ID": "cli_xxxxxxxxxxxxxxxxxx",
        "FEISHU_APP_SECRET": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

**Step 3**: Open Cursor → Settings → MCP → Confirm feishu-mcp status is green

---

### Cline / Continue / Other MCP-compatible tools

All tools that support MCP stdio transport can connect using the same config format:

```json
{
  "command": "/absolute/path/to/.venv/bin/python",
  "args": ["-m", "feishu_mcp.server"],
  "env": {
    "FEISHU_APP_ID": "cli_xxx",
    "FEISHU_APP_SECRET": "xxx"
  }
}
```

---

## Long-Connection Event Listener

Feishu's long connection (WebSocket) **requires no public IP** and no ngrok — receive Feishu push events directly from behind NAT.

```bash
# Start the event listener standalone (runs 24/7)
.venv\Scripts\python.exe -m feishu_mcp.webhook.longconn
```

Example log output after startup:

```
INFO  Connecting to Feishu WebSocket: wss://msg-frontier.feishu.cn/ws/v2
INFO  Feishu long connection established
INFO  Received message event: chat_id=oc_xxx, sender=ou_xxx, text=Hello
```

Receiving events in your own application code:

```python
import lark_oapi as lark

client = lark.Client.builder() \
    .app_id("cli_xxx") \
    .app_secret("xxx") \
    .event_callback(lark.EventType.IM_MESSAGE_RECEIVE_V1, your_handler) \
    .build()

ws = lark.ws.Client(app_id, app_secret, event_handler=client.event_handler)
ws.start()
```

---

## Docker Deployment

### Using Docker directly

```bash
# Build image
docker build -t feishu-miqroera-mcp .

# Start Feishu event listener (background)
docker run -d \
  --name feishu-listener \
  --env-file .env \
  --restart unless-stopped \
  feishu-miqroera-mcp \
  feishu_mcp.webhook.longconn

# View logs
docker logs -f feishu-listener
```

### Using Docker Compose

```bash
# Copy and fill in env vars
cp .env.example .env
# Edit .env with APP_ID and APP_SECRET

# Start event listener
docker compose up -d feishu-listener

# Check status
docker compose ps

# View logs
docker compose logs -f feishu-listener
```

> **MCP Server (stdio)** is usually invoked directly as a local process by the AI Agent framework and does not need to be containerized.  
> Docker is primarily used for persistently running the **event listener**.

---

## Full Tool List

| Tool | Description |
|------|-------------|
| `get_chat_members` | Get the member list of a group |
| `resolve_users_by_name` | Look up users in a group by name |
| `send_message` | Send a text/rich-text message to a group or user |
| `reply_message` | Reply to a specific message |
| `get_or_create_group_calendar` | Get or create a shared group calendar |
| `create_calendar_event` | Create an event in a calendar |
| `add_event_attendees` | Add attendees to a calendar event |
| `list_calendar_events` | Query the list of calendar events |
| `create_task` | Create a Feishu task (with due time and description) |
| `assign_task` | Assign an owner to a task |
| `add_task_to_list` | Add a task to a tasklist |
| `list_tasks` | Query the task list |
| `create_folder` | Create a folder in Drive |
| `create_document` | Create a Feishu cloud document |
| `write_document_markdown` | Write Markdown content into a document |
| `upload_file` | Upload a file to Feishu Drive |
| `upload_file_and_share` | Upload a file and return a shareable link in one step (upload + set permission + get link) |
| `insert_file_block` | Insert a file attachment block into a document |
| `set_doc_permission` | Add collaborators to a document (supports users or groups) |
| `set_doc_public_access` | Set document public access / link sharing permission |
| `get_share_link` | Get the sharing link for a document |
| `grant_permission_request` | Handle a permission request and authorize the applicant |

See [docs/api.md](docs/api.md) for full parameter details.

---

## Feishu App Permissions

Enable the following permissions in your app's management page on the [Feishu Developer Console](https://open.feishu.cn/):

| Permission | Purpose |
|------------|--------|
| `im:message` | Send/receive messages |
| `im:message.group_at_msg` | Group @mention feature |
| `im:chat.members:read` | Read group members |
| `task:task` | Task read/write |
| `calendar:calendar` | Calendar read/write |
| `drive:drive` | Drive/document read/write |
| `docx:document` | Cloud document content editing |

Path to enable permissions: App Management → Permission Management → Enable the above permissions → Publish version.

---

## Development & Contributing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires real Feishu credentials)
pytest tests/integration/ -v

# Format code
ruff format src/ tests/

# Lint check
ruff check src/ tests/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

[MIT](LICENSE) © 2026 feishu-miqroera-mcp contributors
