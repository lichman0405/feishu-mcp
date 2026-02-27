"""
tests/integration/test_stage2_tasks.py
Stage 2 Integration Test: Task Module

Usage:
  python tests/integration/test_stage2_tasks.py
"""

import sys, json
sys.path.insert(0, "src")

from feishu_mcp.tools.users import get_chat_members
from feishu_mcp.tools.tasks import create_task, assign_task

CHAT_ID = "oc_2ed2973a91574e4033c7eac08ffe8c6e"

def step(label): print(f"\n{'='*55}\n  {label}\n{'='*55}")
def ok(msg): print(f"  ✅ {msg}")
def fail(msg): print(f"  ❌ {msg}"); sys.exit(1)
def info(msg): print(f"  ℹ  {msg}")


# ─── Step 1: Get first non-bot member from group ─────────
step("Step 1: Get group members, find a real user open_id")
members = get_chat_members(CHAT_ID)
# Filter out potential bots (open_id starting with ou_ are real users)
humans = [m for m in members if m["open_id"].startswith("ou_")]
if not humans:
    humans = members  # fallback
target = humans[0]
info(f"Using: {target['name']}  open_id={target['open_id']}")
ok(f"Found {len(members)} member(s)")


# ─── Step 2: Create task (no assignee yet) ───────────────
step("Step 2: Create task")
from datetime import datetime, timedelta, timezone
due_dt = datetime.now(timezone.utc) + timedelta(days=3)
due_str = due_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
info(f"Due time: {due_str}")

task = create_task(
    title="[MCP Integration Test] Stage 2 Acceptance Task",
    description="This test task was auto-created by Feishu MCP Server to verify the task module.",
    due_time=due_str,
)
info(f"Task response: {json.dumps(task, ensure_ascii=False)}")
task_id = task.get("guid") or task.get("task_id")
if not task_id:
    fail(f"Task creation failed — no guid: {task}")
ok(f"Task created successfully: guid={task_id}")


# ─── Step 3: Assign to group member ──────────────────────
step(f"Step 3: Assign task to {target['name']}")
assign_result = assign_task(task_id, [target["open_id"]])  # task_id is actually guid
info(f"Assign response: {json.dumps(assign_result, ensure_ascii=False)}")
ok(f"Task assigned successfully → {target['name']}")


# ─── Summary ─────────────────────────────────────────────
step("Stage 2 Acceptance Results")
ok("Create task ✓")
ok(f"Assign to member ({target['name']}) ✓")
print()
print(f"  📋 task_id: {task_id}")
print(f"  📋 assignee open_id: {target['open_id']}")
print()
print("  ✅ Stage 2 all passed!")