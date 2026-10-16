"""Snapshot for the C7 live acceptance: config.toml bytes and hash, process list, TEMP browser profiles, guard cache.

    python -I baseline.py <out.json> [<compare-with.json>]
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG = Path(r"D:\codex\config.toml")
TEMP = Path(os.environ.get("TEMP", r"R:\Temp"))
CACHE = Path(os.environ["LOCALAPPDATA"]) / "ask-codex"


def processes():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,CreationDate,"
                          "CommandLine | ConvertTo-Json -Compress"], capture_output=True, text=True, encoding="utf-8")
    rows = json.loads(out.stdout)
    return {str(r["ProcessId"]): {"name": r["Name"], "parent": r["ParentProcessId"], "created": str(r["CreationDate"]),
                                  "cmd": (r["CommandLine"] or "")[:300]} for r in rows}


def snapshot(out):
    data = CONFIG.read_bytes()
    value = {
        "config_sha256": hashlib.sha256(data).hexdigest(),
        "processes": processes(),
        "temp_profiles": sorted(p.name for p in TEMP.iterdir()
                                if p.name.startswith(("puppeteer_dev_chrome_profile-", "chrome-devtools-mcp-"))),
        "cache": sorted(str(p.relative_to(CACHE)) for p in CACHE.rglob("*") if p.is_file()) if CACHE.exists() else [],
        "eval_stub": Path(r"D:\work_data\project\skill\ask-codex\.eval-stub").exists(),
    }
    Path(out).write_text(json.dumps(value, indent=1), encoding="utf-8")
    shutil.copyfile(CONFIG, Path(out).with_suffix(".config.toml"))
    return value


def compare(a, b):
    added = {pid: row for pid, row in b["processes"].items()
             if pid not in a["processes"] or a["processes"][pid]["created"] != row["created"]}
    interesting = {pid: row for pid, row in added.items()
                   if row["name"].lower() in ("chrome.exe", "node.exe", "codex.exe", "python.exe", "python3.exe",
                                              "bash.exe", "conhost.exe", "cmd.exe")}
    return {"config_same": a["config_sha256"] == b["config_sha256"],
            "temp_profiles_added": sorted(set(b["temp_profiles"]) - set(a["temp_profiles"])),
            "cache_added": sorted(set(b["cache"]) - set(a["cache"])),
            "new_processes_of_interest": interesting}


if __name__ == "__main__":
    now = snapshot(sys.argv[1])
    if len(sys.argv) > 2:
        before = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        print(json.dumps(compare(before, now), indent=1))
    else:
        print(json.dumps({k: v for k, v in now.items() if k != "processes"}, indent=1))
