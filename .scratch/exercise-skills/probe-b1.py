"""Plan review 1, B1: do the browser tools run under the full exercise command line?

The exercise constants (read-only, approval_policy="never", approvals_reviewer="user", --ignore-rules,
agents and apps off, every other MCP server disabled) plus the plan's browser server definition (node
launched directly, nonce name, filesystemRoot, redacted headers, closed proxy owned by this script,
bypass list, WebRTC policy, enabled_tools), against a local page this script serves on 127.0.0.1.

Usage: python -I probe-b1.py <variant>   variant: base | tool-approve | default-approve
Evidence: .scratch/exercise-skills/evidence/b1-<variant>-*
"""
import json
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path("D:/work_data/project/skill/ask-codex")
sys.path.insert(0, str(REPO / "skills/ask/scripts"))
import consult  # noqa: E402

variant = sys.argv[1]
WS = "D:/tmp/ui-b1/ws"
ENTRY = "D:/tmp/ui-b1/mcp/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js"
MCP_CWD = Path("D:/tmp/ui-b1/mcp-cwd")
EVIDENCE_DIR = Path("D:/tmp/ui-b1/ws/evidence")
OUT = REPO / ".scratch/exercise-skills/evidence"
PORT = 18765
TOKEN = secrets.token_hex(4)
TOOLS = ["navigate_page", "new_page", "list_pages", "select_page", "close_page", "take_screenshot", "take_snapshot",
         "click", "hover", "fill", "fill_form", "type_text", "press_key", "drag", "handle_dialog", "wait_for",
         "resize_page", "emulate", "list_console_messages", "get_console_message", "list_network_requests",
         "get_network_request", "get_css_styles", "lighthouse_audit"]

PAGE = """<!doctype html><html><head><title>B1 probe</title></head><body>
<h1 style="background:#0f766e;color:white;padding:16px">Probe form</h1>
<label for="name">Name</label> <input id="name" name="name">
<button id="save" onclick="document.getElementById('out').textContent='Saved: '+document.getElementById('name').value+' / %s'">Save</button>
<p id="out">Nothing saved yet</p></body></html>""" % TOKEN
hits = []


class Page(BaseHTTPRequestHandler):
    def do_GET(self):
        hits.append(self.path)
        body = PAGE.encode() if self.path in ("/", "/index.html") else b"not found"
        self.send_response(200 if self.path in ("/", "/index.html") else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def dead_proxy():
    # Owned closed proxy: accept and close at once, so nothing else can bind the port.
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(16)

    def loop():
        while True:
            try:
                conn, _ = sock.accept()
                conn.close()
            except OSError:
                return
    threading.Thread(target=loop, daemon=True).start()
    return sock.getsockname()[1]


server = ThreadingHTTPServer(("127.0.0.1", PORT), Page)
threading.Thread(target=server.serve_forever, daemon=True).start()
proxy_port = dead_proxy()
MCP_CWD.mkdir(exist_ok=True)
EVIDENCE_DIR.mkdir(exist_ok=True)
node = subprocess.run(["where", "node"], capture_output=True, text=True).stdout.splitlines()[0].strip()
name = "cdt_" + secrets.token_hex(4)
origin = f"127.0.0.1:{PORT}"
cdt_args = [ENTRY, "--isolated", "--headless", "--no-javascript-evaluation", "--no-usage-statistics",
            "--no-performance-crux", "--redactNetworkHeaders", f"--filesystemRoot={EVIDENCE_DIR.as_posix()}",
            "--viewport=1280x720", f"--allowedUrlPattern=http://{origin}/*", f"--proxyServer=http://127.0.0.1:{proxy_port}",
            f"--chromeArg=--proxy-bypass-list=<-loopback>;{origin}",
            "--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
definition = [
    "-c", f"mcp_servers.{name}.command={json.dumps(node)}",
    "-c", f"mcp_servers.{name}.args={json.dumps(cdt_args)}",
    "-c", f"mcp_servers.{name}.cwd={json.dumps(MCP_CWD.as_posix())}",
    "-c", f'mcp_servers.{name}.env={{CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY="1",CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS="1",NODE_OPTIONS=""}}',
    "-c", f"mcp_servers.{name}.startup_timeout_sec=90",
    "-c", f"mcp_servers.{name}.enabled_tools={json.dumps(TOOLS)}",
]
if variant == "tool-approve":
    for tool in TOOLS:
        definition += ["-c", f'mcp_servers.{name}.tools.{tool}.approval_mode="approve"']
elif variant == "default-approve":
    definition += ["-c", f'mcp_servers.{name}.default_tools_approval_mode="approve"']
elif variant != "base":
    raise SystemExit("unknown variant")

prompt = f"""This is a browser-capability probe run by the project owner against their own local test page.

Use the MCP server `{name}` (your MCP tools may be deferred; discover them first). Do not run any shell command and do not open any URL other than the one below.

1. Navigate to http://{origin}/.
2. Take a snapshot.
3. Fill the "Name" field with the text: probe-b1
4. Click the "Save" button.
5. Take a screenshot and report the exact text of the paragraph below the button.

Report each step's result, quoting any error verbatim (including any approval, cancellation or permission message).
"""
request = {"project": WS, "prompt": prompt,
           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}], "confirmations": {}}
with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
    summary, overrides = consult.preflight(request, neutral)
args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json", "-C", WS,
        "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"', *overrides,
        "--disable", "apps", "-c", "agents.enabled=false", "-c", "features.multi_agent_v2.enabled=false",
        "-c", 'approval_policy="never"', "-c", 'approvals_reviewer="user"', "--ignore-rules",
        *definition, "-o", str(OUT / f"b1-{variant}-last.txt"), "-"]
tag = f"b1-{variant}"
(OUT / f"{tag}-argv.json").write_text(json.dumps(args, indent=1), encoding="utf-8")
with open(OUT / f"{tag}-events.jsonl", "wb") as events:
    proc = subprocess.run(consult.invocation_for(args, OUT / f"{tag}-argv.bin"), input=prompt.encode("utf-8"),
                          stdout=events, stderr=subprocess.PIPE, env=consult.shell_environment(), timeout=900)
(OUT / f"{tag}-stderr.log").write_bytes(proc.stderr)
server.shutdown()
result = {"exit": proc.returncode, "token": TOKEN, "server_hits": hits, "server": name, "proxy_port": proxy_port,
          "policy": summary.get("policy"), "allowed": summary.get("allowed_servers"),
          "evidence_dir_files": sorted(p.name for p in EVIDENCE_DIR.iterdir())}
(OUT / f"{tag}-result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
print(json.dumps(result))
