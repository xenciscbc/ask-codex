"""Start the cdt MCP server directly (same command/args as the probe) and ask it for tools/list over stdio."""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

extra = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
args = json.loads(next(a for a in extra if a.startswith("mcp_servers.cdt.args=")).split("=", 1)[1])
env = dict(os.environ, CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY="1", CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS="1")
proc = subprocess.Popen(["cmd", *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=env, cwd="D:/tmp/exercise-probe/ws")
lines = []
threading.Thread(target=lambda: [lines.append(l) for l in proc.stdout], daemon=True).start()
errs = []
threading.Thread(target=lambda: [errs.append(l) for l in proc.stderr], daemon=True).start()


def send(message):
    proc.stdin.write((json.dumps(message) + "\n").encode())
    proc.stdin.flush()


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}}})
start = time.time()
while not lines and time.time() - start < 120:
    time.sleep(0.5)
print("init after %.1fs:" % (time.time() - start), lines[0][:300] if lines else "NO REPLY")
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
time.sleep(5)
for line in lines[1:]:
    try:
        print("tools", [t["name"] for t in json.loads(line)["result"]["tools"]])
    except (ValueError, KeyError):
        print("OTHER", line[:300])
print("stderr", b"".join(errs)[:1500])
proc.stdin.close()
proc.kill()
subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
