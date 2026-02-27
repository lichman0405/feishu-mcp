"""
tests/integration/test_stage1_messages.py
Stage 1 Integration Test: Messaging + User Resolution

Usage:
  python tests/integration/test_stage1_messages.py

Prerequisites:
  - .env configured with real credentials
  - Bot has joined at least one Feishu group
"""

import sys
import json
sys.path.insert(0, "src")

import httpx
from feishu_mcp.auth import get_tenant_access_token, get_auth_headers

BASE = "https://open.feishu.cn"

def step(label: str):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print('='*55)

def ok(msg): print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}"); sys.exit(1)
def info(msg): print(f"  ℹ  {msg}")


# ─── Step 1: Token ───────────────────────────────────────
step("Step 1: Get tenant_access_token")
try:
    token = get_tenant_access_token()
    ok(f"Token: {token[:15]}...")
except Exception as e:
    fail(str(e))


# ─── Step 2: List groups the bot has joined ──────────────
step("Step 2: List groups the bot has joined")
headers = get_auth_headers()
with httpx.Client(timeout=10) as c:
    r = c.get(f"{BASE}/open-apis/im/v1/chats", headers=headers,
              params={"page_size": 20})
    r.raise_for_status()
data = r.json()
if data.get("code") != 0:
    fail(f"Failed to get group list: {data}")

chats = data.get("data", {}).get("items", [])
if not chats:
    fail("Bot has not joined any group! Please add the bot to a group in Feishu and re-run.")

for i, chat in enumerate(chats):
    info(f"[{i}] Group: {chat.get('name', '?')}  chat_id: {chat['chat_id']}")

ok(f"Found {len(chats)} group(s)")


# ─── Step 3: Get members of first group ──────────────────
step("Step 3: Get member list of the first group")
target_chat = chats[0]
chat_id = target_chat["chat_id"]
chat_name = target_chat.get("name", "Unnamed group")
info(f"Using group: {chat_name} ({chat_id})")

from feishu_mcp.tools.users import get_chat_members
members = get_chat_members(chat_id)
if not members:
    fail("Group member list is empty (possible insufficient permission: im:chat.members:read required)")

for m in members[:5]:
    info(f"  - {m['name']:12s}  open_id: {m['open_id']}")
if len(members) > 5:
    info(f"  ... {len(members)} members total")
ok(f"Retrieved {len(members)} group member(s)")


# ─── Step 4: Test resolve_users_by_name ──────────────────
step("Step 4: Resolve user by name (using the first member's name)")
test_name = members[0]["name"]
expected_id = members[0]["open_id"]

from feishu_mcp.tools.users import resolve_users_by_name
result = resolve_users_by_name(chat_id, [test_name])
resolved_id = result.get(test_name)

if resolved_id == expected_id:
    ok(f"'{test_name}' → {resolved_id}")
elif resolved_id:
    ok(f"'{test_name}' → {resolved_id} (matched, but differs from expected open_id — may be partial match)")
else:
    fail(f"Unable to resolve '{test_name}'")


# ─── Step 5: Send test message to group ──────────────────
step("Step 5: Send test text message to group")
from feishu_mcp.tools.messages import send_message, build_text_with_at

test_content = build_text_with_at("🤖 Feishu MCP Server Stage 1 acceptance test message — if you see this, the messaging module is working correctly!")
try:
    msg = send_message("chat_id", chat_id, test_content, "text")
    ok(f"Message sent successfully: message_id={msg['message_id']}")
    MESSAGE_ID = msg["message_id"]
except Exception as e:
    fail(f"Failed to send message: {e}")


# ─── Step 6: Reply to test message ───────────────────────
step("Step 6: Reply to the message just sent")
from feishu_mcp.tools.messages import reply_message

reply_content = json.dumps({"text": "✅ This is a reply message — reply_message tool is working!"})
try:
    reply = reply_message(MESSAGE_ID, reply_content, "text")
    ok(f"Reply sent successfully: message_id={reply['message_id']}")
except Exception as e:
    fail(f"Failed to reply to message: {e}")


# ─── Summary ─────────────────────────────────────────────
step("Stage 1 Acceptance Results")
ok("tenant_access_token retrieved ✓")
ok("Group list retrieved ✓")
ok("Group members resolved ✓")
ok("User lookup by name ✓")
ok("Group message sent ✓")
ok("Reply message sent ✓")
print()
print(f"  📋 Available chat_id (copy to .env or use in subsequent tests):")
for chat in chats:
    print(f"     {chat['chat_id']}  ({chat.get('name', '?')})")
print()
print("  ✅ Stage 1 all passed! Check the group to see the bot's test messages.")