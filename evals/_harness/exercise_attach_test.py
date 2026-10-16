"""Attach mode (plan `.scratch/exercise-skills/plan.md` claim C8, ticket 08: I14, I15, I16's script side, I1/I3 with an
empty disposable directory, I5-I7 with substituted ports, I8's supervisor parts and I12's states for attach mode,
I13's eval fake, U7-U10, R6-4, R6-5, AT-1..AT-10).

Offline; never calls a real Codex service and never starts Chrome. The "user's" dev servers are real processes this
test starts itself (a small Python HTTP listener); every process is ended only by its identity (PID + creation time).
Layers:
- AttachRulesTest: the listener-table rule on real listeners (one owner per port, loopback only, the closed forwarder
  list by image name, a second process on ::1 / 127.0.0.2, wildcards; hosts other than 127.0.0.1 refused with
  the fixed sentence, D-2026-10-16b), plus rows Windows cannot produce on demand
  (PID 4, an unreadable owner, an IPv4-mapped address) as given tables; request validation; the tripwire; the
  port-substitution diff; the fingerprint's mode.
- AttachCliTest: the public CLI with the stub Codex (Seam 1 as exercise_app_test): attach-owners, prepare (an empty
  target, nothing started), attach-start (the supervisor's handles to the attached servers carry exactly
  SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION), guard (the real guard code with `Checks.run` and the
  real-definition check substituted in-process, plan I13), run, collect (tripwire), finish; owner changes, the
  supervisor's death (U10), the bounds and stop; the attached servers survive every one with their identity.
- RealCheckTest: the real-definition check (attach.real_check through the CLI guard) with the browser server replaced
  in-process by a fake MCP server that applies `--allowedUrlPattern` like chrome-devtools-mcp 1.10.1; the negative
  control widens the allowlist and fails on the free-port item with the proxy layer's net::ERR_* class.
- AttachFakeTest: the eval fake (I13) covers attach mode through the CLI on a non-Windows platform.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exercise_app_test as app_base  # noqa: E402  (helpers only; its tests are not collected here)
import exercise_platform_test as platform_base  # noqa: E402
import exercise_run_test as base  # noqa: E402

sys.path.insert(0, str(base.SCRIPTS))
if sys.platform == "win32":
    import attach  # noqa: E402
    import browser  # noqa: E402
    import guard  # noqa: E402

created_at, alive, kill, wait_until = app_base.created_at, app_base.alive, app_base.kill, app_base.wait_until
TOKEN = "supersecretvalue1234567890"
FACTS = {"node": "C:/fake/node.exe", "node_version": "v24.12.0", "manifest_sha256": "m" * 64,
         "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome_version": "154.0.8037.98",
         "codex_version": "codex-cli 0.159.3", "chrome_policy_sha256": "p" * 64}
HOST_REFUSED = ("Attach mode takes 127.0.0.1 only: the allowlist of chrome-devtools-mcp does not support [::1], so bind your "
                "dev server to 127.0.0.1.")  # D-2026-10-16b, written here literally
OWNER_ACCESS = 0x100000 | 0x1000  # SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, written here literally
REPLY = {"claims": [], "out_of_scope": [], "coverage": {"pages": ["/"], "flows": [], "viewports": ["1280x720"]}}

# The "user's" dev server: python -I user_server.py <host:port> ... [--token=...]; answers every request with 200.
USER_SERVER = r'''
import socket, sys, threading, time
def serve(sock):
    while True:
        try:
            connection, _ = sock.accept()
        except OSError:
            return
        try:
            connection.settimeout(2)
            connection.recv(4096)
            connection.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok")
        except OSError:
            pass
        finally:
            connection.close()
for spec in [a for a in sys.argv[1:] if not a.startswith("--")]:
    host, port = spec.rsplit(":", 1)
    host = host.strip("[]")
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    if family == socket.AF_INET6:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    sock.bind((host, int(port)))
    sock.listen(16)
    threading.Thread(target=serve, args=(sock,), daemon=True).start()
print("listening", flush=True)
while True:
    time.sleep(3600)
'''

# A stand-in for chrome-devtools-mcp 1.10.1 for the real-definition check: navigation obeys --allowedUrlPattern
# (http://<host>:<port or *>/*) with the allowlist's own refusal text (P5); an allowed URL goes direct when its
# host:port is on the proxy bypass list (a TCP connect decides loaded or net::ERR_CONNECTION_REFUSED), else through
# the closed proxy (net::ERR_PROXY_CONNECTION_FAILED). isolatedContext pages obey the same rules.
CHECK_MCP = r'''
import json, os, socket, sys
from urllib.parse import urlsplit
notes, args = sys.argv[1], sys.argv[2:]
patterns = [a.split("=", 1)[1] for a in args if a.startswith("--allowedUrlPattern=")]
bypass = next(a.split("=", 2)[2] for a in args if a.startswith("--chromeArg=--proxy-bypass-list=")).split(";")
pages, calls = {1: "about:blank"}, open(os.path.join(notes, f"check-calls-{os.getpid()}.jsonl"), "a", encoding="utf-8")
with open(os.path.join(notes, f"check-server-{os.getpid()}.json"), "w", encoding="utf-8") as f:
    json.dump({"pid": os.getpid(), "args": args}, f)

def allowed(url):
    parts = urlsplit(url)
    for pattern in patterns:
        p = urlsplit(pattern[:-1] if pattern.endswith("*") else pattern)
        port = pattern.split("://", 1)[1].split("/", 1)[0].rsplit(":", 1)[1]
        if parts.scheme == p.scheme and parts.hostname == p.hostname and (port == "*" or str(parts.port) == port):
            return True
    return False

def go(url):
    if not allowed(url):
        return True, f"Unable to navigate in the selected page: Navigation to {url} is blocked by blocklist/allowlist rules."
    netloc = urlsplit(url).netloc
    if netloc in bypass:
        host = urlsplit(url).hostname
        try:
            socket.create_connection((host, urlsplit(url).port), timeout=3).close()
            return False, f"Successfully navigated to {url}."
        except OSError:
            return True, f"Unable to navigate in the selected page: net::ERR_CONNECTION_REFUSED at {url}"
    return True, f"Unable to navigate in the selected page: net::ERR_PROXY_CONNECTION_FAILED at {url}"

def listing():
    return "## Pages\n" + "\n".join(f"{n}: {u}" for n, u in sorted(pages.items()))

TOOLS = ["navigate_page", "new_page", "list_pages", "select_page", "close_page", "take_screenshot", "take_snapshot",
         "click", "hover", "fill", "fill_form", "type_text", "press_key", "drag", "handle_dialog", "wait_for",
         "resize_page", "emulate", "list_console_messages", "get_console_message", "list_network_requests",
         "get_network_request", "get_css_styles", "lighthouse_audit"]
for raw in sys.stdin.buffer:
    message = json.loads(raw)
    if "id" not in message:
        continue
    method = message.get("method")
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "chrome_devtools", "version": "1.10.1"}}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "inputSchema": {"type": "object"}} for n in TOOLS]}
    elif method == "tools/call":
        name, arguments = message["params"]["name"], message["params"]["arguments"]
        calls.write(json.dumps({"name": name, "arguments": arguments}) + "\n")
        calls.flush()
        if name == "list_pages":
            error, text = False, listing()
        elif name == "navigate_page":
            error, text = go(arguments["url"])
            if not error:
                pages[arguments.get("pageId", 1)] = arguments["url"]
        elif name == "new_page":
            error, text = go(arguments["url"])
            pages[max(pages) + 1] = arguments["url"] if not error else "about:blank"
        elif name == "close_page":
            pages.pop(arguments.get("pageId"), None)
            error, text = False, listing()
        else:
            error, text = True, "unknown tool " + name
        result = {"content": [{"type": "text", "text": text}], "isError": error}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
    sys.stdout.flush()
'''

if sys.platform == "win32":
    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _nt = ctypes.WinDLL("ntdll")
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.GetCurrentProcess.restype = wintypes.HANDLE
    _k32.DuplicateHandle.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.HANDLE),
                                     wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.GetProcessId.argtypes = [wintypes.HANDLE]
    _k32.GetProcessId.restype = wintypes.DWORD
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _nt.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                              ctypes.POINTER(wintypes.ULONG)]


def process_handles_to(holder_pid, pids):
    """{target pid: [granted access, ...]} of the process handles `holder_pid` holds to any of `pids` (its handle
    table, NtQueryInformationProcess class 51; each handle duplicated into this test to read its process id)."""
    holder = _k32.OpenProcess(0x400 | 0x40, False, holder_pid)  # PROCESS_QUERY_INFORMATION | PROCESS_DUP_HANDLE
    if not holder:
        raise OSError(f"cannot open PID {holder_pid} ({ctypes.get_last_error()})")
    try:
        size = 1 << 16
        while True:
            buffer, needed = ctypes.create_string_buffer(size), wintypes.ULONG()
            status = _nt.NtQueryInformationProcess(holder, 51, buffer, size, ctypes.byref(needed)) & 0xFFFFFFFF
            if status == 0:
                break
            if status != 0xC0000004 or size > 1 << 24:
                raise OSError(f"handle query failed {status:x}")
            size *= 4
        import struct
        count = struct.unpack_from("<Q", buffer.raw, 0)[0]
        found = {}
        for index in range(count):
            value, _, _, granted = struct.unpack_from("<QQQI", buffer.raw, 16 + index * 40)
            duplicate = wintypes.HANDLE()
            if not _k32.DuplicateHandle(holder, value, _k32.GetCurrentProcess(), ctypes.byref(duplicate), 0, False, 2):
                continue
            try:
                pid = _k32.GetProcessId(duplicate)
            finally:
                _k32.CloseHandle(duplicate)
            if pid in pids:
                found.setdefault(pid, []).append(granted)
        return found
    finally:
        _k32.CloseHandle(holder)


def guard_seam(notes, attached_ports, real_ok=True, cache_facts=None):
    """In-process seams of a `guard` CLI call (plan I13): the real guard code (BOOTSTRAP replaced
    require_current_pass, so guard is reloaded) with fixed dependency facts, `Checks.run` replaced by a run that holds
    the guard's app ports with the real holder and records them, and the real-definition check recorded and answered."""
    return (
        "import importlib, json, os, time, guard, attach, winjob\n"
        "importlib.reload(guard)\n"
        f"guard.dependencies = lambda cli, cwd, codex_cwd, state_dir=None: {json.dumps(cache_facts or FACTS)}\n"
        f"_notes, _attached = {str(notes)!r}, {json.dumps(sorted(attached_ports))}\n"
        "def _note(value):\n"
        "    with open(os.path.join(_notes, 'guard-notes.jsonl'), 'a', encoding='utf-8') as f:\n"
        "        f.write(json.dumps(value) + '\\n')\n"
        "def _run(self, job_prefix='ask-codex-guard'):\n"
        "    held = guard.hold_app_ports(self.app)\n"
        "    try:\n"
        "        owners = sorted({pid for a, p, pid in winjob.tcp_listeners() if p in _attached})\n"
        "        _note({'checks_app': self.app, 'args': self.definition['args'], 'attached_owners': owners})\n"
        "    finally:\n"
        "        for _, sock in held:\n"
        "            sock.close()\n"
        "    return [{'item': 'seam', 'ok': True, 'detail': ''}]\n"
        "guard.Checks.run = _run\n"
        "def _real(cli, directory, plan):\n"
        "    status = json.load(open(os.path.join(directory, 'supervisor.json'), encoding='utf-8'))\n"
        "    _note({'real_check': True, 'supervisor_state': status['state'], 'at': time.time()})\n"
        f"    if {bool(real_ok)!r}:\n"
        "        return {'passed': True, 'items': [{'item': 'seam', 'ok': True, 'detail': ''}]}\n"
        "    return {'passed': False, 'items': [{'item': 'free-loopback-port-refused-by-the-allowlist', 'ok': False,\n"
        "            'detail': 'http://127.0.0.1:9/: net::ERR_PROXY_CONNECTION_FAILED: seam'}]}\n"
        "attach.real_check = _real\n")


def timing(**values):
    return "import supervisor, attach\nsupervisor.TIMING.update(" + json.dumps(values) + ")\n"


@unittest.skipUnless(sys.platform == "win32", "the exercise platform layer is Windows only (plan I13)")
class ServersBase(app_base.AppTestBase):
    """AppTestBase plus the "user's" servers this test starts itself (never through the exercise)."""

    def setUp(self):
        super().setUp()
        self.server_script = base.write(self.root / "user_server.py", USER_SERVER)
        self.servers = []
        self.addCleanup(self.close_servers)

    def start_server(self, *specs, executable=None, extra=()):
        process = subprocess.Popen([executable or sys.executable, "-I", str(self.server_script), *specs, *extra],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                                   creationflags=0x200)
        self.servers.append(process)
        identity = (process.pid, created_at(process.pid))
        self.identities.append(identity)
        line = process.stdout.readline()
        if b"listening" not in line:
            raise AssertionError(f"the user's server did not start: {line!r} {process.stderr.read()!r}")
        return identity

    def close_servers(self):
        self.end_leftovers()
        for process in self.servers:
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                pass
            for stream in (process.stdout, process.stderr):
                stream.close()

    def forwarder(self, name):
        """A copy of this Python under another image name (with its DLLs and a pyvenv.cfg naming the real home)."""
        folder = self.root / "forwarders" / name.replace(".exe", "")
        folder.mkdir(parents=True)
        home = Path(sys.executable).parent
        shutil.copy(sys.executable, folder / name)
        for dll in home.glob("*.dll"):
            shutil.copy(dll, folder / dll.name)
        (folder / "pyvenv.cfg").write_text(f"home = {home}\n", encoding="utf-8")
        return folder / name


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class AttachRulesTest(ServersBase):
    """I14's listener-table rule, validation, tripwire, substitution and fingerprint (in-process)."""

    def test_one_loopback_owner_is_confirmed_with_its_identity_and_a_redacted_command_line(self):
        port = app_base.free_port()
        pid, created = self.start_server(f"127.0.0.1:{port}", extra=(f"--token={TOKEN}",))
        [entry] = attach.examine([f"127.0.0.1:{port}"])
        self.assertEqual(entry["problems"], [], entry)
        owner = entry["owner"]
        self.assertEqual((owner["pid"], owner["created"]), (pid, created))
        self.assertEqual(owner["name"].lower(), "python.exe")
        self.assertIn("user_server.py", owner["command_line"])
        self.assertNotIn(TOKEN, owner["command_line"], "I11: the owner's command line is redacted")
        self.assertIn("[REDACTED]", owner["command_line"])
        problems, owners = attach.confirm([f"127.0.0.1:{port}"], {port: {"pid": pid, "created": created}})
        self.assertEqual(problems, [])
        self.assertEqual(owners[0]["pid"], pid)
        # The same PID with another creation time is not the confirmed process.
        problems, _ = attach.confirm([f"127.0.0.1:{port}"], {port: {"pid": pid, "created": created + 1}})
        self.assertTrue(any("another creation time" in p for p in problems), problems)
        # One process on both loopback addresses of one port is one owner (attached as 127.0.0.1).
        both = app_base.free_port()
        pid2, _ = self.start_server(f"127.0.0.1:{both}", f"[::1]:{both}")
        [entry] = attach.examine([f"127.0.0.1:{both}"])
        self.assertEqual(entry["problems"], [], entry)
        self.assertEqual(entry["owner"]["pid"], pid2)

    def test_no_listener_a_wildcard_and_a_second_process_on_another_loopback_address_refuse(self):
        free = app_base.free_port()
        [entry] = attach.examine([f"127.0.0.1:{free}"])
        self.assertTrue(any("nothing listens" in p for p in entry["problems"]), entry)
        for spec in ("0.0.0.0", "[::]"):
            with self.subTest(wildcard=spec):
                port = app_base.free_port()
                self.start_server(f"{spec}:{port}")
                [entry] = attach.examine([f"127.0.0.1:{port}"])
                self.assertTrue(any("wildcard" in p for p in entry["problems"]), entry)
        for other in ("[::1]", "127.0.0.2"):
            with self.subTest(second=other):
                port = app_base.free_port()
                self.start_server(f"127.0.0.1:{port}")
                self.start_server(f"{other}:{port}")
                [entry] = attach.examine([f"127.0.0.1:{port}"])
                self.assertTrue(any("more than one process" in p for p in entry["problems"]), entry)
                self.assertIsNone(entry["owner"])
        # The attached host itself must be listened on: a server bound only to ::1 is not on 127.0.0.1.
        port = app_base.free_port()
        self.start_server(f"[::1]:{port}")
        [entry] = attach.examine([f"127.0.0.1:{port}"])
        self.assertTrue(any(f"nothing listens on 127.0.0.1:{port} itself" in p for p in entry["problems"]), entry)

    def test_every_entry_of_the_closed_forwarder_list_refuses_by_its_image_name(self):
        self.assertEqual(sorted(attach.FORWARDERS), sorted(["wslrelay.exe", "com.docker.backend.exe", "vpnkit.exe",
                                                             "com.docker.proxy.exe", "svchost.exe"]))
        for name in ("wslrelay.exe", "com.docker.backend.exe", "com.docker.proxy.exe", "vpnkit.exe", "svchost.exe"):
            with self.subTest(forwarder=name):
                port = app_base.free_port()
                pid, _ = self.start_server(f"127.0.0.1:{port}", executable=self.forwarder(name))
                [entry] = attach.examine([f"127.0.0.1:{port}"])
                self.assertEqual(entry["owner"]["name"].lower(), name)
                self.assertTrue(any("port forwarder" in p for p in entry["problems"]), entry)

    def test_system_an_unreadable_owner_and_an_ipv4_mapped_binding_refuse(self):
        # Rows Windows does not produce on demand, given as the table: PID 4 (System / http.sys), an owner that cannot
        # be read (a PID that does not run), an IPv4-mapped address. (Measured on this host: a dual-stack socket
        # bound to ::ffff:127.0.0.1 is listed in the IPv4 table as 127.0.0.1, i.e. as an IPv4 loopback binding.)
        port = 18777
        running = {pid for pid, _, _ in __import__("winjob").processes()}
        dead = next(p for p in range(4_000_000, 4_100_000, 4) if p not in running)
        for rows, expected in (([("127.0.0.1", port, 4)], "PID 4"), ([("127.0.0.1", port, 0)], "PID 0"),
                               ([("127.0.0.1", port, dead)], "cannot be read"),
                               ([("::ffff:127.0.0.1", port, os.getpid())], "IPv4-mapped"),
                               ([("192.168.1.5", port, os.getpid())], "not a loopback address")):
            with self.subTest(rows=rows):
                [entry] = attach.examine([f"127.0.0.1:{port}"], listeners=rows)
                self.assertTrue(any(expected in p for p in entry["problems"]), entry)

    def test_attach_requests_are_validated_before_anything(self):
        import exercise
        owners = [{"port": 18090, "pid": 1234, "created": 5678}]
        good = {"interaction": "exercise", "kind": "ui", "mode": "attach", "project": r"D:\p", "prompt": "x",
                "models": [{"model": None, "effort": "medium"}], "target_root": {"path": r"D:\t", "confirmed_by_user": True},
                "app": ["127.0.0.1:18090"], "headed": False, "scope": "",
                "attach": {"chosen_by_user": True, "owners": owners}}
        spec = exercise.validate(good)
        self.assertEqual((spec["mode"], spec["confirmed"]), ("attach", {18090: {"pid": 1234, "created": 5678}}))
        cases = [
            ("no explicit choice", {"attach": {"owners": owners}}, "explicit choice"),
            ("choice false", {"attach": {"chosen_by_user": False, "owners": owners}}, "explicit choice"),
            ("attach fields missing", {"attach": None}, "explicit choice"),
            ("localhost", {"app": ["localhost:18090"]}, HOST_REFUSED),
            ("[::1] (D-2026-10-16b)", {"app": ["[::1]:18090"]}, HOST_REFUSED),
            ("127.0.0.1 beside [::1]", {"app": ["127.0.0.1:18090", "[::1]:18091"], "attach": {"chosen_by_user": True,
                                        "owners": [*owners, {"port": 18091, "pid": 2, "created": 2}]}}, HOST_REFUSED),
            ("https", {"app": ["https://127.0.0.1:18090"]}, "https, wss"),
            ("wss", {"app": ["wss://127.0.0.1:18090"]}, "https, wss"),
            ("port 80", {"app": ["127.0.0.1:80"], "attach": {"chosen_by_user": True,
                                                            "owners": [{"port": 80, "pid": 1, "created": 1}]}}, "80 and 443"),
            ("port 443", {"app": ["127.0.0.1:443"], "attach": {"chosen_by_user": True,
                                                          "owners": [{"port": 443, "pid": 1, "created": 1}]}}, "80 and 443"),
            ("non-loopback", {"app": ["192.168.1.5:18090"]}, "not loopback"),
            ("commands", {"commands": {"start": [{"argv": ["python", "x.py"]}]}}, "takes no commands"),
            ("env files", {"env_files": [".env"]}, "takes no env_files"),
            ("no owners", {"attach": {"chosen_by_user": True}}, "attach.owners"),
            ("owner of another port", {"attach": {"chosen_by_user": True,
                                                  "owners": [{"port": 18091, "pid": 1, "created": 1}]}}, "exactly one"),
            ("owner without creation time", {"attach": {"chosen_by_user": True,
                                                        "owners": [{"port": 18090, "pid": 1}]}}, "created"),
            ("unknown attach field", {"attach": {"chosen_by_user": True, "owners": owners, "auto": True}}, "Unknown"),
            ("unknown mode", {"mode": "live"}, "copy\" or \"attach"),
            ("attach fields in copy mode", {"mode": "copy"}, "attach mode"),
        ]
        for label, change, expected in cases:
            with self.subTest(case=label):
                request = {**good, **change}
                if change.get("attach", 0) is None:
                    del request["attach"]
                with self.assertRaises(ValueError) as caught:
                    exercise.validate(request)
                self.assertIn(expected.lower(), str(caught.exception).lower())

    def test_the_tripwire_lists_shell_commands_naming_an_attached_port_or_an_http_client(self):
        import base64
        encoded = base64.b64encode("Invoke-RestMethod http://127.0.0.1:18090/api".encode("utf-16-le")).decode()
        commands = [
            ("c1", "curl -s http://127.0.0.1:18090/api/users", True),
            ("c2", '"C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command '
                   '"Invoke-WebRequest -UseBasicParsing http://[::1]:18091/"', True),
            ("c3", f"powershell.exe -NoProfile -EncodedCommand {encoded}", True),
            ("c4", "python -c \"import urllib.request; urllib.request.urlopen('http://example.com')\"", True),
            ("c5", "node -e \"fetch('http://127.0.0.1:9/x')\"", True),
            ("c6", "wget -qO- http://localhost:5173", True),
            ("c7", "powershell -Command \"(New-Object Net.WebClient).DownloadString('http://x')\"", True),
            ("c8", "powershell -Command \"irm http://127.0.0.1:3000\"", True),
            ("c9", "Get-Content backend\\config.json | Select-String 18091", True),
            ("c10", "rg -n TODO src", False),
            ("c11", "Get-ChildItem -Recurse frontend", False),
            ("c12", "type notes.txt 180900 118090", False),
            ("c13", f"curl -H 'Authorization: Bearer {TOKEN}' http://127.0.0.1:18090/", True),
        ]
        events = self.root / "events.jsonl"
        lines = []
        for key, command, _ in commands:
            item = {"id": key, "type": "command_execution", "command": command, "status": "in_progress"}
            lines.append(json.dumps({"type": "item.started", "item": item}))
            lines.append(json.dumps({"type": "item.completed", "item": {**item, "status": "completed"}}))
        lines.append(json.dumps({"type": "item.completed", "item": {"id": "m", "type": "agent_message", "text": "curl"}}))
        lines.append("not json")
        events.write_text("\n".join(lines), encoding="utf-8")
        found = attach.tripwire(events, ["127.0.0.1:18090", "127.0.0.1:18091"])
        listed = [entry["command"] for entry in found]
        expected = [command for _, command, hit in commands if hit]
        self.assertEqual(len(listed), len(expected), found)
        self.assertNotIn(TOKEN, json.dumps(found), "I11: listed commands are redacted")
        names = {entry["command"][:20]: entry["names"] for entry in found}
        self.assertIn("port 18090", names["curl -s http://127.0"])
        self.assertIn("curl", names["curl -s http://127.0"])
        self.assertTrue(any("Invoke-RestMethod" in entry["names"] for entry in found), "inside -EncodedCommand")
        self.assertTrue(any("Invoke-WebRequest" in e["names"] and "port 18091" in e["names"] for e in found))
        for hit in ("python HTTP", "node HTTP", "wget", "Net.WebClient"):
            self.assertTrue(any(hit in entry["names"] for entry in found), hit)
        self.assertFalse(any("rg -n TODO" in c or "Get-ChildItem" in c or "180900" in c for c in listed))
        self.assertEqual(attach.tripwire(self.root / "missing.jsonl", ["127.0.0.1:18090"]), [])

    def test_the_substitution_differs_only_in_port_numbers_and_the_fingerprint_names_the_mode(self):
        app = ["127.0.0.1:18090", "127.0.0.1:18091"]
        node, entry = Path(r"C:\Program Files\nodejs\node.exe"), Path(r"C:\state\cdt\entry.js")
        real = browser.template(app, False, node, entry)
        mapping = {18090: 51001, 18091: 51002}
        guarded = browser.template(guard.substitute_ports(app, mapping), False, node, entry)
        guard.check_substitution(real, guarded, mapping)  # only the port numbers differ
        self.assertNotIn("18090", json.dumps(guarded))
        for label, other in (
                ("another host", browser.template(["127.0.0.2:51001", "127.0.0.1:51002"], False, node, entry)),
                ("headed", browser.template(guard.substitute_ports(app, mapping), True, node, entry)),
                ("an attached port left", browser.template(["127.0.0.1:18090", "127.0.0.1:51002"], False, node, entry)),
                ("another port than mapped", browser.template(["127.0.0.1:51009", "127.0.0.1:51002"], False, node, entry)),
                ("an extra argument", {**guarded, "args": [*guarded["args"], "--allowedUrlPattern=http://127.0.0.1:*/*"]})):
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    guard.check_substitution(real, other, mapping)
        with self.assertRaises(ValueError):
            guard.check_substitution(real, browser.template(guard.substitute_ports(app, {18090: 18091, 18091: 51002}),
                                                            False, node, entry), {18090: 18091, 18091: 51002})
        # The attach-mode fingerprint keeps the attached ports and adds the mode; guard ports are not in it.
        self.assertNotEqual(guard.fingerprint(real, FACTS, "attach"), guard.fingerprint(real, FACTS))
        self.assertEqual(guard.fingerprint(real, FACTS), guard.fingerprint(real, dict(FACTS)), "copy mode unchanged")
        other_port = browser.template(["127.0.0.1:18092", "127.0.0.1:18091"], False, node, entry)
        self.assertNotEqual(guard.fingerprint(other_port, FACTS, "attach"), guard.fingerprint(real, FACTS, "attach"))

    def test_navigation_classes(self):
        self.assertEqual(attach.navigation_class(True, "Unable to navigate in the selected page: Navigation to "
                                                       "http://x/ is blocked by blocklist/allowlist rules."), "allowlist")
        self.assertEqual(attach.navigation_class(True, "net::ERR_EMPTY_RESPONSE at http://x/"), "net::ERR_EMPTY_RESPONSE")
        self.assertEqual(attach.navigation_class(False, "Successfully navigated to http://x/."), "loaded")
        self.assertEqual(attach.navigation_class(None, "timeout"), "no answer")
        self.assertEqual(attach.navigation_class(True, "Error: something"), "error")

    def test_the_attach_module_reads_no_environment_variable(self):
        import ast
        source = (base.SCRIPTS / "attach.py").read_text(encoding="utf-8")
        reads = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute) and
                 n.attr in ("environ", "getenv", "environb", "putenv")]
        self.assertEqual(reads, [])
        self.assertNotIn("getenv", source)


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class AttachCliTest(ServersBase):
    """Ticket 08 acceptance through the public CLI with the stub Codex and real "user's" servers."""

    def setUp(self):
        super().setUp()
        self.app = [f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{self.ports[1]}"]
        self.backend = self.start_server(self.app[0], extra=(f"--token={TOKEN}",))
        self.frontend = self.start_server(self.app[1])
        self.guard_notes = self.root / "guard-notes"
        self.guard_notes.mkdir()
        self.attach_scenario({"exec": {"reply": REPLY}})
        self.request = {"interaction": "exercise", "kind": "ui", "mode": "attach", "project": str(self.project),
                        "prompt": "Exercise type: UI exercise.\nExercise the app and report what you find.",
                        "models": [{"model": "gpt-6-sol", "effort": "high"}],
                        "target_root": {"path": str(self.targets), "confirmed_by_user": True},
                        "app": self.app, "headed": False, "scope": "", "target_name": "attach-target"}

    def attach_scenario(self, value):
        # The attach-mode target is empty: the stub finds its scenario beside it (for_attach_targets).
        base.write(self.targets / ".stub/scenario.json",
                   json.dumps({"records": str(self.records), "for_attach_targets": True, **value}))

    def owners(self, app=None):
        path = base.write(self.requests / f"attach-{time.monotonic_ns()}.json",
                          json.dumps({"project": str(self.project), "app": app or self.app}))
        return self.call("attach-owners", path)

    def prepare(self, **change):
        found = self.owners(change.get("app"))
        self.assertEqual(found["state"], "ready", found)
        request = {**self.request, "attach": {"chosen_by_user": True, "owners": found["owners"]}, **change}
        path = base.write(self.requests / "request.json", json.dumps(request))
        ready = self.call("prepare", path, "--base", self.base)
        self.assertEqual(ready["state"], "prepared", ready)
        directory = Path(ready["directory"])
        return directory, json.loads((directory / "plan.json").read_text("utf-8"))

    def attached(self, code=None, **change):
        directory, plan = self.prepare(**change)
        result = self.call("attach-start", directory, code=code)
        if (directory / "supervisor-process.json").exists():
            identity = self.supervisor(directory)
            self.identities.append((identity["pid"], identity["created"]))
        self.assertEqual(result["state"], "attached", result)
        return directory, plan, result

    def guarded(self, directory, real_ok=True):
        result = self.call("guard", directory, code=guard_seam(self.guard_notes, self.ports, real_ok))
        return result

    def guard_notes_list(self):
        path = self.guard_notes / "guard-notes.jsonl"
        return [json.loads(line) for line in path.read_text("utf-8").splitlines()] if path.exists() else []

    def assert_servers_untouched(self):
        for pid, created in (self.backend, self.frontend):
            self.assertTrue(alive(pid, created), f"the user's server PID {pid} runs with its identity")
        listening = {p: pid for _, p, pid in __import__("winjob").tcp_listeners() if p in self.ports}
        self.assertEqual(listening, {self.ports[0]: self.backend[0], self.ports[1]: self.frontend[0]})

    def assert_gone(self, directory):
        self.assertEqual(os.listdir(self.targets), [".stub"], "the target and its siblings are gone")
        self.assertFalse(os.path.lexists(directory), "the run directory is gone")

    # --- ticket 08 acceptance ---

    def test_a_whole_attached_exercise_copies_nothing_starts_nothing_and_leaves_the_servers_as_they_were(self):
        self.attach_scenario({"exec": {"reply": REPLY, "events": [
            {"type": "item.completed", "item": {"id": "x1", "type": "command_execution",
                                                "command": f"curl -s http://{self.app[0]}/api/users", "status": "completed"}},
            {"type": "item.completed", "item": {"id": "x2", "type": "command_execution", "command": "rg -n TODO src",
                                                "status": "completed"}}]}})
        found = self.owners()
        self.assertEqual(found["state"], "ready", found)
        self.assertEqual([(o["port"], o["pid"]) for o in found["owners"]],
                         [(self.ports[0], self.backend[0]), (self.ports[1], self.frontend[0])])
        self.assertNotIn(TOKEN, json.dumps(found), "the owner's command line is redacted (AT-9)")
        self.assertEqual(found["attached"], [f"python.exe:{self.backend[0]}", f"python.exe:{self.frontend[0]}"])
        directory, plan = self.prepare()
        target = Path(plan["summary"]["target"])
        # No copy: a new empty disposable directory under the confirmed root (I1, I3), holding only evidence.
        self.assertEqual(os.listdir(target), ["evidence"])
        self.assertEqual(json.loads((directory / "target.json").read_text("utf-8"))["copy"], "none")
        self.assertEqual(plan["summary"]["mode"], "attach")
        self.assertEqual(plan["summary"]["attached"], found["attached"])
        self.assertNotIn(TOKEN, (directory / "plan.json").read_text("utf-8"))
        self.assertFalse(base.related(target, self.project))
        # No app process: nothing was started (no supervisor, no app job) before attach-start.
        self.assertFalse((directory / "supervisor-process.json").exists())
        started = self.call("attach-start", directory)
        identity = self.supervisor(directory)
        self.identities.append((identity["pid"], identity["created"]))
        self.assertEqual(started["state"], "attached", started)
        status = self.status(directory)
        self.assertEqual((status["state"], status["apps"], status["job"] if "job" in status else None),
                         ("attached", [], None), "no app process, no app job")
        self.assertEqual(status["owner_access"], OWNER_ACCESS)
        # The supervisor's handles to the attached servers carry exactly SYNCHRONIZE | QUERY_LIMITED (no terminate).
        handles = process_handles_to(identity["pid"], {self.backend[0], self.frontend[0]})
        self.assertEqual(sorted(handles), sorted([self.backend[0], self.frontend[0]]), handles)
        self.assertTrue(all(OWNER_ACCESS in access and all(not a & ~OWNER_ACCESS for a in access)
                            for access in handles.values()), handles)  # transient query handles are subsets
        self.assertFalse(app_base.bindable(plan["browser"]["proxy_port"]), "the supervisor holds the proxy port")
        # The guard runs after attach-start, on guard-owned ports only; the real-definition check follows it.
        guarded = self.guarded(directory)
        self.assertEqual(guarded["state"], "guard_passed", guarded)
        self.assertEqual(guarded["guard"]["source"], "ran")
        notes = self.guard_notes_list()
        [checks] = [n for n in notes if "checks_app" in n]
        held = {int(origin.rsplit(":", 1)[1]) for origin in checks["checks_app"]}
        self.assertFalse(held & set(self.ports), "the guard never binds an attached port")
        self.assertEqual(checks["attached_owners"], sorted([self.backend[0], self.frontend[0]]),
                         "the attached ports kept their owners while the guard held its own")
        self.assertFalse(any(str(p) in arg for arg in checks["args"] for p in self.ports))
        [real] = [n for n in notes if n.get("real_check")]
        self.assertEqual(real["supervisor_state"], "attached", "the real-definition check runs after attach-start")
        record = json.loads((directory / "guard.json").read_text("utf-8"))
        self.assertEqual(record["mode"], "attach")
        self.assertEqual(sorted(record["substitution"]), sorted(str(p) for p in self.ports))
        self.assertTrue(record["real_check"]["passed"])
        # Codex works from the empty directory (-C), never the project.
        self.assertEqual(self.call("run", directory)["state"], "finished")
        argv = json.loads((self.records / "exec-argv.json").read_text("utf-8"))
        self.assertEqual(argv[argv.index("-C") + 1], target.as_posix())
        self.assertNotIn(str(self.project), json.dumps(argv))
        self.assertNotIn(self.project.as_posix(), json.dumps(argv))
        [call] = [json.loads(p.read_text("utf-8")) for p in self.exec_calls()]
        self.assertEqual(Path(call["cwd"]).resolve(), target.resolve())
        self.assertEqual(sorted(os.listdir(target)), ["evidence"])
        self.assertEqual((self.records / "violations.log").read_text("utf-8"), "")
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        self.assertEqual(collected["attach"]["attached"], found["attached"])
        [tripped] = collected["attach"]["tripwire"]
        self.assertIn(f"port {self.ports[0]}", tripped["names"])
        self.assertIn("curl", tripped["names"])
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(finished["ended"]["app"]["confirmed"] and finished["ended"]["browser"]["confirmed"])
        self.assertEqual(finished["ended"]["app"]["trees"], [], "no app process to end")
        self.assertTrue(app_base.bindable(plan["browser"]["proxy_port"]), "the proxy is released")
        self.assertFalse(alive(identity["pid"], identity["created"]))
        self.assert_servers_untouched()
        self.assert_gone(directory)

    def test_attach_mode_needs_the_users_choice_and_the_confirmed_owners_and_creates_nothing_otherwise(self):
        found = self.owners()
        cases = [
            ("no explicit choice", {"attach": {"owners": found["owners"]}}, "explicit choice"),
            ("owner restarted", {"attach": {"chosen_by_user": True, "owners": [
                {**found["owners"][0], "pid": found["owners"][0]["pid"] + 4}, found["owners"][1]]}}, "not the confirmed"),
            ("same PID, another creation time", {"attach": {"chosen_by_user": True, "owners": [
                {**found["owners"][0], "created": found["owners"][0]["created"] + 1}, found["owners"][1]]}},
             "another creation time"),
            ("non-loopback host", {"app": ["10.0.0.5:8080"], "attach": {"chosen_by_user": True, "owners": [
                {"port": 8080, "pid": 4, "created": 1}]}}, "not loopback"),
            ("a port nothing listens on", {"app": [self.app[0], f"127.0.0.1:{app_base.free_port()}"]}, "nothing listens"),
            ("install and start commands", {"commands": {"start": [{"argv": ["python", "x.py"]}]}}, "takes no commands"),
            ("an [::1] host (D-2026-10-16b)", {"app": [self.app[0], f"[::1]:{self.ports[1]}"]}, HOST_REFUSED),
        ]
        for label, change, expected in cases:
            with self.subTest(case=label):
                request = {**self.request, "attach": {"chosen_by_user": True, "owners": found["owners"]}, **change}
                if label == "a port nothing listens on":
                    request["attach"] = {"chosen_by_user": True, "owners": [
                        found["owners"][0], {"port": int(change["app"][1].rsplit(":", 1)[1]), "pid": 4, "created": 1}]}
                path = base.write(self.requests / "request.json", json.dumps(request))
                refused = self.call("prepare", path, "--base", self.base)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn(expected.lower(), refused["reason"].lower())
                self.assertEqual(self.runs(), [], "nothing is created")
                self.assertEqual(os.listdir(self.targets), [".stub"])
        v6 = self.owners([f"[::1]:{self.ports[1]}"])
        self.assertEqual(v6["state"], "failed", v6)
        self.assertIn(HOST_REFUSED, v6["reason"], "attach-owners refuses [::1] with the fixed sentence")
        refused = self.owners([self.app[0], f"127.0.0.1:{app_base.free_port()}"])
        self.assertEqual(refused["state"], "refused", refused)
        self.assertIn("nothing listens", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        self.assert_servers_untouched()

    def test_app_start_refuses_in_attach_mode_attach_start_in_copy_mode_and_attach_start_is_never_retried(self):
        directory, plan = self.prepare()
        refused = self.call("app-start", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("attach-start", refused["reason"])
        # The guard comes after attach-start in attach mode (the table is polled while it runs).
        early = self.call("guard", directory, code=guard_seam(self.guard_notes, self.ports))
        self.assertEqual(early["state"], "failed", early)
        self.assertIn("attach-start comes before the guard", early["reason"])
        self.assertEqual(self.call("attach-start", directory)["state"], "attached")
        identity = self.supervisor(directory)
        self.identities.append((identity["pid"], identity["created"]))
        again = self.call("attach-start", directory)
        self.assertEqual(again["state"], "failed", again)
        self.assertIn("never retried", again["reason"])
        run = self.call("run", directory, code=guard_seam(self.guard_notes, self.ports))  # the real pass check
        self.assertEqual(run["state"], "failed", "no Codex without the guard and the real-definition check")
        self.assertIn("No browser guard pass", run["reason"])
        self.assertEqual(self.exec_calls(), [])
        self.assert_servers_untouched()
        self.assertEqual(self.call("collect", directory)["state"], "failed", "collect of the failed run settles it")
        self.assert_gone(directory)
        # Copy mode: attach-start is refused.
        copy_request = {**self.request, "mode": "copy", "app": [f"127.0.0.1:{app_base.free_port()}"],
                        "commands": {"start": [{"argv": [sys.executable, "-c", "0"]}]}, "target_name": "copy-target"}
        path = base.write(self.requests / "copy.json", json.dumps(copy_request))
        ready = self.call("prepare", path, "--base", self.base)
        refused = self.call("attach-start", ready["directory"])
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("attach-mode exercises only", refused["reason"])
        self.assertEqual(self.call("finish", ready["directory"])["state"], "finished")

    def test_a_cache_hit_still_runs_the_real_definition_check_other_guard_ports_hit_and_another_attached_port_misses(self):
        first, _, _ = self.attached(target_name="first")
        self.assertEqual(self.guarded(first)["guard"]["source"], "ran")
        second, _, _ = self.attached(target_name="second")
        result = self.guarded(second)
        self.assertEqual(result["guard"]["source"], "cache", "same attached ports: the pass is reused")
        records = [json.loads((d / "guard.json").read_text("utf-8")) for d in (first, second)]
        self.assertEqual(records[0]["fingerprint"], records[1]["fingerprint"])
        self.assertEqual(len([n for n in self.guard_notes_list() if n.get("real_check")]), 2,
                         "the real-definition check runs on a cache hit too (never cached)")
        self.assertTrue(records[1]["real_check"]["passed"])
        third_port = app_base.free_port()
        third = self.start_server(f"127.0.0.1:{third_port}")
        directory, _, _ = self.attached(target_name="third", app=[self.app[0], f"127.0.0.1:{third_port}"])
        result = self.guarded(directory)
        self.assertEqual(result["guard"]["source"], "ran", "another attached port: another fingerprint")
        self.assertNotEqual(json.loads((directory / "guard.json").read_text("utf-8"))["fingerprint"],
                            records[0]["fingerprint"])
        for d in (first, second, directory):
            self.assertEqual(self.call("finish", d)["state"], "finished")
        self.assertTrue(alive(*third))
        self.assert_servers_untouched()

    def test_a_failing_real_definition_check_ends_the_exercise_and_records_the_failing_item(self):
        directory, plan, _ = self.attached()
        identity = self.supervisor(directory)
        failed = self.guarded(directory, real_ok=False)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("real-definition check", failed["reason"])
        [item] = failed["guard"]["failing"]
        self.assertEqual(item["item"], "free-loopback-port-refused-by-the-allowlist")
        self.assertIn("net::ERR_PROXY_CONNECTION_FAILED", item["detail"])
        self.assertTrue(failed["target_removed"])
        self.assertFalse(alive(identity["pid"], identity["created"]), "the supervisor was ended")
        self.assertTrue(app_base.bindable(plan["browser"]["proxy_port"]))
        self.assert_servers_untouched()
        self.assert_gone(directory)

    def test_an_owner_swap_is_detected_within_5_s_and_stops_codex_and_the_exercise(self):
        self.attach_scenario({"exec": {"mode": "slow-active", "duration_s": 90, "event_every_s": 0.2}})
        directory, plan, _ = self.attached()
        self.assertEqual(self.guarded(directory)["state"], "guard_passed")
        polls = self.status(directory)["polls"]
        wait_until(lambda: self.status(directory)["polls"] >= polls + 2, 10, "the supervisor does not poll every 2 s")
        running = self.background("run", directory)
        try:
            wait_until(lambda: (directory / "0" / "pid").exists() and (self.records / "exec-argv.json").exists(),
                       60, "Codex never started")
            # The user's backend is swapped: the old owner ends, another process takes the port.
            kill(*self.backend)
            killed_at = time.time()
            replacement = self.start_server(self.app[0])
            wait_until(lambda: self.status(directory)["state"] in ("owner_changed", "stop_unconfirmed",
                                                                   "end_unconfirmed"), 60, "the swap was not acted on")
            status = self.status(directory)
            self.assertLess(status["changed"]["at"] - killed_at, 5.0, "detected within 5 s of the swap")
            out, err = running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertEqual(status["state"], "owner_changed", status)
        self.assertIn("changed", status["changed"]["reason"])
        self.assertEqual(status["changed"]["codex"]["state"], "stopped", status)
        self.assertFalse((self.records / "exec-finished").exists(), "Codex was stopped")
        self.assertEqual(status["changed"]["removal"]["state"], "removed")
        self.assertTrue(alive(*replacement), "the new owner is never signalled")
        self.assertTrue(alive(*self.frontend))
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "stopped", collected)
        self.assertEqual(collected["attach"]["supervisor"]["state"], "owner_changed")
        self.assertFalse(directory.exists())
        self.assertEqual(os.listdir(self.targets), [".stub"])

    def test_killing_the_supervisor_stops_codex_and_never_touches_the_attached_servers(self):
        self.attach_scenario({"exec": {"mode": "slow-active", "duration_s": 60, "event_every_s": 0.2}})
        directory, plan, _ = self.attached()
        self.assertEqual(self.guarded(directory)["state"], "guard_passed")
        identity = self.supervisor(directory)
        running = self.background("run", directory)
        try:
            wait_until(lambda: (directory / "0" / "pid").exists() and (self.records / "exec-argv.json").exists(),
                       60, "Codex never started")
            time.sleep(1)
            kill(identity["pid"], identity["created"])
            died = time.monotonic()
            wait_until(lambda: (directory / "0" / "stop-request").exists(), 5, "no stop requested")
            self.assertLess(time.monotonic() - died, 2.5, "the Codex stop starts within 2 s of the death (U10)")
            out, err = running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertIn("supervisor_died", json.loads(out), (out, err))
        self.assertFalse((self.records / "exec-finished").exists())
        self.assert_servers_untouched()
        collected = self.call("collect", directory)
        self.assertIn(collected["runs"][0]["state"], ("stopped", "stop_unconfirmed"), collected)
        if collected["runs"][0]["state"] == "stopped":
            self.assert_gone(directory)
        self.assert_servers_untouched()

    def test_killing_the_supervisor_without_codex_then_finish_leaves_the_servers(self):
        directory, plan, _ = self.attached()
        identity = self.supervisor(directory)
        kill(identity["pid"], identity["created"])
        self.assert_servers_untouched()
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(app_base.bindable(plan["browser"]["proxy_port"]))
        self.assert_servers_untouched()
        self.assert_gone(directory)

    def test_the_lifetime_bounds_and_stop_end_the_exercise_and_never_signal_the_servers(self):
        directory, plan, _ = self.attached(code=timing(bound_after_start=6))
        identity = self.supervisor(directory)
        wait_until(lambda: self.status(directory)["state"] in ("bound_ended", "stop_unconfirmed", "end_unconfirmed"),
                   60, "the bound was not reached")
        status = self.status(directory)
        self.assertEqual(status["state"], "bound_ended", status)
        self.assertEqual(status["bound"]["reason"], "6 h after the attach confirmation")
        self.assertEqual(status["bound"]["removal"]["state"], "removed")
        wait_until(lambda: not alive(identity["pid"], identity["created"]), 15, "the supervisor did not exit")
        self.assertTrue(app_base.bindable(plan["browser"]["proxy_port"]))
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned")
        self.assert_servers_untouched()
        self.assert_gone(directory)
        # 2 h after collect (shortened).
        directory, plan, _ = self.attached(code=timing(bound_after_collect=3), target_name="second")
        self.assertEqual(self.guarded(directory)["state"], "guard_passed")
        self.assertEqual(self.call("run", directory)["state"], "finished")
        self.assertEqual(self.call("collect", directory)["runs"][0]["state"], "completed")
        wait_until(lambda: self.status(directory)["state"] in ("bound_ended", "stop_unconfirmed", "end_unconfirmed"),
                   60, "the bound after collect was not reached")
        self.assertEqual(self.status(directory)["bound"]["reason"], "2 h after collect")
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned")
        self.assert_servers_untouched()
        # stop while Codex runs.
        self.attach_scenario({"exec": {"mode": "slow-active", "duration_s": 60, "event_every_s": 0.2}})
        directory, plan, _ = self.attached(target_name="third")
        self.assertEqual(self.guarded(directory)["state"], "guard_passed")
        running = self.background("run", directory)
        try:
            wait_until(lambda: (directory / "0" / "pid").exists() and (self.records / "exec-argv.json").exists(),
                       60, "Codex never started")
            stopped = self.call("stop", directory)
            running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertEqual(stopped["state"], "stopped", stopped)
        self.assertTrue(stopped["ended"]["app"]["confirmed"] and stopped["target_removed"])
        self.assert_servers_untouched()


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class RealCheckTest(ServersBase):
    """attach.real_check through the CLI guard, with chrome-devtools-mcp replaced in-process by CHECK_MCP."""

    def setUp(self):
        super().setUp()
        self.app = [f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{self.ports[1]}"]
        self.backend = self.start_server(self.app[0])
        self.frontend = self.start_server(self.app[1])
        self.mcp = base.write(self.root / "check_mcp.py", CHECK_MCP)
        self.mcp_notes = self.root / "mcp-notes"
        self.mcp_notes.mkdir()
        base.write(self.targets / ".stub/scenario.json", json.dumps({"records": str(self.records),
                                                                      "for_attach_targets": True,
                                                                      "exec": {"reply": REPLY}}))

    def attached(self):
        path = base.write(self.requests / "attach.json", json.dumps({"project": str(self.project), "app": self.app}))
        found = self.call("attach-owners", path)
        self.assertEqual(found["state"], "ready", found)
        request = {"interaction": "exercise", "kind": "ui", "mode": "attach", "project": str(self.project),
                   "prompt": "Exercise type: UI exercise.", "models": [{"model": None, "effort": "medium"}],
                   "target_root": {"path": str(self.targets), "confirmed_by_user": True}, "app": self.app,
                   "headed": False, "scope": "", "attach": {"chosen_by_user": True, "owners": found["owners"]}}
        ready = self.call("prepare", base.write(self.requests / "request.json", json.dumps(request)), "--base", self.base)
        directory = Path(ready["directory"])
        self.assertEqual(self.call("attach-start", directory)["state"], "attached")
        identity = self.supervisor(directory)
        self.identities.append((identity["pid"], identity["created"]))
        return directory

    def seam(self, widen=False):
        code = guard_seam(self.root, self.ports).replace("attach.real_check = _real\n", "")
        code += ("import winjob, sys, exercise\n"
                 "_start = winjob.start_suspended\n"
                 "def _fake(job, argv, cwd, env, command_line=None):\n"
                 f"    return _start(job, [sys.executable, {str(self.mcp)!r}, {str(self.mcp_notes)!r}, *argv[2:]], cwd, env)\n"
                 "winjob.start_suspended = _fake\n")
        if widen:  # the negative control: the check's session runs the real definition with a widened allowlist
            code += ("_check = attach.real_check\n"
                     "def _widened(cli, directory, plan):\n"
                     "    original = exercise._template\n"
                     "    def template(spec, node, entry):\n"
                     "        t = original(spec, node, entry)\n"
                     "        return {**t, 'args': [*t['args'], '--allowedUrlPattern=http://127.0.0.1:*/*']}\n"
                     "    exercise._template = template\n"
                     "    try:\n"
                     "        return _check(cli, directory, plan)\n"
                     "    finally:\n"
                     "        exercise._template = original\n"
                     "attach.real_check = _widened\n")
        return code

    def test_the_real_definition_check_passes_on_the_allowlists_own_refusals(self):
        directory = self.attached()
        result = self.call("guard", directory, code=self.seam())
        self.assertEqual(result["state"], "guard_passed", result)
        calls = [json.loads(line) for p in self.mcp_notes.glob("check-calls-*.jsonl")
                 for line in p.read_text("utf-8").splitlines()]
        urls = [c["arguments"].get("url") for c in calls if c["name"] in ("navigate_page", "new_page")]
        for origin in self.app:
            self.assertIn(f"http://{origin}/", urls)
        for spelling in (f"localhost:{self.ports[0]}", f"[::1]:{self.ports[0]}", f"127.0.0.2:{self.ports[0]}",
                         f"localhost:{self.ports[1]}", f"[::1]:{self.ports[1]}", f"127.0.0.2:{self.ports[1]}"):
            self.assertIn(f"http://{spelling}/", urls)
        self.assertIn("http://example.com/", urls)
        self.assertTrue(any(c["name"] == "new_page" and c["arguments"].get("isolatedContext") for c in calls))
        [server] = [json.loads(p.read_text("utf-8")) for p in self.mcp_notes.glob("check-server-*.json")]
        self.assertIn(f"--allowedUrlPattern=http://{self.app[0]}/*", server["args"], "the real (attached) definition")
        record = [e for e in json.loads((directory / "target.json").read_text("utf-8"))["entries"]
                  if e.get("purpose", "").startswith("check-")]
        self.assertEqual(sorted(e["purpose"] for e in record), ["check-cwd", "check-profile", "check-temp"])
        self.assertEqual(os.listdir(directory / "repro-jobs"), [], "the check's job was ended and unregistered")
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assertTrue(alive(*self.backend) and alive(*self.frontend))

    def test_the_negative_control_a_widened_allowlist_fails_on_the_free_port_with_the_proxy_layers_error(self):
        directory = self.attached()
        result = self.call("guard", directory, code=self.seam(widen=True))
        self.assertEqual(result["state"], "failed", result)
        failing = {item["item"]: item["detail"] for item in result["guard"]["failing"]}
        self.assertIn("free-loopback-port-refused-by-the-allowlist", failing, failing)
        self.assertIn("net::ERR_PROXY_CONNECTION_FAILED", failing["free-loopback-port-refused-by-the-allowlist"])
        self.assertTrue(result["target_removed"])
        self.assertFalse(directory.exists())
        self.assertTrue(alive(*self.backend) and alive(*self.frontend))


@unittest.skipUnless(sys.platform == "win32", "offline suite of the Windows checkout (the fake itself is portable)")
class AttachFakeTest(unittest.TestCase):
    """I13: the eval fake covers attach mode; production's validation, owner comparison and lifecycle run on it."""

    setUp = platform_base.PlatformLayerTest.setUp
    stage, path_with, call = (platform_base.PlatformLayerTest.stage, platform_base.PlatformLayerTest.path_with,
                              platform_base.PlatformLayerTest.call)
    prepare, runs, violations, exec_count = (platform_base.PlatformLayerTest.prepare, platform_base.PlatformLayerTest.runs,
                                              platform_base.PlatformLayerTest.violations,
                                              platform_base.PlatformLayerTest.exec_count)

    def scenario(self, **fake):
        base.write(self.project / ".stub/scenario.json", json.dumps({
            "records": str(self.records), "exercise_fake": fake,
            "exec": {"reply": REPLY, "events": [{"type": "item.completed", "item": {
                "id": "c1", "type": "command_execution", "command": "curl -s http://127.0.0.1:18090/api",
                "status": "completed"}}]}}))

    def attach_request(self):
        path = base.write(self.requests / "attach.json", json.dumps({"project": str(self.project),
                                                                     "app": ["127.0.0.1:18090", "127.0.0.1:18091"]}))
        found = self.call("attach-owners", path, platform="linux")
        self.assertEqual(found["state"], "ready", found)
        return {**{k: v for k, v in self.request.items() if k != "commands"}, "mode": "attach",
                "app": ["127.0.0.1:18090", "127.0.0.1:18091"], "attach": {"chosen_by_user": True, "owners": found["owners"]}}

    def test_the_fake_runs_an_attached_exercise_through_the_cli(self):
        self.scenario()
        self.path_with(self.stage())
        request = self.attach_request()
        refused = self.prepare({**request, "attach": {"owners": request["attach"]["owners"]}}, platform="linux")
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("explicit choice", refused["reason"])
        ready = self.prepare(request, platform="linux")
        self.assertEqual(ready["state"], "prepared", ready)
        self.assertEqual(ready["summary"]["attached"], ["python.exe:5101", "python.exe:5102"])
        directory = Path(ready["directory"])
        target = Path(ready["summary"]["target"])
        self.assertEqual(os.listdir(target), ["evidence"], "an empty target: nothing copied")
        self.assertEqual(self.call("app-start", directory, platform="linux")["state"], "failed")
        self.assertEqual(self.call("attach-start", directory, platform="linux")["state"], "attached")
        self.assertEqual(self.call("guard", directory, platform="linux")["state"], "guard_passed")
        self.assertEqual(self.call("run", directory, platform="linux")["state"], "finished")
        self.assertEqual(self.call("wait", directory, "--seconds", "5", platform="linux")["state"], "finished")
        collected = self.call("collect", directory, platform="linux")
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        [tripped] = collected["attach"]["tripwire"]
        self.assertIn("port 18090", tripped["names"])
        argv = json.loads((self.records / "exec-argv.json").read_text("utf-8"))
        self.assertEqual(argv[argv.index("-C") + 1], target.as_posix())
        self.assertEqual(self.violations(), "")
        finished = self.call("finish", directory, platform="linux")
        self.assertEqual(finished["state"], "finished", finished)
        self.assertEqual(self.runs(), [], "the stand-in root (with the scenario beside the target) is gone")

    def test_the_fake_refuses_a_changed_owner_and_a_failed_guard_ends_through_production(self):
        self.scenario()
        self.path_with(self.stage())
        request = self.attach_request()
        self.scenario(attach_owners={"18090": {"pid": 7777}})
        changed = self.prepare(request, platform="linux")
        self.assertEqual(changed["state"], "failed", changed)
        self.assertIn("not the confirmed process", changed["reason"])
        self.scenario(attach_owners={"18091": {"image": "C:\\Windows\\System32\\wslrelay.exe"}})
        path = base.write(self.requests / "attach.json", json.dumps({"project": str(self.project),
                                                                     "app": ["127.0.0.1:18090", "127.0.0.1:18091"]}))
        forwarded = self.call("attach-owners", path, platform="linux")
        self.assertEqual(forwarded["state"], "refused", forwarded)
        self.assertIn("forwarder", forwarded["reason"])
        self.scenario(guard="fail")
        ready = self.prepare(request, platform="linux")
        directory = Path(ready["directory"])
        self.assertEqual(self.call("attach-start", directory, platform="linux")["state"], "attached")
        failed = self.call("guard", directory, platform="linux")
        self.assertEqual(failed["state"], "failed", failed)
        self.assertTrue(failed["target_removed"])
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.exec_count(), 0)


def tearDownModule():
    try:
        base.TEST_ROOT.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    unittest.main()
