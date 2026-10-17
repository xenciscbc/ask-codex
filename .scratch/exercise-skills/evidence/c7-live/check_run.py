"""Check a captured run directory against the C7 live acceptance items.  python -I check_run.py <run capture dir>"""
import json
import re
import sys
from pathlib import Path

run = Path(sys.argv[1])
out = {}
plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
nonce = None
for key in ("nonce",):
    nonce = plan.get("browser", {}).get(key) or plan.get(key)
definition = json.dumps(plan.get("browser", {}).get("definition", {}))
servers = set(re.findall(r'"(cdt_[0-9a-f]+)"', definition)) or set(re.findall(r"cdt_[0-9a-f]+", (run / "0/argv").read_text(encoding="utf-8", errors="replace")))
out["nonce_servers"] = sorted(servers)
guard = json.loads((run / "guard.json").read_text(encoding="utf-8"))
out["guard_source"] = guard.get("source")
items = guard.get("items") if isinstance(guard.get("items"), list) else None
out["guard_items_type"] = type(guard.get("items")).__name__
if items:
    out["guard_decoy_items"] = [i for i in items if "decoy" in json.dumps(i).lower() or "record" in json.dumps(i).lower()]
    out["guard_failing"] = [i for i in items if not i.get("ok")]
mcp_calls, approval, commands, writes = 0, [], [], []
WRITE = re.compile(r"(?i)(\bset-content\b|\bout-file\b|\badd-content\b|\bnew-item\b|\bremove-item\b|\bcopy-item\b|\bmove-item\b|\brm\b|\bmv\b|\bcp\b|\bmkdir\b|\btouch\b|>\s*[^&|]|\btee\b|\bsed\s+-i|\bdel\b|\bwrite_text\b|\bopen\([^)]*['\"]w)")
for line in (run / "0/events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    item = event.get("item") or {}
    kind = item.get("type") or item.get("item_type")
    text = json.dumps(item)
    if kind == "mcp_tool_call":
        mcp_calls += 1
        if "requires approval" in text.lower():
            approval.append(item.get("tool"))
    if kind == "command_execution" and event.get("type") == "item.completed":
        command = item.get("command", "")
        commands.append(command)
        if WRITE.search(command):
            writes.append(command)
out["mcp_tool_call_events"] = mcp_calls
started, completed, images = 0, 0, 0
for line in (run / "0/events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
    try:
        event = json.loads(line)
    except ValueError:
        continue
    item = event.get("item") or {}
    if item.get("type") != "mcp_tool_call":
        continue
    if event.get("type") == "item.started":
        started += 1
    elif event.get("type") == "item.completed":
        completed += 1
        result = item.get("result") or {}
        if item.get("tool") == "take_screenshot" and any(
                isinstance(c, dict) and c.get("type") == "image" for c in (result.get("content") or [])):
            images += 1
out["mcp_tool_calls_started"] = started
out["mcp_tool_calls_completed"] = completed
out["screenshots_returning_an_image"] = images
out["requires_approval"] = approval
out["command_executions"] = commands
out["possibly_writing_commands"] = writes
screens = []
for line in (run / "0/events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines():
    if "filePath" in line and "take_screenshot" in line:
        try:
            item = json.loads(line).get("item") or {}
        except ValueError:
            continue
        if json.loads(line).get("type") == "item.completed":
            screens.append({"args": item.get("arguments"), "result": json.dumps(item.get("result") or item.get("error"))[:300]})
out["screenshot_filepath_calls"] = screens
sup = run / "supervisor.log"
out["supervisor_log_tail"] = sup.read_text(encoding="utf-8", errors="replace").splitlines()[-8:] if sup.exists() else None
print(json.dumps(out, indent=1, ensure_ascii=False))
