"""Guards of an exercise (plan `.scratch/exercise-skills/plan.md` claim C3; I5 verification, I7, I8 guard part).

    consult.py guard <run directory>      dependency check, then the browser guard or a cached pass (before any app
                                          process starts); a failure removes the target at once (I12)
    consult.py exercise-deps              dependency check only (for /ask-codex:setup, and for /ask-codex:ui before
                                          its confirmation: it names the tested codex-cli version, N10)

Dependency check: the pinned package install verifies against the committed manifest (install.py); node.exe is
found on the run environment's PATH; Chrome stable is the executable chrome-devtools-mcp's launcher picks with the
MCP's environment, and its file version must be 149 or later.

Fingerprint (I7): SHA-256 over the definition template (per-run values as placeholders `<nonce>`, `<target>`,
`<cwd>`, `<temp>`, `<profile>`, `<proxy port>`; app host:ports and the headed flag kept; node and entry paths inside it), node's
path and version, the manifest's SHA-256, Chrome's executable path and version, the codex-cli version and a hash of
Chrome's enterprise policy keys. A pass is cached in the user-level state directory (`guard-cache/<fingerprint>.json`,
never in a project) and reused for at most 12 hours on an identical fingerprint; on a cache hit the app ports are
checked free again. Each exercise records the pass it relies on in `guard.json` in its run directory; `run`
recomputes the fingerprint and refuses to start Codex unless that record names the same fingerprint and passed
less than 12 hours ago (require_current_pass).

Browser guard (I7, I8): runs before any app process, holds every app port itself (proving each free: no listener on
that port number on any address, then exclusive binds) and its own owned proxy port (a listener that accepts and
closes); creates its own kill-on-close job (winjob; the guard is not a member) and starts I5's definition - the
same template instantiated with the guard's own nonce, `TEMP`, `cwd` and seeded profile siblings (U16), proxy port
and the exercise's target - with node created suspended, assigned, resumed, over stdio, without Codex, in the environment Codex gives
a stdio MCP server (CODEX_DEFAULT_ENV taken from the run environment, then the definition's `env`). Its MCP client
declares Codex 0.159.3's capabilities (mcp_stdio). Every item of I7 is checked and every failing item reported.

Port mapping (C8, attach mode): the checks take the app origins they serve from the definition the caller builds;
`guard_attached` maps each attached port to a guard-owned free port (`substitute_ports`) before the guard's template
is built, proves by a literal diff that only those port numbers differ from the real template (`check_substitution`),
and then runs the real-definition check (attach.real_check) on the attached ports, every exercise and never cached.
The attach-mode fingerprint keeps the attached ports and adds the mode; a pass records the substitution.

Nothing here reads an environment variable to select, skip or substitute anything (I13): the run environment is
read only to build the MCP's environment (as Codex does) and to locate the inherited TEMP the checks watch. Tests
substitute in-process or pass `state_dir`.
"""
import ctypes
from ctypes import wintypes
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import struct
import subprocess
import threading
import time
from urllib.parse import parse_qs, quote, urlsplit

import browser
import install
import mcp_stdio
import target as disposable_target
import winjob

HERE = Path(__file__).resolve().parent
PAGE_DIR = HERE.parent / "guard-page"
CACHE_SECONDS = 12 * 3600
MIN_CHROME_MAJOR = 149
# The codex-cli whose per-tool browser approval probe B1 measured (plan N10, A8); a release reruns B1 to raise it.
TESTED_CODEX_CLI = "codex-cli 0.159.3"
PROBE = "ask-codex-guard"
CHROME_SUFFIX = r"Google\Chrome\Application\chrome.exe"
# chrome-devtools-mcp 1.10.1 (puppeteer, channel stable on Windows): these variables in this order, then fixed
# prefixes; the first existing <prefix>\Google\Chrome\Application\chrome.exe is launched.
CHROME_PREFIX_VARIABLES = ("PROGRAMFILES", "ProgramW6432", "ProgramFiles(x86)", "LOCALAPPDATA")
CHROME_PREFIXES = (r"C:\Program Files", r"C:\Program Files (x86)", r"D:\Program Files", r"D:\Program Files (x86)")
# codex-rs 0.159.3, rmcp-client create_env_for_mcp_server: DEFAULT_ENV_VARS on Windows =
# codex_protocol::shell_environment::WINDOWS_CORE_ENV_VARS, read from Codex's own environment; then the server's
# configured `env` (env_vars is empty, I6). CA-path variables are added only when set (none on the measured host).
CODEX_DEFAULT_ENV = ("PATH", "PATHEXT", "SHELL", "COMSPEC", "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "USERNAME",
                     "USERDOMAIN", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "PROGRAMFILES", "PROGRAMFILES(X86)",
                     "PROGRAMW6432", "PROGRAMDATA", "LOCALAPPDATA", "APPDATA", "TEMP", "TMP", "TMPDIR", "POWERSHELL",
                     "PWSH")
POLICY_PATH = r"SOFTWARE\Policies\Google\Chrome"
SENTINEL_SPELLINGS = ("127.0.0.1", "localhost", "[::1]", "127.0.0.2", "0.0.0.0")
SENTINEL_BINDS = ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1"), (socket.AF_INET, "127.0.0.2"))
EXTERNAL = "https://example.com/"
DOWNLOAD_BODY = b"ask-codex guard download probe\n"
KEEP_CACHEABLE = ("/post", "/post.html", "/prefs.json", "/local-state.json")
FORBIDDEN_SCHEMES = ("file:", "chrome:", "devtools:", "view-source:", "blob:", "filesystem:", "about:")
UNC_TIMEOUT = 40
TOOL_TIMEOUT = 60


def now():
    return time.time()


class GuardFailed(ValueError):
    def __init__(self, items, reason="The browser guard failed"):
        self.items = items
        failing = [item["item"] for item in items if not item["ok"]]
        super().__init__(f"{reason} on {len(failing)} item(s): {', '.join(failing[:12])}"
                         + (" ..." if len(failing) > 12 else "") + "; no app start, no Codex")


# --- dependency facts ---

def _env_get(env, name):
    for key, value in env.items():
        if key.upper() == name.upper():
            return value
    return None


def chrome_executable(env):
    prefixes = []
    for name in CHROME_PREFIX_VARIABLES:
        value = _env_get(env, name)
        if value and value not in prefixes:
            prefixes.append(value)
    for value in CHROME_PREFIXES:
        if value not in prefixes:
            prefixes.append(value)
    for prefix in prefixes:
        candidate = ntpath.join(prefix, CHROME_SUFFIX)
        if os.path.isfile(candidate):
            return candidate
    return None


def file_version(path):
    version = ctypes.WinDLL("version")
    version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    version.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p),
                                       ctypes.POINTER(wintypes.UINT)]
    size = version.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return None
    data = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(path), 0, size, data):
        return None
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if not version.VerQueryValueW(data, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 52:
        return None
    fixed = ctypes.string_at(pointer, 52)
    ms, ls = struct.unpack_from("<II", fixed, 8)
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def _registry_tree(root, path, access):
    import winreg
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | access)
    except OSError:
        return None
    with key:
        values, subkeys, index = {}, {}, 0
        while True:
            try:
                name, value, kind = winreg.EnumValue(key, index)
            except OSError:
                break
            values[name] = [kind, value if isinstance(value, (str, int)) else repr(value)]
            index += 1
        index = 0
        while True:
            try:
                sub = winreg.EnumKey(key, index)
            except OSError:
                break
            subkeys[sub] = _registry_tree(key, sub, access)
            index += 1
    return {"values": values, "keys": subkeys}


def chrome_policy_digest():
    import winreg
    """SHA-256 of every Chrome enterprise policy key and value (machine and user, both registry views)."""
    tree = {}
    for root, label in ((winreg.HKEY_LOCAL_MACHINE, "HKLM"), (winreg.HKEY_CURRENT_USER, "HKCU")):
        for access, view in ((winreg.KEY_WOW64_64KEY, "64"), (winreg.KEY_WOW64_32KEY, "32")):
            tree[f"{label}/{view}"] = _registry_tree(root, POLICY_PATH, access)
    return hashlib.sha256(json.dumps(tree, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest(), tree


def node_version(node, cwd):
    result = subprocess.run([str(node), "--version"], cwd=cwd, capture_output=True, text=True, timeout=30,
                            env={"SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"), "NODE_OPTIONS": ""})
    if result.returncode or not re.fullmatch(r"v\d+\.\d+\.\d+\s*", result.stdout):
        raise ValueError("node --version failed; node is required for exercises")
    return result.stdout.strip()


def codex_version(cli, cwd):
    text = cli.command(["codex", "--version"], cwd).strip()
    if not text or len(text) > 200:
        raise ValueError("codex --version returned no version")
    return text


def mcp_environment(base_env, definition_env):
    """The environment Codex 0.159.3 gives a stdio MCP server: its default variables, then the definition's env."""
    env = {}
    for name in CODEX_DEFAULT_ENV:
        value = _env_get(base_env, name)
        if value is not None:
            env[name] = value
    for name, value in definition_env.items():
        for key in [k for k in env if k.upper() == name.upper()]:
            del env[key]
        env[name] = value
    return env


def dependencies(cli, cwd, codex_cwd, state_dir=None):
    """Facts of the fingerprint; raises ValueError with a clear message when a dependency is missing or too old."""
    manifest_digest = install.verify(state_dir) if state_dir else install.verify_installed()
    node = browser.node_executable(cli.which)
    env = mcp_environment(cli.shell_environment(), {})
    chrome = chrome_executable(env)
    if not chrome:
        raise ValueError("Google Chrome (stable) was not found; install Chrome 149 or later")
    version = file_version(chrome)
    if not version or int(version.split(".")[0]) < MIN_CHROME_MAJOR:
        raise ValueError(f"Chrome stable {MIN_CHROME_MAJOR} or later is required (found {version or 'unknown'} "
                         f"at {chrome})")
    policy, _ = chrome_policy_digest()
    return {"node": browser._posix(node), "node_version": node_version(node, cwd), "manifest_sha256": manifest_digest,
            "chrome": chrome, "chrome_version": version, "codex_version": codex_version(cli, codex_cwd),
            "chrome_policy_sha256": policy}


def fingerprint(template, facts, mode=None):
    """SHA-256 over the template and the facts; an attach-mode exercise adds its mode (C8), so a copy-mode pass is
    never reused for attach mode or the reverse. The copy-mode value is unchanged (no mode key)."""
    value = {"template": template, "facts": facts}
    if mode is not None:
        value["mode"] = mode
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# --- cache ---

def cache_directory(state_dir=None):
    return (Path(state_dir) if state_dir else browser.state_directory()) / "guard-cache"


def cached_pass(state_dir, fp):
    """The cached pass for `fp` if it passed at most 12 hours ago, else None."""
    path = cache_directory(state_dir) / f"{fp}.json"
    try:
        status = os.lstat(path)
    except OSError:
        return None
    if getattr(status, "st_file_attributes", 0) & 0x400 or not stat.S_ISREG(status.st_mode):
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    passed = record.get("passed_at") if isinstance(record, dict) else None
    if record.get("fingerprint") != fp or type(passed) not in (int, float):
        return None
    age = now() - passed
    return record if 0 <= age <= CACHE_SECONDS else None


def store_pass(state_dir, fp, record):
    directory = cache_directory(state_dir)
    directory.mkdir(parents=True, exist_ok=True)
    status = os.lstat(directory)
    if getattr(status, "st_file_attributes", 0) & 0x400:
        raise ValueError("The guard cache directory is a link; not written")
    temporary = directory / f"{fp}.{secrets.token_hex(4)}.tmp"
    temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    temporary.replace(directory / f"{fp}.json")


# --- app ports ---

def substitute_ports(app, mapping):
    """C8: the app origins with attached port numbers replaced by guard-owned ports (only port numbers change)."""
    result = []
    for origin in app:
        host, port = origin.rsplit(":", 1)
        result.append(f"{host}:{mapping.get(int(port), int(port))}")
    return result


PORT_AFTER_COLON = re.compile(r"(?<=:)(\d+)")


def _port_only(real, guarded, mapping):
    """The two strings are equal except for numbers after a ':' that the mapping turns one into the other."""
    a, b = PORT_AFTER_COLON.split(real), PORT_AFTER_COLON.split(guarded)
    if len(a) != len(b):
        return False
    for index, (x, y) in enumerate(zip(a, b)):
        if index % 2 == 0:
            if x != y:
                return False
        elif x != y and mapping.get(int(x)) != int(y):
            return False
    return True


def check_substitution(real, guarded, mapping):
    """C8 (I14, AT-5): a literal diff of the real definition template and the guard's: they may differ only in the
    attached port numbers, each replaced by its guard port, and no attached port may remain in the guard's (it never
    binds or serves one). Raises ValueError naming every other difference (e.g. a changed host)."""
    differences = []

    def walk(x, y, where):
        if type(x) is not type(y):
            differences.append(where)
        elif isinstance(x, dict):
            if set(x) != set(y):
                differences.append(where)
            else:
                for key in x:
                    walk(x[key], y[key], f"{where}.{key}")
        elif isinstance(x, list):
            if len(x) != len(y):
                differences.append(where)
            else:
                for index, (a, b) in enumerate(zip(x, y)):
                    walk(a, b, f"{where}[{index}]")
        elif isinstance(x, str):
            if x != y and not _port_only(x, y, mapping):
                differences.append(where)
        elif x != y:
            differences.append(where)

    walk(real, guarded, "definition")
    text = json.dumps(guarded)
    left = sorted(port for port in mapping if re.search(rf":{port}(?![0-9])", text))
    if set(mapping.values()) & set(mapping):
        differences.append("a guard port equals an attached port")
    if differences or left:
        raise ValueError("The guard's definition differs from the real one in more than the attached port numbers ("
                         + ", ".join(differences + [f"attached port {p} left in the guard's definition" for p in left])
                         + "); refused")


def _addresses(host):
    return {"127.0.0.1": [(socket.AF_INET, "127.0.0.1")], "[::1]": [(socket.AF_INET6, "::1")],
            "localhost": [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]}[host]


def _exclusive(family, address, port):
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.set_inheritable(False)
        sock.bind((address, port))
        sock.listen(64)
        return sock
    except OSError:
        sock.close()
        raise


def hold_app_ports(app):
    """Prove every app port free (no listener on that port number on any address) and bind it exclusively on its
    loopback addresses; returns [(origin, socket)]. Raises ValueError naming the port and the owner."""
    ports = {int(origin.rsplit(":", 1)[1]) for origin in app}
    busy = [(a, p, pid) for a, p, pid in winjob.tcp_listeners() if p in ports]
    if busy:
        raise ValueError("App port(s) in use before any app start: " +
                         ", ".join(f"{a}:{p} (PID {pid})" for a, p, pid in busy))
    held = []
    try:
        for origin in app:
            host, port = origin.rsplit(":", 1)
            for family, address in _addresses(host):
                try:
                    held.append((origin, _exclusive(family, address, int(port))))
                except OSError:
                    raise ValueError(f"The app port {address}:{port} cannot be held by the guard; not free") from None
    except BaseException:
        for _, sock in held:
            sock.close()
        raise
    return held


def ports_free(app):
    """Cache hit: the app ports are checked free again (held for the check, then released)."""
    for _, sock in hold_app_ports(app):
        sock.close()


# --- guard-owned listeners ---

class Recorder:
    def __init__(self):
        self.lock = threading.Condition()
        self.reports, self.app_requests, self.sentinel, self.lan, self.udp = {}, [], [], [], []

    def report(self, ctx, key, value):
        with self.lock:
            self.reports.setdefault(ctx, {}).setdefault(key, []).append(value)
            self.lock.notify_all()

    def wait(self, ctx, key, timeout):
        deadline = time.monotonic() + timeout
        with self.lock:
            while key not in self.reports.get(ctx, {}):
                left = deadline - time.monotonic()
                if left <= 0:
                    return None
                self.lock.wait(left)
            return self.reports[ctx][key]

    def get(self, ctx, key):
        with self.lock:
            return list(self.reports.get(ctx, {}).get(key, []))


class RawListener:
    """Accepts and records every TCP connection (first bytes), then closes it: any arrival is a hit."""

    def __init__(self, binds, port, sink):
        self.sockets, self.sink = [], sink
        for family, address in binds:
            self.sockets.append(_exclusive(family, address, port))
        self.port = port
        for sock in self.sockets:
            threading.Thread(target=self._serve, args=(sock,), daemon=True).start()

    def _serve(self, sock):
        while True:
            try:
                connection, peer = sock.accept()
            except OSError:
                return
            try:
                connection.settimeout(1.5)
                try:
                    first = connection.recv(512)
                except OSError:
                    first = b""
                self.sink.append({"local": sock.getsockname()[0], "peer": str(peer[0]),
                                  "first": first.decode("latin-1")[:300]})
            finally:
                connection.close()

    def close(self):
        for sock in self.sockets:
            sock.close()


class StunListener:
    """UDP listener answering STUN binding requests with a made-up mapped address (a srflx candidate would show)."""

    def __init__(self, family, address, sink):
        self.sock = socket.socket(family, socket.SOCK_DGRAM)
        self.sock.bind((address, 0))
        self.port, self.sink = self.sock.getsockname()[1], sink
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        while True:
            try:
                data, peer = self.sock.recvfrom(2048)
            except OSError:
                return
            self.sink.append({"local": self.sock.getsockname()[0], "peer": str(peer[0]), "bytes": len(data)})
            if len(data) >= 20 and data[:2] == b"\x00\x01":
                attribute = struct.pack(">HHBBH4s", 0x0020, 8, 0, 1, 4242 ^ 0x2112,
                                        bytes(a ^ b for a, b in zip(socket.inet_aton("203.0.113.7"),
                                                                   b"\x21\x12\xa4\x42")))
                try:
                    self.sock.sendto(struct.pack(">HH", 0x0101, len(attribute)) + data[4:20] + attribute, peer)
                except OSError:
                    pass

    def close(self):
        self.sock.close()


def lan_address():
    """A local non-loopback IPv4 interface address (the external stand-in's address)."""
    for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
        address = info[4][0]
        if not address.startswith(("127.", "169.254.", "0.")):
            return address
    return None


class CheckSite:
    """The check page and its routes, served on every app origin from sockets the guard holds."""

    def __init__(self, token, recorder, sentinels, lan, stun):
        self.token, self.recorder = token, recorder
        self.prefix = f"/__ask_codex_guard/{token}"
        self.sentinels, self.lan, self.stun = sentinels, lan, stun
        self.page = (PAGE_DIR / "check.html").read_text(encoding="utf-8")
        self.worker = (PAGE_DIR / "worker.js").read_text(encoding="utf-8")
        self.sw = (PAGE_DIR / "sw.js").read_text(encoding="utf-8")
        self.servers = []

    def url(self, origin, route, ctx=None):
        query = f"?ctx={quote(ctx)}" if ctx is not None else ""
        return f"http://{origin}{self.prefix}{route}{query}"

    def config(self, origin, ctx):
        value = {"ctx": ctx, "base": f"http://{origin}{self.prefix}", "sentinels": self.sentinels, "lan": self.lan,
                 "external": f"{EXTERNAL}?{PROBE}={self.token}", "stun": self.stun,
                 "download": f"{PROBE}-{self.token}-download.bin", "body": f"{PROBE}-body-{self.token}"}
        return json.dumps(value).replace("<", "\\u003c")

    def serve(self, origin, sock):
        site = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def send(self, code, body=b"", kind="text/plain", headers=()):
                self.send_response(code)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(body)))
                # Not for bodies the file-writing items save (get_network_request did not answer for a no-store
                # response body in 1.10.1).
                if not urlsplit(self.path).path.endswith(KEEP_CACHEABLE):
                    self.send_header("Cache-Control", "no-store")
                for name, value in headers:
                    self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def do_GET(self):
                parts = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(parts.query).items()}
                ctx = query.get("ctx", "")
                site.recorder.app_requests.append({"origin": origin, "method": self.command, "path": self.path[:300],
                                                   "host": self.headers.get("Host"),
                                                   "probe_header": self.headers.get("X-Ask-Codex-Guard")})
                if not parts.path.startswith(site.prefix + "/"):
                    return self.send(404, b"not found")
                route = parts.path[len(site.prefix):]
                if route == "/check.html":
                    body = site.page.replace("__CONFIG__", site.config(origin, ctx))
                    return self.send(200, body.encode("utf-8"), "text/html; charset=utf-8")
                if route == "/worker.js":
                    return self.send(200, site.worker.replace("__CONFIG__", site.config(origin, ctx)).encode("utf-8"),
                                     "text/javascript")
                match = re.fullmatch(r"/sw/([^/]+)/sw\.js", route)
                if match:
                    sw_ctx = match.group(1)
                    return self.send(200, site.sw.replace("__CONFIG__", site.config(origin, sw_ctx)).encode("utf-8"),
                                     "text/javascript")
                if route == "/r":
                    site.recorder.report(ctx, query.get("k", ""), query.get("v", ""))
                    return self.send(200, b"ok")
                if route == "/redirect307":
                    return self.send(307, b"", headers=(("Location", query.get("to", "/")),))
                if route == "/download":
                    return self.send(200, DOWNLOAD_BODY, "application/octet-stream",
                                     (("Content-Disposition",
                                       f'attachment; filename="{PROBE}-{site.token}-download.bin"'),))
                if route == "/post":
                    length = int(self.headers.get("Content-Length") or 0)
                    if length:
                        self.rfile.read(min(length, 65536))
                    return self.send(200, b"ok")
                if route in ("/prefs.json", "/local-state.json"):
                    # App-served JSON that would select a direct connection if Chrome ever read it as its profile.
                    body = {"proxy": {"mode": "direct", "server": "", "bypass_list": ""},
                            "ask_codex_guard": site.token}
                    return self.send(200, json.dumps(body).encode("utf-8"), "application/json")
                if route == "/tall.html":
                    body = "<!doctype html><title>tall</title><div style='height:40000px;background:" \
                           "linear-gradient(#fff,#888)'>tall</div>"
                    return self.send(200, body.encode("utf-8"), "text/html")
                if route == "/large.html":
                    body = "<!doctype html><title>large</title><ul>" + "".join(
                        f"<li><button>item {i}</button></li>" for i in range(6000)) + "</ul>"
                    return self.send(200, body.encode("utf-8"), "text/html")
                if route == "/post.html":
                    body = "<!doctype html><title>post</title><script>fetch('post', {method: 'POST', body: " \
                           f"'{PROBE}-body-{site.token}'}})</script>"
                    return self.send(200, body.encode("utf-8"), "text/html")
                if route == "/blank.html":
                    return self.send(200, b"<!doctype html><title>blank</title><p>blank</p>", "text/html")
                return self.send(404, b"not found")

            do_POST = do_GET
            do_HEAD = do_GET

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(sock.getsockname()[:2], Handler, bind_and_activate=False)
        server.socket.close()
        server.socket = sock
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
        self.servers.append(server)

    def close(self):
        for server in self.servers:
            server.shutdown()
            server.server_close()


# --- file-system observation ---

def _lexists(path):
    try:
        os.lstat(path)
        return True
    except OSError:
        return False


def _names(directory):
    try:
        return set(os.listdir(directory))
    except OSError:
        return set()


def _find(directory, stem, recursive):
    """Entries under `directory` whose name contains `stem` (links reported, never followed)."""
    found = []
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return found
    for entry in entries:
        if stem in entry.name:
            found.append(entry.path)
        if recursive:
            status = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(status.st_mode) and not getattr(status, "st_file_attributes", 0) & 0x400:
                found += _find(entry.path, stem, True)
    return found


def _digest_tree(directory):
    result = {}
    for root, dirs, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            result[os.path.relpath(path, directory)] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for name in dirs:
            result[os.path.relpath(os.path.join(root, name), directory) + "/"] = "dir"
    return result


def _regular_without_streams(path):
    status = os.lstat(path)
    return stat.S_ISREG(status.st_mode) and not getattr(status, "st_file_attributes", 0) & 0x400 and \
        not winjob.named_streams(path)


def _scrub(path):
    """Remove a guard artifact; links are unlinked, never followed."""
    if not _lexists(path):
        return
    status = os.lstat(path)
    if getattr(status, "st_file_attributes", 0) & 0x400:
        (os.rmdir if stat.S_ISDIR(status.st_mode) else os.unlink)(path)
    elif stat.S_ISDIR(status.st_mode):
        for entry in os.scandir(path):
            _scrub(entry.path)
        os.rmdir(path)
    else:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        os.unlink(path)


def downloads_directory():
    guid = (0x374DE290, 0x123F, 0x4565, (0x91, 0x64, 0x39, 0xC4, 0x92, 0x5E, 0x46, 0x7B))
    shell32, ole32 = ctypes.WinDLL("shell32"), ctypes.WinDLL("ole32")
    shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(browser._Guid), ctypes.c_uint32, ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_wchar_p)]
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    d1, d2, d3, d4 = guid
    value, path = browser._Guid(d1, d2, d3, (ctypes.c_ubyte * 8)(*d4)), ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(value), 0, None, ctypes.byref(path)) != 0:
        return None
    try:
        return path.value
    finally:
        ole32.CoTaskMemFree(path)


# --- the browser checks ---

class Checks:
    """One browser guard run over a definition (I7). `layout` names the directories the checks watch:
    target, evidence, temp (the definition's TEMP), cwd, profile (the --userDataDir), run (the run directory),
    inherited_temp."""

    def __init__(self, definition, env, layout, chrome, progress=None):
        self.definition, self.env, self.layout, self.chrome = definition, env, layout, chrome
        self.progress = progress or (lambda message: None)
        self.token = secrets.token_hex(6)
        self.items, self.recorder = [], Recorder()
        self.app = [arg.split("=", 1)[1][len("http://"):-2] for arg in definition["args"]
                    if arg.startswith("--allowedUrlPattern=")]
        self.counter = 0
        self.stuck = None

    def add(self, item, ok, detail=""):
        self.items.append({"item": item, "ok": bool(ok), "detail": str(detail)[:600]})
        self.progress(f"{'ok  ' if ok else 'FAIL'} {item} {str(detail)[:160]}")
        return ok

    # -- MCP helpers --

    def tool(self, name, timeout=TOOL_TIMEOUT, **arguments):
        """(is_error, text); (None, reason) when the server did not answer. After one unanswered call the server is
        treated as stuck (it handles calls in order): every later call is skipped, so the guard ends and fails."""
        started = time.monotonic()
        if self.stuck:
            return None, f"skipped: the MCP server stopped answering ({self.stuck})"
        try:
            return self.client.tool(name, arguments, timeout=timeout)
        except mcp_stdio.McpTimeout as error:
            self.stuck = f"{name}: {error}"
            self.add("mcp-server-answers-every-call", False, self.stuck)
            return None, str(error)
        finally:
            self.progress(f"     {name} {time.monotonic() - started:.1f}s")

    def pages(self):
        # 1.10.1 lists "<id>: <url>" or "<id>: <title> (<url>)", each optionally followed by " [selected]".
        _, text = self.tool("list_pages")
        pages = []
        for match in re.finditer(r"^(\d+):[ \t]*(.*)$", text or "", re.M):
            rest = re.sub(r"(\s*\[[^\]]*\])+\s*$", "", match.group(2).strip())
            inner = re.search(r"\(([^()\s]*)\)$", rest)
            pages.append((int(match.group(1)), inner.group(1) if inner else (rest.split() or [""])[0]))
        return pages

    def close_extra_pages(self, keep):
        for page, _ in self.pages():
            if page not in keep:
                self.tool("close_page", pageId=page)

    def new_page(self, url, isolated=None):
        before = {page for page, _ in self.pages()}
        arguments = {"url": url}
        if isolated:
            arguments["isolatedContext"] = isolated
        error, text = self.tool("new_page", **arguments)
        created = [page for page, _ in self.pages() if page not in before]
        return error, text, (created[0] if created else None)

    def load(self, page, origin, ctx, isolated=None):
        """Open the check page; wait for the page, its worker, WebRTC and Service Worker groups."""
        url = self.site.url(origin, "/check.html", ctx)
        if page is None:
            error, text, page = self.new_page(url, isolated)
        else:
            error, text = self.tool("navigate_page", pageId=page, type="url", url=url)
        ran = self.recorder.wait(ctx, "script", 15)
        if ran:
            self.recorder.wait(ctx, "page-done", 20)
            self.recorder.wait(ctx, "rtc-done", 10)
            self.recorder.wait(ctx, "worker", 10)
            if not self.recorder.wait(ctx, "sw-done", 15) and page is not None:
                self.tool("navigate_page", pageId=page, type="url", url=url)  # a lagging activation runs on reload
                self.recorder.wait(ctx, "sw-done", 15)
        return page, error, text

    def group_done(self, ctx):
        r = self.recorder
        missing = [key for key in ("script", "page-done", "rtc-done", "worker", "sw-registered", "sw-done")
                   if not r.get(ctx, key)]
        if r.get(ctx, "sw-registered") and r.get(ctx, "sw-registered")[0] != "yes":
            missing.append("sw-registered=" + r.get(ctx, "sw-registered")[0])
        return missing

    # -- the run --

    def run(self, job_prefix="ask-codex-guard"):
        # (the guard listeners, the check site and the files it watches are set up before the browser starts)
        self.lan_ip = lan_address()
        self.held = hold_app_ports(self.app)
        self.add("app-ports-held-free", True, ", ".join(self.app))
        closers = []
        try:
            self.sentinel_port = self._free_port_on_all(SENTINEL_BINDS)
            sentinel = RawListener(SENTINEL_BINDS, self.sentinel_port, self.recorder.sentinel)
            closers.append(sentinel.close)
            if not self.lan_ip:
                self.add("external-stand-in-available", False, "no local non-loopback IPv4 interface address")
                lan = None
            else:
                lan_port = self._free_port_on_all(((socket.AF_INET, self.lan_ip),))
                lan = RawListener(((socket.AF_INET, self.lan_ip),), lan_port, self.recorder.lan)
                closers.append(lan.close)
            stun_lan = StunListener(socket.AF_INET, self.lan_ip or "127.0.0.1", self.recorder.udp)
            stun_loop = StunListener(socket.AF_INET, "127.0.0.1", self.recorder.udp)
            closers += [stun_lan.close, stun_loop.close]
            sentinels = [f"http://{spelling}:{self.sentinel_port}/{self.token}" for spelling in SENTINEL_SPELLINGS]
            lan_url = f"http://{self.lan_ip}:{lan.port}/{self.token}" if lan else f"http://127.0.0.1:9/{self.token}"
            self.site = CheckSite(self.token, self.recorder, sentinels, lan_url,
                                  [f"stun:{self.lan_ip or '127.0.0.1'}:{stun_lan.port}", f"stun:127.0.0.1:{stun_loop.port}"])
            for origin, sock in self.held:
                self.site.serve(origin, sock)
            closers.append(self.site.close)
            self._prepare_files()
            job = winjob.Job(job_prefix)
            try:
                process = winjob.start_suspended(job, [self.definition["command"], *self.definition["args"]],
                                                 self.definition["cwd"], self.env)
                self.process, self.job = process, job
                stderr = []
                threading.Thread(target=lambda: [stderr.append(line) for line in process.stderr], daemon=True).start()
                self.stderr = stderr
                try:
                    self.client = mcp_stdio.Client(process.stdin, process.stdout)
                    self._browser_checks()
                finally:
                    try:
                        process.stdin.close()
                    except OSError:
                        pass
                    process.wait(5)
                    ended = job.terminate()
                    self.add("guard-job-ended", ended, "kill-on-close job reports no active process"
                             if ended else f"{job.active_processes()} process(es) still active in the guard job")
                    process.close()
            finally:
                job.close()
            self._final_items()
        finally:
            for close in reversed(closers):
                try:
                    close()
                except OSError:
                    pass
            for _, sock in self.held:
                sock.close()
            self._cleanup_files()
        return self.items

    @staticmethod
    def _free_port_on_all(binds):
        for _ in range(50):
            with socket.socket(binds[0][0], socket.SOCK_STREAM) as probe:
                probe.bind((binds[0][1], 0))
                port = probe.getsockname()[1]
            try:
                for family, address in binds:
                    _exclusive(family, address, port).close()
                return port
            except OSError:
                continue
        raise ValueError("No free port for a guard listener")

    # -- files the checks watch --

    def _prepare_files(self):
        L, t = self.layout, self.token
        self.sentinel_dir = Path(L["run"]) / f"guard-sentinel-{t}"
        self.sentinel_dir.mkdir()
        self.secret = secrets.token_hex(12)  # appears only inside the file, never in a path or URL
        (self.sentinel_dir / "keep.txt").write_text(f"{PROBE} sentinel {self.secret}\n", encoding="utf-8")
        self.sentinel_before = _digest_tree(self.sentinel_dir)
        self.decoys = {}
        for extension in (".png", ".txt", ".network-request", ".network-response"):
            path = Path(L["run"]) / f"guard-decoy-{t}{extension}"
            path.write_text(f"decoy {t}\n", encoding="utf-8")
            self.decoys[extension] = path
        self.decoy_dir = Path(L["run"]) / f"guard-decoy-{t}-lighthouse"
        self.decoy_dir.mkdir()
        for name in ("report.json", "report.html"):
            (self.decoy_dir / name).write_text(f"decoy {t}\n", encoding="utf-8")
        self.decoy_before = {str(p): p.read_bytes() for p in [*self.decoys.values(), *self.decoy_dir.iterdir()]}
        self.run_before = _names(L["run"])
        self.target_before = _names(L["target"])
        self.cwd_before = _names(L["cwd"])
        self.inherited_before = _names(L["inherited_temp"])
        self.downloads = downloads_directory()
        self.removed_downloads = []
        self.downloads_before = _names(self.downloads) if self.downloads else set()
        self.evidence_before = _names(L["evidence"])
        self.junction = Path(L["evidence"]) / f"{PROBE}-junction-{t}"
        import _winapi
        _winapi.CreateJunction(str(self.sentinel_dir), str(self.junction))
        self.symlink = Path(L["evidence"]) / f"{PROBE}-symlink-{t}"
        try:
            os.symlink(str(self.sentinel_dir), str(self.symlink), target_is_directory=True)
            self.symlink_note = None
        except OSError as error:
            self.symlink = None
            self.symlink_note = f"a symbolic link cannot be created by this user on this host ({error.winerror}); " \
                                "the item is not applicable"

    def _cleanup_files(self):
        L = self.layout
        for name in _names(L["evidence"]) - getattr(self, "evidence_before", set()):
            try:
                _scrub(os.path.join(L["evidence"], name))
            except OSError:
                pass
        for path in [*getattr(self, "decoys", {}).values(), getattr(self, "decoy_dir", None),
                     getattr(self, "sentinel_dir", None)]:
            if path is not None:
                try:
                    _scrub(path)
                except OSError:
                    pass
        # The download item can leave the guard's own probe file in the user's Downloads (Chrome's default download
        # directory; the item then fails): only files named after this run's token with the probe's exact content.
        if getattr(self, "downloads", None):
            for name in _names(self.downloads) - self.downloads_before:
                path = os.path.join(self.downloads, name)
                if name.startswith(f"{PROBE}-{self.token}-download") and os.path.isfile(path) and \
                        not os.path.islink(path) and Path(path).read_bytes() == DOWNLOAD_BODY:
                    try:
                        os.unlink(path)
                        self.removed_downloads.append(name)
                    except OSError:
                        pass

    def _probe(self, extension=""):
        self.counter += 1
        stem = f"{PROBE}-{self.token}-{self.counter:03d}"
        return stem, stem + extension

    def _where(self, stem):
        """Where entries named after `stem` appeared: evidence, temp, or a list of outside locations."""
        L = self.layout
        inside_evidence = _find(L["evidence"], stem, True)
        inside_temp = _find(L["temp"], stem, False)
        outside = []
        for directory, recursive in ((self.sentinel_dir, True), (L["run"], False), (L["target"], False),
                                     (L["cwd"], True), (L["inherited_temp"], False), (self.downloads, False),
                                     (L["profile"], True)):
            if directory:
                outside += [p for p in _find(directory, stem, recursive)
                            if not (ntpath.normcase(p).startswith(ntpath.normcase(L["evidence"]) + "\\")
                                    or ntpath.normcase(p).startswith(ntpath.normcase(L["temp"]) + "\\"))]
        return inside_evidence, inside_temp, sorted(set(outside))

    def _decoys_unchanged(self):
        current = {}
        for path in self.decoy_before:
            try:
                current[path] = Path(path).read_bytes()
            except OSError:
                current[path] = None
        extra = _names(self.decoy_dir) - {"report.json", "report.html"}
        return current == self.decoy_before and not extra

    def _attempt(self, item, tool, arguments, expect, stem, timeout=TOOL_TIMEOUT):
        error, text = self.tool(tool, timeout=timeout, **arguments)
        evidence, temp, outside = self._where(stem)
        decoys = self._decoys_unchanged()
        detail = f"{'error' if error else 'no answer' if error is None else 'ok'}: {(text or '')[:200]}"
        if outside:
            detail += f"; outside: {outside[:3]}"
        bad_inside = [p for p in evidence + temp if not _regular_without_streams(p) and not os.path.isdir(p)]
        if expect == "refused":
            ok = error is True and not evidence and not temp and not outside and decoys
        elif expect == "evidence":
            ok = error is False and evidence and not temp and not outside and not bad_inside
        elif expect == "temp":
            ok = error is False and temp and not evidence and not outside and not bad_inside
        else:  # contained: refused, or only regular files under evidence
            ok = not temp and not outside and not bad_inside and (error is True and not evidence or error is False)
        if bad_inside:
            detail += f"; not regular files without streams: {bad_inside[:3]}"
        if not decoys:
            detail += "; a decoy beside the record changed"
        return self.add(item, ok, detail)

    def _decoy_attempt(self, item, tool, arguments, timeout=TOOL_TIMEOUT):
        """R4-1: an absolute write aimed at a script-owned decoy beside the run's target record is refused (the
        decoy, never the real record): an error, every decoy unchanged, nothing new in the run directory."""
        error, text = self.tool(tool, timeout=timeout, **arguments)
        new = sorted(_names(self.layout["run"]) - self.run_before)
        decoys = self._decoys_unchanged()
        return self.add(item, error is True and decoys and not new,
                        f"{'error' if error else 'no answer' if error is None else 'ok'}: {(text or '')[:200]}; "
                        f"decoys {'unchanged' if decoys else 'changed'}; new in run directory: {new[:3]}")

    # -- the item groups --

    def _browser_checks(self):
        client, r = self.client, self.recorder
        try:
            info = client.initialize()
        except mcp_stdio.McpError as error:
            self.add("mcp-server-started", False, f"{error}; stderr: {b''.join(self.stderr)[-400:]!r}")
            return
        self.add("mcp-server-started", isinstance(info, dict) and info.get("serverInfo", {}).get("version") ==
                 browser.VERSION, json.dumps((info or {}).get("serverInfo"))[:200])
        listed = {tool.get("name") for tool in (client.request("tools/list", timeout=30) or {}).get("tools", [])}
        missing = [name for name in self.definition["enabled_tools"] if name not in listed]
        self.add("enabled-tools-exist-in-tools-list", not missing, f"missing: {missing}" if missing else
                 f"{len(self.definition['enabled_tools'])} names present")
        pages = self.pages()
        if not pages:
            self.add("browser-page-available", False, "list_pages returned no page")
            return
        main = pages[0][0]
        # The check page from every app origin, with every probe group.
        for index, origin in enumerate(self.app):
            ctx = f"load{index}"
            self.load(main, origin, ctx)
            self.add(f"check-page-loads-from-{origin}", r.get(ctx, "script"), "page script reported" if
                     r.get(ctx, "script") else "the check page did not run")
        self._process_items()
        # An isolated context obeys the same limits.
        self.load(None, self.app[0], "isolated", isolated=f"{PROBE}-isolated")
        missing = self.group_done("isolated")
        self.add("isolated-context-runs-every-probe-group", not missing, f"missing reports: {missing}" if missing
                 else "every probe group reported")
        self.close_extra_pages({main})
        self._scheme_items(main)
        self._header_items(main)
        self._download_items(main)
        self._file_items(main)
        self._no_path_items(main)
        self._profile_items(main)
        self._lighthouse_reach(main)
        self.add("elicitation-declined-roots-not-offered",
                 all(m != "elicitation/create" or a.get("result", {}).get("action") == "decline" for m, a in
                     client.server_requests) and all(m != "roots/list" or "error" in a for m, a in
                                                     client.server_requests),
                 f"server requests: {[m for m, _ in client.server_requests]}")

    def _process_items(self):
        pids = self.job.pids()
        images = {pid: winjob.image_path(pid) for pid in pids}
        chrome = [image for image in images.values() if image and ntpath.basename(image).lower() == "chrome.exe"]
        self.add("launched-chrome-is-the-fingerprinted-executable",
                 chrome and all(ntpath.normcase(c) == ntpath.normcase(self.chrome) for c in chrome),
                 f"chrome processes: {sorted(set(chrome))}; fingerprinted: {self.chrome}")
        listening = [(a, p, pid) for a, p, pid in winjob.tcp_listeners() if pid in images]
        self.add("chrome-has-no-tcp-listener", not listening, f"listeners of job processes: {listening}" if listening
                 else f"{len(pids)} job processes, none listening")

    def _scheme_items(self, main):
        L = self.layout
        secret = Path(L["run"]) / f"guard-sentinel-{self.token}" / "keep.txt"
        origin = self.app[0]
        urls = [("file", "file:///" + str(secret).replace("\\", "/"), "file:"),
                ("chrome", "chrome://version/", "chrome:"), ("devtools", "devtools://devtools/bundled/inspector.html",
                                                             "devtools:"),
                ("view-source", f"view-source:http://127.0.0.1:{self.sentinel_port}/{self.token}/scheme/vs",
                 "view-source:"),
                ("blob", f"blob:http://{origin}/00000000-0000-4000-8000-000000000000", "blob:"),
                ("filesystem", f"filesystem:http://{origin}/temporary/{PROBE}", "filesystem:"),
                ("about", "about:version", "about:version")]
        for label, url, prefix in urls:
            for how in ("navigate_page", "new_page"):
                self.tool("navigate_page", pageId=main, type="url", url=self.site.url(origin, "/blank.html"))
                if how == "navigate_page":
                    error, text = self.tool("navigate_page", pageId=main, type="url", url=url, timeout=30)
                else:
                    error, text, _ = self.new_page(url)
                shown = [u for _, u in self.pages() if u.lower().startswith(FORBIDDEN_SCHEMES) and u != "about:blank"]
                _, snapshot = self.tool("take_snapshot", pageId=main)
                leaked = self.secret in (snapshot or "")
                ok = (error is True or not shown) and not shown and not leaked and error is not None
                self.add(f"scheme-{label}-{how}-refused-or-no-effect", ok,
                         f"{'error' if error else 'no error'}: {(text or '')[:160]}; pages with {prefix}: {shown}")
                self.close_extra_pages({main})

    def _header_items(self, main):
        """emulate.extraHttpHeaders, Host and Proxy-Authorization included: nothing reaches a guard listener.
        Chrome 154 refuses those two headers (the navigation fails with net::ERR_INVALID_ARGUMENT); a page that does
        load with them runs every probe group like any other. With an ordinary extra header the page must load and
        every probe group must finish."""
        before = len(self.recorder.sentinel) + len(self.recorder.lan)
        outcomes = []
        for label, headers in (("host", {"Host": f"127.0.0.1:{self.sentinel_port}"}),
                               ("proxy-authorization", {"Proxy-Authorization": "Basic YXNrOmNvZGV4"}),
                               ("both", {"Host": f"127.0.0.1:{self.sentinel_port}",
                                         "Proxy-Authorization": "Basic YXNrOmNvZGV4"})):
            error, _ = self.tool("emulate", pageId=main, extraHttpHeaders=json.dumps(headers))
            ctx = f"headers-{label}"
            _, text = self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], "/check.html",
                                                                                            ctx), timeout=30)
            if self.recorder.wait(ctx, "script", 8):
                self.load(main, self.app[0], ctx)
            outcomes.append(f"{label}: {'set' if error is False else 'not set'}, "
                            f"{'page ran' if self.recorder.get(ctx, 'script') else (text or '')[:80]}")
        error, _ = self.tool("emulate", pageId=main, extraHttpHeaders=json.dumps({"X-Ask-Codex-Guard": self.token}))
        self.load(main, self.app[0], "headers")
        missing = self.group_done("headers")
        applied = any(req.get("probe_header") == self.token for req in self.recorder.app_requests)
        self.tool("emulate", pageId=main, extraHttpHeaders="")
        hits = len(self.recorder.sentinel) + len(self.recorder.lan) - before
        self.add("extra-http-headers-keep-the-limits", not missing and applied and error is False and not hits,
                 f"{'; '.join(outcomes)}; ordinary header {'applied' if applied else 'not seen by the app'}; "
                 f"missing reports: {missing}; guard listener hits: {hits}")

    def _download_items(self, main):
        self.load(main, self.app[0], "download")
        _, snapshot = self.tool("take_snapshot", pageId=main)
        match = re.search(r'uid=(\S+) link "Download probe"', snapshot or "")
        clicked = None
        if match:
            clicked, _ = self.tool("click", pageId=main, uid=match.group(1))
        self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], "/download", "download"),
                  timeout=30)
        time.sleep(3)
        stem = f"{PROBE}-{self.token}-download"
        evidence, temp, outside = self._where(stem)
        partial = [n for n in _names(self.downloads) - self.downloads_before if n.endswith(".crdownload")] \
            if self.downloads else []
        partial += [p for directory in (self.layout["temp"], self.layout["profile"], self.layout["evidence"])
                    for p in _find(directory, ".crdownload", True) + _find(directory, "Unconfirmed ", True)]
        self.add("download-does-not-land-outside-evidence", not outside and not partial and not temp,
                 f"link {'clicked' if clicked is False else 'not clicked'}; evidence: {len(evidence)}; "
                 f"outside: {outside + partial}")
        self.add("download-lands-nowhere", clicked is False and not evidence and not temp and not outside and
                 not partial, f"download-attribute click {'done' if clicked is False else 'not done'}, attachment "
                 f"navigation done; found: {evidence + temp + outside + partial}")

    def _paths(self, stem, extension):
        """(label, path, expectation, timeout) of the file-writing matrix for one probe name."""
        L = self.layout
        target, evidence, temp = L["target"], L["evidence"], L["temp"]
        name = stem + extension
        posix = lambda p: str(p).replace("\\", "/")
        drive, rest = ntpath.splitdrive(str(self.sentinel_dir / name))
        admin = f"{drive[0]}$" + rest
        swapped = lambda p: "".join(c.swapcase() if c.isalpha() else c for c in posix(p))
        cases = [
            ("absolute-outside", posix(self.sentinel_dir / name), "refused", TOOL_TIMEOUT),
            ("relative", name, "refused", TOOL_TIMEOUT),
            ("dot-dot", f"{posix(evidence)}/../{name}", "refused", TOOL_TIMEOUT),
            ("extended-path", "\\\\?\\" + str(self.sentinel_dir / name), "refused", TOOL_TIMEOUT),
            ("extended-unc", "\\\\?\\UNC\\127.0.0.1\\" + admin, "refused", UNC_TIMEOUT),
            ("unc-loopback", "\\\\127.0.0.1\\" + admin, "refused", UNC_TIMEOUT),
            ("unc-other-host", f"\\\\127.0.0.2\\{PROBE}-share\\{name}", "refused", UNC_TIMEOUT),
            ("drive-relative", f"{ntpath.splitdrive(str(target))[0]}{name}", "refused", TOOL_TIMEOUT),
            ("alternate-stream-outside", f"{posix(target)}/{name}:s", "refused", TOOL_TIMEOUT),
            ("case-variant-outside", f"{swapped(target)}/{name}", "refused", TOOL_TIMEOUT),
            ("trailing-dot-outside", f"{posix(target)}/{name}.", "refused", TOOL_TIMEOUT),
            ("trailing-space-outside", f"{posix(target)}/{name} ", "refused", TOOL_TIMEOUT),
            ("device-nul", "NUL", "refused", TOOL_TIMEOUT),
            ("device-con", "CON", "refused", TOOL_TIMEOUT),
            ("junction-in-evidence", f"{posix(self.junction)}/{name}", "refused", TOOL_TIMEOUT),
            ("under-target-outside-evidence", f"{posix(target)}/{name}", "refused", TOOL_TIMEOUT),
            ("into-evidence", f"{posix(evidence)}/{name}", "evidence", TOOL_TIMEOUT),
            ("into-run-owned-temp", f"{posix(temp)}/{name}", "temp", TOOL_TIMEOUT),
            ("evidence-case-variant", f"{swapped(evidence)}/{name}", "contained", TOOL_TIMEOUT),
            ("evidence-alternate-stream", f"{posix(evidence)}/{name}:s", "contained", TOOL_TIMEOUT),
            ("evidence-trailing-dot", f"{posix(evidence)}/{name}.", "contained", TOOL_TIMEOUT),
        ]
        short_target = winjob.short_path(target)
        if short_target and short_target.lower() != str(target).lower():
            cases.append(("short-name-outside", f"{short_target}\\{name}", "refused", TOOL_TIMEOUT))
        short_evidence = winjob.short_path(evidence)
        if short_evidence and short_evidence.lower() != str(evidence).lower():
            cases.append(("evidence-short-name", f"{short_evidence}\\{name}", "contained", TOOL_TIMEOUT))
        if self.symlink is not None:
            cases.append(("symlink-in-evidence", f"{posix(self.symlink)}/{name}", "refused", TOOL_TIMEOUT))
        return cases

    def _file_items(self, main):
        # A plain page whose request has a body (get_network_request's request and response files).
        self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], "/post.html"))
        time.sleep(1.5)
        _, listing = self.tool("list_network_requests", pageId=main)
        reqid = None
        for line in (listing or "").splitlines():
            if re.search(r"POST \S*/post\b", line):
                match = re.search(r"reqid=(\d+)", line)
                reqid = int(match.group(1)) if match else None
        self.add("network-request-with-body-available", reqid is not None, (listing or "")[:200] if reqid is None
                 else f"reqid {reqid}")
        params = [("screenshot", "take_screenshot", "filePath", ".png", {}),
                  ("snapshot", "take_snapshot", "filePath", ".txt", {}),
                  ("request-body", "get_network_request", "requestFilePath", ".network-request", {"reqid": reqid}),
                  ("response-body", "get_network_request", "responseFilePath", ".network-response", {"reqid": reqid})]
        if self.symlink is None:
            self.add("symlink-in-evidence", True, self.symlink_note)
        short = winjob.short_path(self.layout["target"])
        if not short or short.lower() == str(self.layout["target"]).lower():
            self.add("short-name-outside", True, "no 8.3 short name on this volume; the item is not applicable")
        for label, tool, param, extension, extra in params:
            if reqid is None and tool == "get_network_request":
                continue
            for form in [case[0] for case in self._paths("form", extension)]:
                stem = self._probe()[0]  # each attempt has its own probe name, so it is traced on its own
                [(_, path, expect, timeout)] = [case for case in self._paths(stem, extension) if case[0] == form]
                self._attempt(f"write-{label}-{form}", tool, {"pageId": main, param: path, **extra}, expect, stem,
                              timeout)
            self._decoy_attempt(f"write-{label}-aimed-at-decoy-beside-record", tool,
                                {"pageId": main, param: str(self.decoys[extension]).replace("\\", "/"), **extra})
        # lighthouse_audit.outputDirPath (each run takes seconds: a subset of the forms, snapshot mode).
        L = self.layout
        posix = lambda p: str(p).replace("\\", "/")
        for form, make, expect in (("absolute-outside", lambda s: posix(self.sentinel_dir / s), "refused"),
                                   ("relative", lambda s: s, "refused"),
                                   ("under-target-outside-evidence", lambda s: f"{posix(L['target'])}/{s}", "refused"),
                                   ("into-evidence", lambda s: f"{posix(L['evidence'])}/{s}", "evidence"),
                                   ("into-run-owned-temp", lambda s: f"{posix(L['temp'])}/{s}", "temp")):
            stem = self._probe()[0]
            self._attempt(f"write-lighthouse-{form}", "lighthouse_audit",
                          {"pageId": main, "mode": "snapshot", "outputDirPath": make(stem)}, expect, stem, 120)
        self._decoy_attempt("write-lighthouse-aimed-at-decoy-beside-record", "lighthouse_audit",
                            {"pageId": main, "mode": "snapshot",
                             "outputDirPath": str(self.decoy_dir).replace("\\", "/")}, 120)
        # Named items of the plan (the negative controls record these).
        def every(suffix):
            chosen = [i for i in self.items if i["item"].startswith("write-") and i["item"].endswith(suffix)]
            return chosen and all(i["ok"] for i in chosen), [i["item"] for i in chosen if not i["ok"]]
        ok, failing = every("-into-run-owned-temp")
        self.add("absolute-temp-write-lands-in-run-owned-temp", ok, f"failing: {failing}" if failing else
                 "every file-writing parameter landed in the run-owned TEMP")
        ok, failing = every("-under-target-outside-evidence")
        self.add("path-under-target-outside-evidence-refused", ok, f"failing: {failing}" if failing else
                 "refused for every parameter")
        ok, failing = every("-into-evidence")
        self.add("write-into-evidence-succeeds", ok, f"failing: {failing}" if failing else
                 "landed under evidence for every parameter")
        ok, failing = every("-aimed-at-decoy-beside-record")
        self.add("write-aimed-at-decoy-beside-record-refused", ok and self._decoys_unchanged(),
                 f"failing: {failing}" if failing else "refused; decoys unchanged")

    def _no_path_items(self, main):
        L = self.layout
        inherited_before = _names(L["inherited_temp"])
        cwd_before, target_before = _names(L["cwd"]), _names(L["target"])
        temp_before = _names(L["temp"])
        self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], "/tall.html"))
        shot_error, _ = self.tool("take_screenshot", pageId=main, fullPage=True, timeout=90)
        self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], "/large.html"))
        snap_error, _ = self.tool("take_snapshot", pageId=main, timeout=90)
        lh_error, _ = self.tool("lighthouse_audit", pageId=main, mode="snapshot", timeout=120)
        new_inherited = [n for n in _names(L["inherited_temp"]) - inherited_before
                         if n.startswith(("chrome-devtools-mcp-", "puppeteer_dev_chrome_profile-")) or
                         self.token in n]
        new_temp = sorted(_names(L["temp"]) - temp_before)
        ok = not new_inherited and _names(L["cwd"]) == cwd_before and _names(L["target"]) == target_before
        self.add("no-path-outputs-stay-in-run-owned-directories", ok,
                 f"new in inherited TEMP: {new_inherited}; new in run-owned TEMP: {new_temp[:6]}; screenshot "
                 f"{'error' if shot_error else 'ok'}, snapshot {'error' if snap_error else 'ok'}, lighthouse "
                 f"{'error' if lh_error else 'ok'}")

    def _profile_items(self, main):
        L = self.layout
        profiles = [L["profile"]] if os.path.isdir(L["profile"]) else []
        written = []
        for route, relative in (("/prefs.json", ("Default", "Preferences")), ("/local-state.json", ("Local State",))):
            self.tool("navigate_page", pageId=main, type="url", url=self.site.url(self.app[0], route))
            _, listing = self.tool("list_network_requests", pageId=main)
            match = None
            for line in (listing or "").splitlines():
                if route in line:
                    match = re.search(r"reqid=(\d+)", line) or match
            if not match or not profiles:
                continue
            for profile in profiles:
                path = str(Path(profile, *relative)).replace("\\", "/")
                error, text = self.tool("get_network_request", pageId=main, reqid=int(match.group(1)),
                                        responseFilePath=path)
                written.append(f"{'/'.join(relative)}: {'error' if error else (text or '')[-120:]}")
        self.load(None, self.app[0], "profile-new-page")
        self.load(None, self.app[0], "profile-isolated", isolated=f"{PROBE}-profile")
        missing = self.group_done("profile-new-page") + self.group_done("profile-isolated")
        self.add("profile-overwrite-keeps-sentinel-and-service-worker-limits", profiles and not missing,
                 f"profiles: {profiles}; written: {written}; missing reports: {missing}")
        self.close_extra_pages({main})

    def _lighthouse_reach(self, main):
        before = len(self.recorder.sentinel) + len(self.recorder.lan)
        self.load(main, self.app[0], "lighthouse")
        error, _ = self.tool("lighthouse_audit", pageId=main, mode="navigation", timeout=180)
        after = len(self.recorder.sentinel) + len(self.recorder.lan)
        others = [req for req in self.recorder.app_requests if not req["path"].startswith(self.site.prefix)
                  and req["path"] not in ("/favicon.ico", "/robots.txt")]
        self.add("lighthouse-does-not-reach-another-port", error is False and after == before,
                 f"{'error' if error else 'ran'}; guard listener hits during lighthouse: {after - before}; "
                 f"other app paths: {[r['path'] for r in others][:5]}")

    def _final_items(self):
        r, L = self.recorder, self.layout
        by_kind = {}
        unattributed = []
        for hit in r.sentinel:
            match = re.search(r"^\S+ /[0-9a-f]+/([^/ ]+)/([a-z0-9]+)", hit["first"])
            if match:
                by_kind.setdefault(match.group(2), []).append(f"{hit['local']} ctx={match.group(1)}")
            else:
                unattributed.append(f"{hit['local']}: {hit['first'][:60]!r}")
        page_ctx = [ctx for ctx in r.reports if r.get(ctx, "script")]
        page_done = all(r.get(ctx, "page-done") for ctx in page_ctx) and page_ctx
        for kind, label in (("img", "image"), ("iframe", "iframe"), ("fetch", "fetch"), ("ws", "websocket"),
                            ("beacon", "sendbeacon"), ("r307img", "307-redirect-image"),
                            ("r307fetch", "307-redirect-fetch")):
            self.add(f"{label}-to-free-loopback-port-blocked", page_done and not by_kind.get(kind),
                     f"arrived via {by_kind[kind][:4]}" if by_kind.get(kind) else
                     "nothing arrived (127.0.0.1, localhost, [::1], 127.0.0.2, 0.0.0.0)" if page_done else
                     "a page probe group did not finish")
        workers = [ctx for ctx in page_ctx if not any(v.startswith("done") for v in r.get(ctx, "worker"))]
        self.add("worker-to-free-loopback-port-blocked", not workers and not by_kind.get("worker") and page_ctx,
                 f"arrived via {by_kind.get('worker', [])[:4]}" if by_kind.get("worker") else
                 f"worker did not finish in {workers}" if workers else "nothing arrived" if page_ctx else
                 "no check page ran")
        sw_missing = [ctx for ctx in page_ctx if not r.get(ctx, "sw-done")]
        self.add("service-worker-to-free-loopback-port-blocked", not sw_missing and not by_kind.get("sw") and page_ctx,
                 f"arrived via {by_kind.get('sw', [])[:4]}" if by_kind.get("sw") else
                 f"service worker did not report in {sw_missing}" if sw_missing else "nothing arrived")
        self.add("view-source-to-free-loopback-port-blocked", not by_kind.get("vs"),
                 by_kind.get("vs", "nothing arrived"))
        self.add("no-unattributed-sentinel-hit", not unattributed, unattributed[:4])
        kind = lambda hit: (re.search(r"^\S+ /[0-9a-f]+/[^/ ]+/([a-z0-9]+)", hit["first"]) or [None, None])[1]
        lan_page = [h for h in r.lan if kind(h) != "sw"]
        lan_sw = [h for h in r.lan if kind(h) == "sw"]
        page_external = [(ctx, v) for ctx in page_ctx for key in ("page-lan", "page-external")
                         for v in r.get(ctx, key) if v != "failed"]
        page_missing = [ctx for ctx in page_ctx if not r.get(ctx, "page-lan") or not r.get(ctx, "page-external")]
        self.add("page-requests-to-non-loopback-and-external-fail",
                 page_ctx and self.lan_ip and not lan_page and not page_external and not page_missing,
                 f"stand-in hits: {len(lan_page)}; reached: {page_external[:4]}; unreported: {page_missing}")
        sw_external = [(ctx, v) for ctx in page_ctx for key in ("sw-lan", "sw-external")
                       for v in r.get(ctx, key) if v != "failed"]
        self.add("service-worker-requests-to-non-loopback-and-external-fail",
                 page_ctx and self.lan_ip and not lan_sw and not sw_external and not sw_missing,
                 f"stand-in hits: {len(lan_sw)}; reached: {sw_external[:4]}; unreported: {sw_missing}")
        rtc = {ctx: r.get(ctx, "rtc") for ctx in page_ctx}
        srflx = [ctx for ctx, values in rtc.items() if any("srflx" in v for v in values)]
        rtc_missing = [ctx for ctx in page_ctx if not r.get(ctx, "rtc-done")]
        self.add("webrtc-yields-no-server-reflexive-candidate",
                 page_ctx and not srflx and not r.udp and not rtc_missing,
                 f"srflx in {srflx}; UDP packets at the guard's STUN listeners: {len(r.udp)}; unreported: "
                 f"{rtc_missing}; candidate types: {sorted({v for values in rtc.values() for v in values})}")
        self.add("sentinel-directory-unchanged", _digest_tree(self.sentinel_dir) == self.sentinel_before)
        self.add("decoys-beside-record-unchanged", self._decoys_unchanged())
        new_inherited = sorted(n for n in _names(L["inherited_temp"]) - self.inherited_before
                               if self.token in n or n.startswith(("puppeteer_dev_chrome_profile-",
                                                                   "chrome-devtools-mcp-")))
        self.add("no-probe-named-entry-in-inherited-temp", not new_inherited,
                 f"{L['inherited_temp']}: {new_inherited[:6]}")
        self.add("mcp-cwd-unchanged", _names(L["cwd"]) == self.cwd_before, sorted(_names(L["cwd"]))[:6])
        self.add("target-unchanged-outside-evidence", _names(L["target"]) == self.target_before,
                 sorted(_names(L["target"]) ^ self.target_before)[:6])
        expected_run = self.run_before
        self.add("run-directory-unchanged", _names(L["run"]) == expected_run,
                 sorted(_names(L["run"]) ^ expected_run)[:6])
        downloads_new = sorted(n for n in (_names(self.downloads) - self.downloads_before) if self.token in n) \
            if self.downloads else []
        self.add("nothing-in-user-downloads", not downloads_new, downloads_new)
        ports = {int(origin.rsplit(":", 1)[1]) for origin in self.app}
        others = [(a, p, pid) for a, p, pid in winjob.tcp_listeners() if p in ports and pid != os.getpid()]
        self.add("app-ports-held-by-the-guard-throughout", not others, others or "only the guard listens")
        try:
            kept = json.loads(Path(L["profile"], "Default", "Preferences").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            kept = {"error": type(error).__name__}
        self.add("profile-still-blocks-downloads", kept.get("download_restrictions") == 3,
                 f"download_restrictions after the run: {kept.get('download_restrictions', kept.get('error'))}")


# --- exercise wiring ---

def _guard_record(directory):
    path = Path(directory) / "guard.json"
    try:
        status = os.lstat(path)
    except OSError:
        return None
    if getattr(status, "st_file_attributes", 0) & 0x400 or not stat.S_ISREG(status.st_mode):
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def current_fingerprint(cli, plan, state_dir=None):
    """The fingerprint of an exercise's definition template and the facts of this host, now."""
    import exercise
    b, summary = plan["browser"], plan["summary"]
    node = browser.node_executable(cli.which)
    facts = dependencies(cli, b["cwd"], summary["target"], state_dir)
    entry = browser.install_directory().joinpath(*browser.ENTRY) if state_dir is None else \
        Path(state_dir, f"{browser.PACKAGE}-{browser.VERSION}", *browser.ENTRY)
    template = exercise._template({"app": summary["app"], "headed": plan["request"]["headed"]}, node, entry)
    instantiated = browser.instantiate(template, summary["browser_server"], summary["target"], b["cwd"], b["temp"],
                                       b["proxy_port"], b["profile"])
    if instantiated != b["definition"] or browser.never_listed(instantiated, b["profile"]):
        raise ValueError("The exercise's browser server definition is not the template's instantiation; "
                         "prepare a new exercise")
    if exercise.is_attach(plan):
        # Attach mode (C8): the template keeps the attached ports; the mode is part of the fingerprint.
        return template, facts, fingerprint(template, facts, "attach")
    return template, facts, fingerprint(template, facts)


def require_current_pass(cli, directory, plan, state_dir=None):
    """`run`: a pass for this exercise's exact fingerprint, less than 12 hours old, or ValueError. Attach mode also
    needs this exercise's own real-definition check (never cached), made after attach-start."""
    import exercise
    record = _guard_record(directory)
    if not record:
        raise ValueError("No browser guard pass for this exercise; run the guard before the app starts")
    _, _, fp = current_fingerprint(cli, plan, state_dir)
    if record.get("fingerprint") != fp:
        raise ValueError("The browser guard passed for another configuration (the fingerprint changed: browser, "
                         "Chrome, node, codex-cli, policy or package); prepare a new exercise")
    passed = record.get("passed_at")
    age = now() - passed if type(passed) in (int, float) else None
    if age is None or not 0 <= age <= CACHE_SECONDS:
        raise ValueError("The browser guard pass is older than 12 hours; prepare a new exercise")
    if exercise.is_attach(plan):
        check = record.get("real_check")
        if record.get("mode") != "attach" or not isinstance(check, dict) or check.get("passed") is not True:
            raise ValueError("The real-definition check of the attached ports has not passed for this exercise; "
                             "run the guard after attach-start")
    return record


def browser_guard(cli, directory, plan, template, state_dir=None):
    """Run the full browser guard for an exercise (own siblings, own nonce, own proxy port); returns its items."""
    import exercise
    b, summary = plan["browser"], plan["summary"]
    temp = disposable_target.create_sibling(directory, "guard-temp")
    cwd = disposable_target.create_sibling(directory, "guard-cwd")
    profile = disposable_target.create_sibling(directory, "guard-profile")
    problems = exercise.placement_problems(directory, Path(summary["target"]), Path(b["evidence"]), temp, cwd, profile)
    if problems:
        raise ValueError("Guard directory placement refused: " + "; ".join(problems))
    browser.seed_profile(profile)  # U16: downloads blocked before the guard's launch
    problems = browser.profile_problems(profile)
    if problems:
        raise ValueError("Guard profile refused: " + "; ".join(problems))
    holder = browser.ProxyHolder(browser.free_loopback_port())
    try:
        definition = browser.instantiate(template, browser.NAME_PREFIX + secrets.token_hex(8), summary["target"],
                                         cwd, temp, holder.port, profile)
        if browser.never_listed(definition, profile):
            raise ValueError("The guard's browser server definition carries a forbidden argument")
        base = cli.shell_environment()
        layout = {"target": summary["target"], "evidence": b["evidence"], "temp": temp, "cwd": cwd,
                  "profile": profile, "run": str(directory),
                  "inherited_temp": _env_get(base, "TEMP") or _env_get(base, "TMP")}
        facts_chrome = chrome_executable(mcp_environment(base, {}))
        return Checks(definition, mcp_environment(base, definition["env"]), layout, facts_chrome).run()
    finally:
        holder.close()


def guard_exercise(cli, directory, state_dir=None):
    """consult.py guard: the dependency check, then a cached pass (ports re-checked) or the browser guard."""
    import exercise
    directory, plan = cli.plan_at(directory)
    if not exercise.is_plan(plan):
        raise ValueError("guard applies to exercises only")
    exercise.require_platform()
    if (directory / "started").exists():
        raise ValueError("The exercise run has started; the guard runs before it")
    if exercise.is_attach(plan):
        return guard_attached(cli, directory, plan, state_dir)
    if (directory / "supervisor-config.json").exists():
        raise ValueError("The app start was attempted for this exercise; the guard runs before any app process")
    try:
        template, facts, fp = current_fingerprint(cli, plan, state_dir)
        hit = cached_pass(state_dir, fp)
        if hit:
            ports_free(plan["summary"]["app"])
            record = {"fingerprint": fp, "source": "cache", "passed_at": hit["passed_at"], "checked_at": now(),
                      "facts": facts}
        else:
            items = browser_guard(cli, directory, plan, template, state_dir)
            if not all(item["ok"] for item in items):
                raise GuardFailed(items)
            passed = now()
            record = {"fingerprint": fp, "source": "ran", "passed_at": passed, "checked_at": passed, "facts": facts,
                      "items": len(items)}
            store_pass(state_dir, fp, {"fingerprint": fp, "passed_at": passed, "facts": facts, "items": len(items)})
        cli.write_json(directory / "guard.json", record)
    except GuardFailed as failure:
        result = exercise.fail_at_once(cli, directory, plan, str(failure))
        return {**result, "guard": {"source": "ran", "passed": False,
                                    "failing": [i for i in failure.items if not i["ok"]],
                                    "items": len(failure.items)}}
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: the guard failed"
        return {**exercise.fail_at_once(cli, directory, plan, reason), "guard": {"passed": False}}
    return {"state": "guard_passed", "directory": str(directory),
            "guard": {"source": record["source"], "passed_at": record["passed_at"], "fingerprint": fp}}


def guard_port_mapping(app, avoid):
    """C8: for each attached port number a guard-owned loopback port, free on 127.0.0.1 and ::1 now, distinct from
    every attached port, from `avoid` (the owned proxy port) and from each other."""
    import attach
    attached = attach.ports_of(app)
    mapping = {}
    for port in sorted(attached):
        for _ in range(50):
            candidate = Checks._free_port_on_all(((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")))
            if candidate not in avoid and candidate not in attached and candidate not in mapping.values():
                mapping[port] = candidate
                break
        else:
            raise ValueError("No free guard port for the attached port substitution")
    return mapping


def _node_and_entry(cli, state_dir=None):
    node = browser.node_executable(cli.which)
    entry = browser.install_directory().joinpath(*browser.ENTRY) if state_dir is None else \
        Path(state_dir, f"{browser.PACKAGE}-{browser.VERSION}", *browser.ENTRY)
    return node, entry


def guard_attached(cli, directory, plan, state_dir=None):
    """consult.py guard of an attach-mode exercise (C8, I14), after attach-start so that the supervisor polls the
    listener table while it runs (N-c): the browser guard on the same template with only the attached port numbers
    replaced by guard-owned ports (a literal diff proves nothing else differs; the guard never binds an attached
    port), or a cached pass for the attach-mode fingerprint; then, every exercise and never cached, the
    real-definition check on the attached ports (attach.real_check). A failure ends what the exercise holds and
    removes the target (exercise.fail_ended); the attached processes are never signalled."""
    import attach
    import exercise
    import supervisor
    try:
        supervisor.require_started(directory, plan)
    except ValueError as error:
        raise ValueError(f"{error}. In attach mode attach-start comes before the guard") from None
    try:
        template, facts, fp = current_fingerprint(cli, plan, state_dir)
        hit = cached_pass(state_dir, fp)
        app = plan["summary"]["app"]
        if hit:
            record = {"fingerprint": fp, "source": "cache", "passed_at": hit["passed_at"], "checked_at": now(),
                      "facts": facts, "mode": "attach"}
        else:
            mapping = guard_port_mapping(app, {plan["browser"]["proxy_port"]})
            node, entry = _node_and_entry(cli, state_dir)
            guarded = exercise._template({"app": substitute_ports(app, mapping), "headed": plan["request"]["headed"]},
                                         node, entry)
            check_substitution(template, guarded, mapping)
            items = browser_guard(cli, directory, plan, guarded, state_dir)
            if not all(item["ok"] for item in items):
                raise GuardFailed(items)
            passed = now()
            substitution = {str(port): guard_port for port, guard_port in sorted(mapping.items())}
            record = {"fingerprint": fp, "source": "ran", "passed_at": passed, "checked_at": passed, "facts": facts,
                      "items": len(items), "mode": "attach", "substitution": substitution}
            store_pass(state_dir, fp, {"fingerprint": fp, "passed_at": passed, "facts": facts, "items": len(items),
                                       "mode": "attach", "substitution": substitution})
        check = attach.real_check(cli, directory, plan)
        if not check["passed"]:
            raise GuardFailed(check["items"], "The real-definition check of the attached ports failed")
        record["real_check"] = {"passed": True, "checked_at": now(), "items": len(check["items"]),
                                "checked": [item["item"] for item in check["items"]]}
        cli.write_json(directory / "guard.json", record)
    except GuardFailed as failure:
        result = exercise.fail_ended(cli, directory, plan, str(failure))
        return {**result, "guard": {"passed": False, "failing": [i for i in failure.items if not i["ok"]],
                                    "items": len(failure.items)}}
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: the guard failed"
        return {**exercise.fail_ended(cli, directory, plan, reason), "guard": {"passed": False}}
    return {"state": "guard_passed", "directory": str(directory),
            "guard": {"source": record["source"], "passed_at": record["passed_at"], "fingerprint": fp,
                      "real_check": "passed"}}


def codex_notice(version):
    """N10: whether the installed codex-cli is the version the browser-tool approval was measured on (probe B1)."""
    return {"codex_tested_version": TESTED_CODEX_CLI, "codex_untested": str(version).strip() != TESTED_CODEX_CLI}


START_CHECK_SECONDS = 120  # the whole start check, MCP start to confirmed end
START_CHECK_PREFIX = "ask-codex-start-check"
PROFILE_LEFTOVERS = ("puppeteer_dev_chrome_profile-", "chrome-devtools-mcp-")


def start_check(cli, state_dir=None):
    """consult.py browser-start-check (setup only, plan C7 / ticket 07: "the pinned MCP starts"). Starts the verified
    pinned chrome-devtools-mcp over stdio with I5's definition (own nonce, a closed owned proxy port held for the
    check, script-owned TEMP/TMP, cwd, profile seeded to block downloads, and a scratch evidence root, all in one
    new directory under the user-level state directory, never in the user's %TEMP%), in the environment Codex gives a
    stdio MCP server (CODEX_DEFAULT_ENV, then the definition's env), inside its own kill-on-close job (node created
    suspended, assigned, resumed). It initializes, lists the tools and requires every enabled tool of the definition;
    it calls no tool, so nothing asks the server to launch Chrome (whether Chrome started anyway is reported). Then
    it ends the job and confirms no process is left in it, checks that no browser profile appeared in the inherited
    %TEMP%, and removes its directory. Bounded by START_CHECK_SECONDS. Returns {"state": "ready", ...} or
    {"state": "failed", "reason", ...}; never raises for a check that fails."""
    disposable_target.require_windows()
    started = time.monotonic()
    result = {"processes_ended": True, "chrome_started": False}
    root = (Path(state_dir) if state_dir else browser.state_directory()) / f"{START_CHECK_PREFIX}-{secrets.token_hex(6)}"
    base = cli.shell_environment()
    inherited = _env_get(base, "TEMP") or _env_get(base, "TMP")
    inherited_before = _names(inherited) if inherited else set()
    holder = job = process = None
    try:
        install.verify(state_dir) if state_dir else install.verify_installed()
        node = browser.node_executable(cli.which)
        entry = browser.entry_script() if state_dir is None else \
            Path(state_dir, f"{browser.PACKAGE}-{browser.VERSION}", *browser.ENTRY)
        if not os.path.isfile(entry) or os.path.islink(entry):
            raise ValueError(f"The browser server entry script is missing ({entry})")
        root.parent.mkdir(parents=True, exist_ok=True)
        root.mkdir()  # exclusive: a new directory owned by this check
        temp, cwd, profile, target = (root / name for name in ("temp", "cwd", "profile", "target"))
        for directory in (temp, cwd, profile, target, target / "evidence"):
            directory.mkdir()
        browser.seed_profile(profile)
        holder = browser.ProxyHolder(browser.free_loopback_port())
        app_port = browser.free_loopback_port()
        definition = browser.instantiate(browser.template([f"127.0.0.1:{app_port}"], False, node, entry),
                                         browser.NAME_PREFIX + secrets.token_hex(8), target, cwd, temp, holder.port,
                                         profile)
        if browser.never_listed(definition, profile):
            raise ValueError("The browser server definition carries a forbidden argument")
        env = mcp_environment(base, definition["env"])
        job = winjob.Job(START_CHECK_PREFIX)
        process = winjob.start_suspended(job, [definition["command"], *definition["args"]], definition["cwd"], env)
        client = mcp_stdio.Client(process.stdin, process.stdout)
        left = lambda: max(1.0, START_CHECK_SECONDS - (time.monotonic() - started))  # noqa: E731
        try:
            info = client.initialize(timeout=min(float(definition["startup_timeout_sec"]), left()))
            listed = client.request("tools/list", timeout=min(30.0, left())) or {}
        except mcp_stdio.McpTimeout as error:
            raise ValueError(f"The browser server did not answer in time ({error})") from None
        except mcp_stdio.McpError as error:
            raise ValueError(f"The browser server did not start ({error})") from None
        server = (info or {}).get("serverInfo", {}) if isinstance(info, dict) else {}
        if server.get("version") != browser.VERSION:
            raise ValueError(f"The browser server reports version {str(server.get('version'))[:40]!r}, not "
                             f"{browser.VERSION}")
        names = sorted(t.get("name") for t in listed.get("tools", []) if isinstance(t, dict))
        missing = [name for name in definition["enabled_tools"] if name not in names]
        if missing:
            raise ValueError(f"The browser server lacks enabled tools: {', '.join(missing)}")
        images = [winjob.image_path(pid) or "" for pid in job.pids()]
        result.update(server={"name": server.get("name"), "version": server.get("version")},
                      tools=names, enabled_tools_present=len(definition["enabled_tools"]),
                      chrome_started=any(ntpath.basename(i).lower() == "chrome.exe" for i in images))
    except Exception as error:
        result["state"] = "failed"
        result["reason"] = str(error) if isinstance(error, ValueError) else \
            f"{type(error).__name__}: the browser server start check failed"
    finally:
        if process is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
            process.wait(5)
        if job is not None:
            ended = job.terminate(15)
            result["processes_ended"] = ended and job.active_processes() == 0
            job.close()
        if process is not None:
            process.close()
        if holder is not None:
            holder.close()
        if os.path.lexists(root):
            try:
                _scrub(root)
            except OSError:
                pass
        result["directory_removed"] = not os.path.lexists(root)
        new = sorted(n for n in (_names(inherited) if inherited else set()) - inherited_before
                     if n.startswith(PROFILE_LEFTOVERS))
        result["inherited_temp_profiles"] = new
    if result.get("state") != "failed":
        problems = [p for p, bad in (("a process of the check is still running", not result["processes_ended"]),
                                     ("its directory could not be removed", not result["directory_removed"]),
                                     ("a browser profile appeared in your %TEMP%", bool(result["inherited_temp_profiles"])))
                    if bad]
        result["state"] = "failed" if problems else "ready"
        if problems:
            result["reason"] = "The browser server started, but " + "; ".join(problems)
    result["seconds"] = round(time.monotonic() - started, 1)
    return result


def dependency_report(cli, state_dir=None):
    """consult.py exercise-deps: node, Chrome (>= 149) and the verified package; no browser is started. Also names
    the codex-cli version the plugin was tested with (N10: the skill tells the user and asks when it differs)."""
    disposable_target.require_windows()
    neutral = Path(cli.shell_environment().get("SYSTEMROOT", r"C:\Windows"))
    facts = dependencies(cli, neutral, neutral, state_dir)
    return {"state": "ready", **facts, **codex_notice(facts["codex_version"])}
