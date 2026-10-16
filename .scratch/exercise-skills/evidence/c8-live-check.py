"""C8 live check (plan claim C8, Live): attach mode with no Codex at all — the stub `codex` (evals/_harness/stub) stands in
for every Codex command, so zero `codex exec` or real Codex calls are made. Real parts: the listener table and its
owners, the supervisor (AttachSupervisor), the port-substituted browser guard and the real-definition check (real
Chrome and the pinned chrome-devtools-mcp), the reproductions.

    python -I -B .scratch/exercise-skills/evidence/c8-live-check.py <output json>

Test targets (plan "Test targets (disposable)", attach-mode live fixture): the fixture project D:\\tmp\\ui-exercise-fixture
(a backend with a seeded SQLite file on 127.0.0.1:18090, a static frontend on 127.0.0.1:18091 whose /api proxies to the
sentinel 127.0.0.1:18081, a ::1 variant on [::1]:18092 and an IPv4 variant on 127.0.0.1:18093), started by this script from the fixture with `python -I` as
the "user's" servers; the sentinel logs every hit under D:\\tmp\\ui-sentinel; target root D:\\tmp\\ui-exercise-targets;
scratch D:\\tmp\\c8-base and D:\\tmp\\c8-work. Every path must be absent and every port free before the run, else it stops.

A  attach to 18090/18091: attach-owners -> prepare -> attach-start (the supervisor's handles to the servers) -> guard
   (real: port-substituted guard, then the uncached real-definition check) -> the negative control (in-process: the real
   definition with a widened allowlist fails the free-port item with a net::ERR_* class) -> run (stub; a curl
   command_execution event) -> collect (tripwire) -> repro (the backend's users through the frontend; the frontend's
   /api proxy reaches the sentinel: the disclosure is true, not a guard failure) -> finish; the servers survive with
   their identity and still own their ports.
B  a second process on [::1]:18090 beside the backend: attach-owners refuses.
C  the ::1 variant [::1]:18092: attach-owners -> prepare -> attach-start -> guard (real). Measured: the guard fails
   closed (chrome-devtools-mcp 1.10.1 cannot construct the URLPattern of http://[::1]:<port>/*; a node probe
   records it).
D  an IPv4 variant 127.0.0.1:18093: D1 guard ran, finish; D2 prepare -> attach-start -> guard (cache hit, the
   real-definition check again) -> run (stub, slow) -> the variant is swapped for another process mid-run ->
   the supervisor stops Codex and the exercise.
Then: the started servers are ended by identity (this script started them), no process created after the baseline is
left, D:\\codex\\config.toml's hash is unchanged, every path created is removed and the guard cache entries this run
added are removed.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/ask/scripts"
CLI = SCRIPTS / "consult.py"
STUB = REPO / "evals/_harness/stub"
FIXTURE, TARGETS, SENTINEL_DIR = Path(r"D:\tmp\ui-exercise-fixture"), Path(r"D:\tmp\ui-exercise-targets"), Path(r"D:\tmp\ui-sentinel")
BASE, WORK = Path(r"D:\tmp\c8-base"), Path(r"D:\tmp\c8-work")
CONFIG_TOML = Path(r"D:\codex\config.toml")
PORTS = {"backend": 18090, "frontend": 18091, "sentinel": 18081, "variant": 18092, "variant4": 18093}
sys.path.insert(0, str(SCRIPTS))
import browser  # noqa: E402
import winjob  # noqa: E402

BACKEND = r'''"""Attach-mode fixture backend: a JSON API over a seeded SQLite file (standard library only)."""
import json, sqlite3, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB = Path(__file__).with_name("data.sqlite")
HOST, PORT = sys.argv[1], int(sys.argv[2])


class Api(BaseHTTPRequestHandler):
    def reply(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:18091")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/users":
            with sqlite3.connect(DB) as db:
                return self.reply(200, [row[0] for row in db.execute("select email from users")])
        self.reply(200, {"service": "attach demo backend"})

    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    address_family = __import__("socket").AF_INET6 if ":" in HOST else __import__("socket").AF_INET


Server((HOST, PORT), Api).serve_forever()
'''

FRONTEND = r'''"""Attach-mode fixture frontend: static pages, and /api proxied to the sentinel 127.0.0.1:18081."""
import sys, urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT = sys.argv[1], int(sys.argv[2])
ROOT = Path(__file__).resolve().parent / "pages"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            with urllib.request.urlopen("http://127.0.0.1:18081" + self.path, timeout=5) as answer:  # the dev proxy
                body = answer.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    address_family = __import__("socket").AF_INET6 if ":" in HOST else __import__("socket").AF_INET


Server((HOST, PORT), Handler).serve_forever()
'''

INDEX = '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Attach demo</title></head>
<body>
<h1>Attach demo</h1>
<button id="load">Load users</button>
<ul id="users"></ul>
<script>
document.getElementById("load").addEventListener("click", async () => {
  const users = await (await fetch("http://127.0.0.1:18090/api/users")).json();
  document.getElementById("users").innerHTML = users.map((u) => "<li>" + u + "</li>").join("");
});
</script>
</body>
</html>
'''

SENTINEL = r'''"""Sentinel 127.0.0.1:18081: logs every hit."""
import sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
LOG = sys.argv[1]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        with open(LOG, "a", encoding="utf-8") as log:
            log.write(f"{time.time():.3f} {self.client_address[0]} {self.path}\n")
        body = b"<!doctype html><title>sentinel</title><p>sentinel reached</p>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 18081), Handler).serve_forever()
'''

LISTEN = r'''"""A second process on a port (helper): binds the given address and accepts."""
import socket, sys, time
host, port = sys.argv[1], int(sys.argv[2])
sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
if ":" in host:
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
sock.bind((host, port))
sock.listen(8)
print("listening", flush=True)
while True:
    time.sleep(3600)
'''

URLPATTERN_PROBE = r"""for (const p of [String.raw`http://[::1]:18092/*`, String.raw`http://[\:\:1]:18092/*`,
                 String.raw`http://127.0.0.1:18092/*`]) {
  try { new URLPattern(p); console.log("ok " + p); } catch (e) { console.log("throws " + p + ": " + e.message); }
}
"""

REPLY = {"claims": [{"category": "ux", "statement": "The Load users button gives no feedback while loading.", "steps": [],
                     "expected": "A loading state", "actual": "Nothing until the list appears", "viewport": None,
                     "evidence": [], "confidence": "medium", "in_scope": True}],
         "out_of_scope": [], "coverage": {"pages": ["/"], "flows": ["load users"], "viewports": ["1280x720"]}}
CURL = {"type": "item.completed", "item": {"id": "item_c1", "type": "command_execution",
                                            "command": "curl -s http://127.0.0.1:18090/api/users",
                                            "aggregated_output": "", "exit_code": 0, "status": "completed"}}

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


def handles_to(holder_pid, pids):
    """{pid: [granted access]} of the process handles `holder_pid` holds to `pids` (its handle table)."""
    holder = _k32.OpenProcess(0x400 | 0x40, False, holder_pid)
    if not holder:
        return {"error": ctypes.get_last_error()}
    try:
        size = 1 << 16
        while True:
            buffer, needed = ctypes.create_string_buffer(size), wintypes.ULONG()
            status = _nt.NtQueryInformationProcess(holder, 51, buffer, size, ctypes.byref(needed)) & 0xFFFFFFFF
            if status == 0:
                break
            if status != 0xC0000004 or size > 1 << 24:
                return {"error": hex(status)}
            size *= 4
        found = {}
        for index in range(struct.unpack_from("<Q", buffer.raw, 0)[0]):
            value, _, _, granted = struct.unpack_from("<QQQI", buffer.raw, 16 + index * 40)
            duplicate = wintypes.HANDLE()
            if not _k32.DuplicateHandle(holder, value, _k32.GetCurrentProcess(), ctypes.byref(duplicate), 0, False, 2):
                continue
            try:
                pid = _k32.GetProcessId(duplicate)
            finally:
                _k32.CloseHandle(duplicate)
            if pid in pids:
                found.setdefault(str(pid), []).append(hex(granted))
        return found
    finally:
        _k32.CloseHandle(holder)


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def processes():
    found = {}
    for pid, parent, image in winjob.processes():
        created = winjob.creation_time(pid)
        if created is not None:
            found[(pid, created)] = (parent, image)
    return found


def new_alive(before):
    now, me = processes(), winjob.creation_time(os.getpid())
    left = []
    for (pid, created), (parent, image) in now.items():
        if (pid, created) in before or pid == os.getpid() or created < me:
            continue
        line = (winjob.command_line(pid) or "")
        left.append({"pid": pid, "image": winjob.image_path(pid) or image, "parent": parent,
                     "headless_chrome": image.lower() == "chrome.exe" and ("--headless" in line or "--user-data-dir" in line),
                     "mcp_node": image.lower() == "node.exe" and "chrome-devtools-mcp" in line,
                     "names_the_run": any(r in line.casefold() for r in (str(TARGETS).casefold(), str(BASE).casefold()))})
    return left


def consult_which():
    import consult
    return consult.which


def bindable(port):
    import socket
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).exists() else None


def main(output):
    log = {"started_at": time.time(), "steps": [], "precheck": {}}
    created_paths = [FIXTURE, TARGETS, SENTINEL_DIR, BASE, WORK]
    existing = [str(p) for p in created_paths if os.path.lexists(p)]
    busy = [(a, p, pid) for a, p, pid in winjob.tcp_listeners() if p in PORTS.values()]
    log["precheck"] = {"existing_paths": existing, "busy_ports": busy}
    if existing or busy:
        Path(output).write_text(json.dumps(log, indent=1), encoding="utf-8")
        raise SystemExit(f"precheck failed (nothing created): existing {existing}, busy {busy}")
    log["config_toml_sha256_before"] = sha256(CONFIG_TOML)
    cache = browser.guard_cache_directory()
    cache_before = set(os.listdir(cache)) if cache.exists() else set()
    baseline = processes()
    log["baseline_processes"] = len(baseline)
    records, home = WORK / "records", WORK / "home"
    for directory in (TARGETS, BASE, records, home, SENTINEL_DIR):
        directory.mkdir(parents=True)
    write(FIXTURE / "README.md", "# Attach demo (C8 live fixture)\n")
    write(FIXTURE / "backend/server.py", BACKEND)
    write(FIXTURE / "frontend/server.py", FRONTEND)
    write(FIXTURE / "frontend/pages/index.html", INDEX)
    write(WORK / "sentinel.py", SENTINEL)
    write(WORK / "listen.py", LISTEN)
    import sqlite3
    db = sqlite3.connect(FIXTURE / "backend/data.sqlite")
    try:
        with db:
            db.execute("create table users (email text)")
            db.execute("insert into users values ('ada@example.invalid')")
    finally:
        db.close()  # an open connection kept the fixture's file locked until exit in the first runs
    seed_hash = sha256(FIXTURE / "backend/data.sqlite")

    def scenario(**exec_):
        write(TARGETS / ".stub/scenario.json", json.dumps({"records": str(records), "for_attach_targets": True,
                                                           "exec": exec_}))
    scenario(reply=REPLY, events=[CURL])
    started = []

    def start(argv, cwd):
        process = subprocess.Popen([sys.executable, "-I", *map(str, argv)], cwd=str(cwd), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=0x200 | 0x08000000)
        identity = {"pid": process.pid, "created": winjob.creation_time(process.pid)}
        started.append((process, identity))
        return identity

    def wait_port(port, host="127.0.0.1"):
        deadline = time.time() + 20
        while time.time() < deadline:
            if any(p == port and (a == host or host == "any") for a, p, _ in winjob.tcp_listeners()):
                return True
            time.sleep(0.2)
        return False

    def end(identity):
        return winjob.terminate_verified(identity["pid"], identity["created"])

    env = {**os.environ, "CODEX_HOME": str(home / ".codex"), "PYTHONDONTWRITEBYTECODE": "1",
           "PATH": os.pathsep.join([str(STUB), os.environ["PATH"]])}

    def cli(*args, timeout=1200, background=False):
        began = time.time()
        if background:
            return subprocess.Popen([sys.executable, "-B", str(CLI), *map(str, args)], env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        result = subprocess.run([sys.executable, "-B", str(CLI), *map(str, args)], env=env, capture_output=True,
                                text=True, encoding="utf-8", timeout=timeout)
        try:
            value = json.loads(result.stdout)
        except ValueError:
            value = {"stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}
        log["steps"].append({"call": str(args[0]), "seconds": round(time.time() - began, 1), "state": value.get("state")})
        print(args[0], value.get("state"), flush=True)
        return value

    def owners(app):
        return cli("attach-owners", write(WORK / f"attach-{time.monotonic_ns()}.json",
                                          json.dumps({"project": str(FIXTURE), "app": app})))

    def prepare(app, found, name):
        request = {"interaction": "exercise", "kind": "ui", "mode": "attach", "project": str(FIXTURE),
                   "prompt": "Exercise type: UI exercise.\nC8 live check (stub codex).",
                   "models": [{"model": None, "effort": "medium"}],
                   "target_root": {"path": str(TARGETS), "confirmed_by_user": True}, "app": app, "headed": False,
                   "scope": "", "target_name": name, "attach": {"chosen_by_user": True, "owners": found["owners"]}}
        return cli("prepare", write(WORK / f"request-{name}.json", json.dumps(request)), "--base", BASE)

    def status(directory):
        try:
            return json.loads((Path(directory) / "supervisor.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    try:
        sentinel = start([WORK / "sentinel.py", SENTINEL_DIR / "hits.log"], WORK)
        backend = start(["backend/server.py", "127.0.0.1", PORTS["backend"]], FIXTURE)
        frontend = start(["frontend/server.py", "127.0.0.1", PORTS["frontend"]], FIXTURE)
        log["servers_listening"] = [wait_port(PORTS["sentinel"]), wait_port(PORTS["backend"]), wait_port(PORTS["frontend"])]
        log["fixture_servers"] = {"backend": backend, "frontend": frontend, "sentinel": sentinel}

        # --- A: attach to the backend and the frontend ---
        app = [f"127.0.0.1:{PORTS['backend']}", f"127.0.0.1:{PORTS['frontend']}"]
        found = owners(app)
        log["A_owners"] = found
        ready = prepare(app, found, "attach-a")
        directory = Path(ready["directory"])
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        target = Path(plan["summary"]["target"])
        log["A_prepared"] = {"state": ready["state"], "summary_mode": plan["summary"].get("mode"),
                             "attached": plan["summary"].get("attached"), "target_listing": sorted(os.listdir(target)),
                             "record_copy": json.loads((directory / "target.json").read_text("utf-8")).get("copy")}
        attached = cli("attach-start", directory)
        log["A_attach_start"] = attached
        supervisor = json.loads((directory / "supervisor-process.json").read_text(encoding="utf-8"))
        log["A_supervisor_handles_to_servers"] = handles_to(supervisor["pid"], {backend["pid"], frontend["pid"]})
        log["A_supervisor_state"] = {k: status(directory).get(k) for k in ("state", "owner_access", "apps", "polls")}
        guarded = cli("guard", directory, timeout=3600)
        log["A_guard"] = guarded
        record = json.loads((directory / "guard.json").read_text(encoding="utf-8")) if (directory / "guard.json").exists() else {}
        log["A_guard_record"] = {k: record.get(k) for k in ("source", "mode", "substitution", "real_check", "items")}
        log["A_servers_alive_after_guard"] = [winjob.alive(backend["pid"], backend["created"]),
                                              winjob.alive(frontend["pid"], frontend["created"])]
        # Negative control (in-process): the real definition with a widened allowlist.
        import consult
        import attach
        import exercise
        original = exercise._template

        def widened(spec, node, entry):
            template = original(spec, node, entry)
            return {**template, "args": [*template["args"], "--allowedUrlPattern=http://127.0.0.1:*/*"]}
        exercise._template = widened
        try:
            control = attach.real_check(consult, directory, plan)
        finally:
            exercise._template = original
        log["A_negative_control"] = {"passed": control["passed"],
                                     "failing": [i for i in control["items"] if not i["ok"]],
                                     "items": [i["item"] for i in control["items"]]}
        log["A_run"] = cli("run", directory)
        log["A_wait"] = cli("wait", directory, "--seconds", "30")
        collected = cli("collect", directory)
        log["A_collect"] = {"state": collected.get("state"), "run": collected.get("runs", [{}])[0].get("state"),
                            "attach": collected.get("attach"), "guard": collected.get("guard")}
        argv = json.loads((records / "exec-argv.json").read_text(encoding="utf-8"))
        log["A_codex_cwd_is_the_empty_target"] = {"-C": argv[argv.index("-C") + 1], "target": target.as_posix(),
                                                  "target_listing_after_run": sorted(os.listdir(target)),
                                                  "project_in_argv": str(FIXTURE).casefold() in json.dumps(argv).casefold()
                                                  or FIXTURE.as_posix().casefold() in json.dumps(argv).casefold()}
        write(WORK / "repro-1.json", json.dumps({"claim": "C1", "steps": [
            {"action": "navigate", "url": f"http://127.0.0.1:{PORTS['frontend']}/"},
            {"action": "click", "element": {"role": "button", "name": "Load users"}},
            {"action": "wait_for", "text": "ada@example.invalid"}]}))
        repro1 = cli("repro", directory, WORK / "repro-1.json")
        log["A_repro_users"] = {"state": repro1.get("state"), "steps": [s.get("status") for s in repro1.get("steps", [])]}
        hits_before = (SENTINEL_DIR / "hits.log").read_text("utf-8").splitlines() if (SENTINEL_DIR / "hits.log").exists() else []
        write(WORK / "repro-2.json", json.dumps({"claim": "C1", "steps": [
            {"action": "navigate", "url": f"http://127.0.0.1:{PORTS['frontend']}/api/ping"},
            {"action": "wait_for", "text": "sentinel reached"}]}))
        repro2 = cli("repro", directory, WORK / "repro-2.json")
        hits_after = (SENTINEL_DIR / "hits.log").read_text("utf-8").splitlines() if (SENTINEL_DIR / "hits.log").exists() else []
        log["A_repro_api_proxy"] = {"state": repro2.get("state"), "steps": [s.get("status") for s in repro2.get("steps", [])],
                                    "sentinel_hits_before": len(hits_before), "sentinel_hits_after": len(hits_after),
                                    "new_hits": hits_after[len(hits_before):]}
        finished = cli("finish", directory)
        log["A_finish"] = {"state": finished.get("state"), "ended": finished.get("ended")}
        time.sleep(1)
        listeners = {p: pid for _, p, pid in winjob.tcp_listeners() if p in (PORTS["backend"], PORTS["frontend"])}
        log["A_servers_after_finish"] = {
            "backend_alive_same_identity": winjob.alive(backend["pid"], backend["created"]),
            "frontend_alive_same_identity": winjob.alive(frontend["pid"], frontend["created"]),
            "port_owners": listeners, "expected": {PORTS["backend"]: backend["pid"], PORTS["frontend"]: frontend["pid"]},
            "supervisor_alive": winjob.alive(supervisor["pid"], supervisor["created"]),
            "run_directory_left": directory.exists(), "targets_left": sorted(os.listdir(TARGETS)),
            "proxy_port_bindable": bindable(plan["browser"]["proxy_port"])}

        # --- B: a second process on ::1 at the backend's port ---
        helper = start([WORK / "listen.py", "::1", PORTS["backend"]], WORK)
        wait_port(PORTS["backend"], "::1")
        log["B_second_listener_refused"] = owners([f"127.0.0.1:{PORTS['backend']}"])
        log["B_helper_ended"] = end(helper)

        # --- C: the ::1 variant (measured: chrome-devtools-mcp 1.10.1 cannot take an [::1] allowlist pattern) ---
        variant = start(["frontend/server.py", "::1", PORTS["variant"]], FIXTURE)
        log["C_variant_listening"] = wait_port(PORTS["variant"], "::1")
        app_v6 = [f"[::1]:{PORTS['variant']}"]
        found = owners(app_v6)
        log["C_owners"] = {"state": found.get("state"), "attached": found.get("attached"), "reason": found.get("reason")}
        ready = prepare(app_v6, found, "attach-c")
        directory = Path(ready["directory"])
        log["C_attach_start"] = cli("attach-start", directory).get("state")
        sentinel_before = len(records.joinpath("exec.sentinel").read_text("utf-8").splitlines())
        guarded = cli("guard", directory, timeout=3600)
        log["C_guard"] = {"state": guarded.get("state"), "reason": guarded.get("reason"),
                          "failing": [i["item"] for i in (guarded.get("guard") or {}).get("failing", [])],
                          "target_removed": guarded.get("target_removed"), "ended": guarded.get("ended"),
                          "run_directory_left": directory.exists(),
                          "codex_calls_during": len(records.joinpath("exec.sentinel").read_text("utf-8").splitlines())
                          - sentinel_before}
        probe = write(WORK / "urlpattern.mjs", URLPATTERN_PROBE)
        node = browser.node_executable(consult_which())
        log["C_urlpattern_probe"] = subprocess.run([str(node), str(probe)], capture_output=True, text=True,
                                                   timeout=60).stdout.splitlines()
        log["C_variant_alive_same_identity"] = winjob.alive(variant["pid"], variant["created"])
        log["C_variant_ended"] = end(variant)

        # --- D: an IPv4 variant; D1 guard ran, D2 cache hit + real check, then its owner is swapped mid-run ---
        variant = start(["frontend/server.py", "127.0.0.1", PORTS["variant4"]], FIXTURE)
        wait_port(PORTS["variant4"])
        app_d = [f"127.0.0.1:{PORTS['variant4']}"]
        found = owners(app_d)
        ready = prepare(app_d, found, "attach-d1")
        directory = Path(ready["directory"])
        log["D1_attach_start"] = cli("attach-start", directory).get("state")
        guarded = cli("guard", directory, timeout=3600)
        log["D1_guard"] = {"state": guarded.get("state"), "source": (guarded.get("guard") or {}).get("source"),
                           "reason": guarded.get("reason")}
        log["D1_finish"] = cli("finish", directory).get("state")
        found = owners(app_d)
        ready = prepare(app_d, found, "attach-d2")
        directory = Path(ready["directory"])
        log["D_attach_start"] = cli("attach-start", directory).get("state")
        guarded = cli("guard", directory, timeout=3600)
        record = json.loads((directory / "guard.json").read_text(encoding="utf-8")) if (directory / "guard.json").exists() else {}
        log["D_guard"] = {"state": guarded.get("state"), "source": (guarded.get("guard") or {}).get("source"),
                          "real_check": record.get("real_check"), "reason": guarded.get("reason")}
        scenario(mode="slow-active", duration_s=90, event_every_s=0.5)
        (records / "exec-finished").unlink(missing_ok=True)
        running = cli("run", directory, background=True)
        deadline = time.time() + 120
        while time.time() < deadline and not ((directory / "0" / "pid").exists() and (records / "exec-argv.json").exists()):
            time.sleep(0.3)
        time.sleep(2)
        log["D_variant_ended"] = end(variant)
        swapped_at = time.time()
        replacement = start(["frontend/server.py", "127.0.0.1", PORTS["variant4"]], FIXTURE)
        wait_port(PORTS["variant4"])
        while time.time() < swapped_at + 120 and status(directory).get("state") not in ("owner_changed", "stop_unconfirmed",
                                                                                         "end_unconfirmed"):
            time.sleep(0.2)
        current = status(directory)
        out, err = running.communicate(timeout=300)
        changed = current.get("changed") or {}
        log["D_swap"] = {"state": current.get("state"),
                         "detected_after_s": round(changed["at"] - swapped_at, 2) if "at" in changed else None,
                         "reason": changed.get("reason"), "codex": (changed.get("codex") or {}).get("state"),
                         "removal": (changed.get("removal") or {}).get("state"),
                         "stub_ran_to_its_end": (records / "exec-finished").exists(),
                         "replacement_alive": winjob.alive(replacement["pid"], replacement["created"])}
        try:
            log["D_run"] = json.loads(out)
        except ValueError:
            log["D_run"] = {"stdout": out[-500:].decode("utf-8", "replace"), "stderr": err[-500:].decode("utf-8", "replace")}
        collected = cli("collect", directory)
        log["D_collect"] = {"state": collected.get("state"), "run": collected.get("runs", [{}])[0].get("state"),
                            "attach": collected.get("attach"), "target_removed": collected.get("target_removed")}
        log["D_run_directory_left"] = directory.exists()
        log["exec_sentinel_lines"] = len((records / "exec.sentinel").read_text("utf-8").splitlines())
        log["violations"] = (records / "violations.log").read_text("utf-8") if (records / "violations.log").exists() else ""
        log["fixture_survived"] = {"backend": winjob.alive(backend["pid"], backend["created"]),
                                   "frontend": winjob.alive(frontend["pid"], frontend["created"]),
                                   "data_changed_allowed": sha256(FIXTURE / "backend/data.sqlite") != seed_hash}
    finally:
        # This script started every server: end them by identity, then check what is left.
        log["servers_ended"] = [{"pid": identity["pid"], "result": end(identity)} for _, identity in started]
        for process, _ in started:
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                pass
            for stream in (process.stdout, process.stderr):
                stream.close()
        time.sleep(2)
        left = new_alive(baseline)
        log["processes_created_after_baseline_still_alive"] = left
        log["headless_chrome_or_mcp_node_left"] = [p for p in left if p["headless_chrome"] or p["mcp_node"]]
        log["config_toml_sha256_after"] = sha256(CONFIG_TOML)
        log["config_toml_unchanged"] = log["config_toml_sha256_after"] == log["config_toml_sha256_before"]
        added = (set(os.listdir(cache)) if cache.exists() else set()) - cache_before
        for name in added:
            os.unlink(cache / name)
        log["guard_cache_entries_added_and_removed"] = sorted(added)
        log["targets_left_before_cleanup"] = sorted(os.listdir(TARGETS)) if TARGETS.exists() else None
        for path in created_paths:
            for _ in range(20):  # a just-ended server's file can stay locked for a moment
                shutil.rmtree(path, ignore_errors=True)
                if not os.path.lexists(path):
                    break
                time.sleep(0.5)
        log["created_paths_left"] = [str(p) for p in created_paths if os.path.lexists(p)]
        Path(output).write_text(json.dumps(log, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: log.get(k) for k in ("A_servers_after_finish", "D_swap", "headless_chrome_or_mcp_node_left",
                                               "config_toml_unchanged", "created_paths_left")}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1])
