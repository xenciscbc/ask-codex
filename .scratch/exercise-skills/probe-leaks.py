"""P7: which request types escape chrome-devtools-mcp's --allowedUrlPattern. No Codex call.

Serves 127.0.0.1:8765 (allowed) and 127.0.0.1:8766 (stand-in for a disallowed origin), drives the MCP server over
stdio to open 8765/leak.html, and reports which request types reached 8766. Runs twice: with the allowlist and
without it (control: proves the page really sends each request).

Usage: python probe-leaks.py <out-dir>
"""
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
FAR = "127.0.0.1:8766"
hits = []

LEAK = f"""<!doctype html><html><head><title>Leak probe</title></head><body>
<h1>Leak probe</h1><ul id="r"></ul>
<img src="http://{FAR}/img" width="1" height="1">
<iframe src="http://{FAR}/iframe" width="200" height="50"></iframe>
<script>
function note(k, v) {{ const li = document.createElement('li'); li.textContent = k + ': ' + v; document.getElementById('r').appendChild(li); }}
note('script', 'ran');
try {{
  const pc = new RTCPeerConnection({{iceServers: [{{urls: 'stun:127.0.0.1:3478'}}, {{urls: 'stun:stun.l.google.com:19302'}}]}});
  pc.createDataChannel('x');
  pc.onicecandidate = e => fetch('/report?rtc=' + (e.candidate ? e.candidate.type + '-' + e.candidate.protocol : 'done'));
  pc.createOffer().then(o => pc.setLocalDescription(o));
}} catch (e) {{ fetch('/report?rtc=throw'); }}
fetch('https://example.com/', {{mode: 'no-cors'}}).then(() => fetch('/report?page-ext=ok')).catch(() => fetch('/report?page-ext=fail'));
fetch('http://{FAR}/fetch', {{mode: 'no-cors'}}).then(() => note('fetch', 'resolved')).catch(e => note('fetch', 'error ' + e));
try {{ const ws = new WebSocket('ws://{FAR}/ws'); ws.onopen = () => note('ws', 'open'); ws.onerror = () => note('ws', 'error'); }} catch (e) {{ note('ws', 'throw ' + e); }}
try {{ note('beacon', navigator.sendBeacon('http://{FAR}/beacon', 'x')); }} catch (e) {{ note('beacon', 'throw ' + e); }}
try {{ const w = new Worker('/worker.js'); w.onmessage = m => note('worker', m.data); }} catch (e) {{ note('worker', 'throw ' + e); }}
if (navigator.serviceWorker) {{
  navigator.serviceWorker.register('/sw.js').then(() => note('sw', 'registered')).catch(e => note('sw', 'error ' + e));
}} else {{ note('sw', 'unsupported'); }}
</script></body></html>"""
WORKER = f"fetch('http://{FAR}/worker', {{mode: 'no-cors'}}).then(() => postMessage('fetched')).catch(e => postMessage('error ' + e));"
SW = f"self.addEventListener('install', () => self.skipWaiting());\nself.addEventListener('activate', e => e.waitUntil(Promise.all([fetch('http://{FAR}/sw', {{mode: 'no-cors'}}).catch(() => 0), fetch('https://example.com/', {{mode: 'no-cors'}}).then(() => fetch('/report?sw-ext=ok')).catch(() => fetch('/report?sw-ext=fail'))])));"


def handler(port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if port == 8766:
                hits.append(self.path + (" [upgrade]" if self.headers.get("Upgrade") else ""))
                body, kind = b"ok", "text/plain"
            elif self.path.startswith("/report"):
                hits.append("8765" + self.path)
                body, kind = b"ok", "text/plain"
            elif self.path == "/leak.html":
                body, kind = LEAK.encode(), "text/html"
            elif self.path == "/worker.js":
                body, kind = WORKER.encode(), "text/javascript"
            elif self.path == "/sw.js":
                body, kind = SW.encode(), "text/javascript"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_POST = do_GET

        def log_message(self, *args):
            pass
    return Handler


def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", 3478))
    while True:
        sock.recvfrom(2048)
        hits.append("udp3478")


threading.Thread(target=udp_listener, daemon=True).start()
for port in (8765, 8766):
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", port), handler(port)).serve_forever, daemon=True).start()

BASE = ["C:/Users/admin/AppData/Local/npm-cache/_npx/ba38acecdf97096f/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js", "--isolated", "--headless", "--no-javascript-evaluation",
        "--no-usage-statistics", "--no-performance-crux", "--viewport=1280x720"]


def run(label, extra):
    hits.clear()
    env = dict(os.environ, CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY="1", CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS="1")
    proc = subprocess.Popen(["node", *BASE, *extra], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=env, cwd=str(OUT))
    replies = {}

    def reader():
        for line in proc.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "id" in message:
                replies[message["id"]] = message

    threading.Thread(target=reader, daemon=True).start()

    def call(ident, method, params=None, wait=60):
        message = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        proc.stdin.write((json.dumps(message) + "\n").encode())
        proc.stdin.flush()
        end = time.time() + wait
        while ident not in replies and time.time() < end:
            time.sleep(0.2)
        return replies.get(ident)

    call(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "probe", "version": "0"}})
    proc.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    proc.stdin.flush()
    tools = call(2, "tools/list")["result"]["tools"]
    schema = next(t for t in tools if t["name"] == "navigate_page")["inputSchema"]
    pages = call(6, "tools/call", {"name": "list_pages", "arguments": {}})
    page_id = int(re.search(r"(\d+):", pages["result"]["content"][0]["text"]).group(1))
    args = {"url": "http://127.0.0.1:8765/leak.html", "pageId": page_id}
    if "type" in schema.get("properties", {}):
        args["type"] = "url"
    nav = call(3, "tools/call", {"name": "navigate_page", "arguments": args})
    time.sleep(6)
    # A second load lets an activated service worker run its fetch if activation lagged the first load.
    call(4, "tools/call", {"name": "navigate_page", "arguments": args})
    time.sleep(6)
    snap = call(5, "tools/call", {"name": "take_snapshot", "arguments": {"pageId": page_id}})
    text = json.dumps(snap.get("result", snap) if snap else None, ensure_ascii=False)
    result = {"label": label, "navigate": json.dumps(nav, ensure_ascii=False)[:400], "far_hits": sorted(set(hits)),
              "page_notes": [part for part in text.split("\\n") if ":" in part and "listitem" in part][:20]}
    proc.stdin.close()
    subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    return result


if sys.argv[2:] == ["--control"]:
    results = [run("control (no allowlist)", [])]
elif len(sys.argv) > 2:  # extra MCP flags to try on the allowlist run only (mitigation probes)
    results = [run("allowlist + " + " ".join(sys.argv[2:]), ["--allowedUrlPattern=http://127.0.0.1:8765/*", *sys.argv[2:]])]
else:
    results = [run("control (no allowlist)", []), run("allowlist 8765 only", ["--allowedUrlPattern=http://127.0.0.1:8765/*"])]
(OUT / "p7-leaks.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print(json.dumps(results, indent=1, ensure_ascii=False))
