"""Attach mode of an exercise (plan `.scratch/exercise-skills/plan.md` claim C8, ticket 08; I14, I15, I16, U6-U10,
AT-1..AT-10). Windows only (I13): the owner inspection (`examine`) is the platform layer's; the eval fake replaces it.

The user may attach an exercise to the frontend and backend they already run from their project instead of a copy:
no copy, no install, no app process, no app job. Codex still works from a new, empty disposable directory (I1, I3)
with a read-only shell and the same restricted browser, limited to the attached host:ports. The skill never starts,
stops or signals the user's servers.

    consult.py attach-owners <file>     {"project": "<absolute project>", "app": ["127.0.0.1:5173", ...]}: who owns
                                         each attached port, for the user's confirmation; writes nothing
    consult.py prepare <request>        "mode": "attach" with "attach": {"chosen_by_user": true, "owners":
                                         [{"port", "pid", "created"}, ...]} (the owners the user confirmed); the
                                         listener table must still show exactly those owners
    consult.py attach-start <run dir>   the supervisor (AttachSupervisor): owned proxy port, a SYNCHRONIZE |
                                         PROCESS_QUERY_LIMITED_INFORMATION handle to each owner (never terminate rights),
                                         re-verification of each owner by PID and creation time, then the listener
                                         table polled every 2 s until finish; any change stops the exercise
    consult.py guard <run dir>          after attach-start: the browser guard on the same template with only the
                                         attached port numbers replaced by guard-owned ports (guard.py), then, every
                                         exercise and never cached, the real-definition check (real_check)

Listener-table rule (I14, AT-4): every attached port number must have listeners, and the full IPv4 and IPv6 table for
that number must show exactly one process, bound only to specific loopback addresses, listening on each attached
host itself. Refused: a wildcard binding, an IPv4-mapped binding, a non-loopback address, PID 0 or 4 (System,
http.sys), an owner whose image or creation time cannot be read, more than one process on the port number, and an
owner whose image name is on the closed forwarder list FORWARDERS (whatever its directory: a renamed executable
counts by its name). Forwarders off that list (`ssh.exe -L`, `kubectl port-forward`) rely on the user's confirmation
(residual). The owner's command line is read with NtQueryInformationProcess(ProcessCommandLineInformation), limited
rights (winjob.command_line), and redacted (I11) before anyone sees it; Codex is never told the owner or the project
path (AT-9).

Hosts are the literal loopback IP 127.0.0.1 only (AT-5; user decision D-2026-10-16b): chrome-devtools-mcp 1.10.1
cannot construct the allowlist URLPattern of an [::1] origin (measured in the C8 live check), and an escaped pattern
would need a backslash, which the browser server definition never carries; so `[::1]`, `localhost`, other loopback
spellings, https, wss (any scheme) and ports 80 and 443 are refused with HOST_REFUSED (a fixed sentence). The
listener-table rule still examines every address: another process on ::1, 127.0.0.2 or a wildcard at an attached port
number refuses.

"Ended" in attach mode (I14, AT-7): the Codex tree, any repro or check job and the MCP's node and Chrome (I15) have
ended - confirmed before the proxy is released; the attached ports are not checked.

Tripwire (AT-1): at collect, the script lists every Codex `command_execution` that names an attached port or an HTTP
client (HTTP_CLIENTS, a fixed list), also inside `powershell -Command` strings and `-EncodedCommand` payloads. It is a
tripwire, not a control: Codex's read-only shell can reach the attached servers directly (U7).

Nothing here reads an environment variable (I13).
"""
import base64
import binascii
import ipaddress
import json
import ntpath
from pathlib import Path
import re
import socket
import threading
import time

import browser
from redact import redact
import supervisor
import winjob

MODE = "attach"
HOSTS = ("127.0.0.1",)
# The fixed sentence for any other host (D-2026-10-16b).
HOST_REFUSED = ("Attach mode takes 127.0.0.1 only: the allowlist of chrome-devtools-mcp does not support [::1], so bind "
                "your dev server to 127.0.0.1.")
REFUSED_PORTS = (80, 443)
# I14's closed forwarder list (image names, case-insensitive; any svchost.exe).
FORWARDERS = ("wslrelay.exe", "com.docker.backend.exe", "com.docker.proxy.exe", "vpnkit.exe", "svchost.exe")
# The only access the supervisor ever holds to an attached process (never PROCESS_TERMINATE).
OWNER_ACCESS = winjob.SYNCHRONIZE | winjob.PROCESS_QUERY_LIMITED_INFORMATION
# Seconds; tests substitute them in-process in the attach-start call that writes supervisor-config.json (I13).
TIMING = {"listener_poll": 2.0}
CHECK_PURPOSE = "check"
ALLOWLIST_REFUSAL = "blocked by blocklist/allowlist rules"
NAVIGATION_TIMEOUT = 45
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
# The tripwire's fixed client list (AT-1): (label, pattern), matched case-insensitively.
HTTP_CLIENTS = (
    ("curl", r"(?<![\w-])curl(?:\.exe)?(?![\w-])"),
    ("wget", r"(?<![\w-])wget(?:\.exe)?(?![\w-])"),
    ("Invoke-WebRequest", r"Invoke-WebRequest|(?<![\w-])iwr(?![\w-])"),
    ("Invoke-RestMethod", r"Invoke-RestMethod|(?<![\w-])irm(?![\w-])"),
    ("Net.WebClient", r"Net\.WebClient|System\.Net\.Http|HttpClient|Net\.HttpWebRequest|Start-BitsTransfer"),
    ("python HTTP", r"urllib|http\.client|(?<![\w-])requests\.|httpx|aiohttp|urlopen"),
    ("node HTTP", r"(?<![\w.])fetch\s*\(|require\(\s*['\"](?:node:)?https?['\"]\s*\)|from\s+['\"](?:node:)?https?['\"]|"
                  r"(?<![\w-])https?\.(?:get|request)\s*\(|axios|undici"),
)
# PowerShell's -EncodedCommand under any prefix it accepts (-e, -ec, -enc, ...), then a base64 payload.
ENCODED = re.compile(r"(?<![\w-])-(?:ec|e[a-z]*)\s+['\"]?([A-Za-z0-9+/=]{8,})", re.I)


# --- request validation (exercise.validate calls these for "mode": "attach") ---

def precheck_app(app):
    """A scheme-prefixed entry is refused with attach mode's own message (https, wss, ...; AT-5)."""
    for item in app if isinstance(app, list) else []:
        if isinstance(item, str) and SCHEME.match(item) and not re.fullmatch(r"\[[^\]]*\]:\d*|[^:\[\]]*:\d*", item):
            raise ValueError(f"Attach mode takes http host:port entries only ({item!r}); https, wss and other schemes "
                             "are refused")


def ports_of(origins):
    ports = {}
    for origin in origins:
        ports.setdefault(int(origin.rsplit(":", 1)[1]), []).append(origin)
    return ports


def validate(request, origins):
    """Attach mode's fields (I14): the user's explicit choice, the host 127.0.0.1 only, no 80/443, no copy fields,
    exactly one confirmed owner (PID + creation time) per attached port number."""
    attach = request.get("attach")
    if not isinstance(attach, dict) or attach.get("chosen_by_user") is not True:
        raise ValueError("Attach mode needs the user's explicit choice in this conversation for this exercise "
                         "(attach.chosen_by_user = true); project files and memory never select it")
    unknown = set(attach) - {"chosen_by_user", "owners"}
    if unknown:
        raise ValueError(f"Unknown attach fields: {', '.join(sorted(unknown))}")
    for field in ("commands", "env_files", "exclude_names", "limits"):
        if field in request:
            raise ValueError(f"Attach mode takes no {field}: nothing is copied, installed or started")
    ports = ports_of(origins)
    for port, listed in ports.items():
        for origin in listed:
            if origin.rsplit(":", 1)[0] not in HOSTS:
                raise ValueError(f"{HOST_REFUSED} Refused: {origin}")
        if port in REFUSED_PORTS:
            raise ValueError(f"Ports 80 and 443 are refused in attach mode ({', '.join(listed)})")
    owners = attach.get("owners")
    if not isinstance(owners, list):
        raise ValueError("attach.owners must list the owner of each attached port the user confirmed (attach-owners)")
    confirmed = {}
    for owner in owners:
        if not isinstance(owner, dict) or set(owner) != {"port", "pid", "created"} or \
                any(type(owner[key]) is not int for key in owner) or owner["pid"] <= 0:
            raise ValueError('Each confirmed owner is {"port": <int>, "pid": <int>, "created": <int>}')
        if owner["port"] in confirmed:
            raise ValueError(f"Port {owner['port']} has two confirmed owners")
        confirmed[owner["port"]] = {"pid": owner["pid"], "created": owner["created"]}
    if set(confirmed) != set(ports):
        raise ValueError("attach.owners must name exactly one confirmed owner for each attached port number")
    return confirmed


def parse_app(app):
    """attach-owners: the app list, checked as an attach request's (exercise's origin parser, then I14's hosts)."""
    import exercise
    precheck_app(app)
    if not isinstance(app, list) or not app or len(app) > exercise.MAX_APP_PORTS:
        raise ValueError(f"app must list 1 to {exercise.MAX_APP_PORTS} host:ports")
    origins = []
    for item in app:
        match = exercise.ORIGIN.fullmatch(item) if isinstance(item, str) else None
        if not match:
            raise ValueError(f"Invalid app host:port {item!r}")
        host, port = match.group("host"), match.group("port")
        if host not in HOSTS:
            raise ValueError(f"{HOST_REFUSED} Refused: {item}")
        if not re.fullmatch(r"[1-9][0-9]{0,4}", port) or int(port) > 65535:
            raise ValueError(f"Invalid app port {port!r}")
        if int(port) in REFUSED_PORTS:
            raise ValueError(f"Ports 80 and 443 are refused in attach mode ({item})")
        origin = f"{host}:{int(port)}"
        if origin in origins:
            raise ValueError(f"The app host:port {origin} is listed twice")
        origins.append(origin)
    return origins


# --- the listener table (platform layer: `examine` is replaced by the eval fake) ---

def binding(address):
    """loopback, wildcard, mapped (an IPv4-mapped IPv6 address), other or unknown."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return "unknown"
    if ip.is_unspecified:
        return "wildcard"
    if ip.version == 6 and ip.ipv4_mapped is not None:
        return "mapped"
    return "loopback" if ip.is_loopback else "other"


def describe(pid):
    """(owner, problems): PID, creation time, image path and the redacted command line (I11, AT-9)."""
    created, image = winjob.creation_time(pid), winjob.image_path(pid)
    if created is None or not image:
        return ({"pid": pid, "created": created, "image": image, "name": None, "command_line": None},
                [f"the owner of PID {pid} cannot be read (it exited, or there is no access); refused"])
    name = ntpath.basename(image)
    problems = []
    if name.casefold() in FORWARDERS:
        problems.append(f"PID {pid} is {name}, a port forwarder ({', '.join(FORWARDERS)}): the server behind it cannot "
                        "be confirmed; refused")
    line = winjob.command_line(pid)
    return {"pid": pid, "created": created, "image": image, "name": name,
            "command_line": redact(line) if line is not None else None}, problems


def examine(app, project=None, listeners=None):
    """Per attached port number (I14 listener-table rule): {"port", "origins", "listeners", "owner", "problems"}.
    `listeners` is the table as winjob.tcp_listeners() returns it (read now when None); `project` is unused here
    (the eval fake reads its scenario from it)."""
    table = winjob.tcp_listeners() if listeners is None else listeners
    report = []
    for port, origins in sorted(ports_of(app).items()):
        rows = sorted({(address, pid) for address, number, pid in table if number == port})
        problems = []
        if not rows:
            problems.append(f"nothing listens on port {port}")
        for address, pid in rows:
            shown = f"[{address}]:{port}" if ":" in address else f"{address}:{port}"
            kind = binding(address)
            if pid in (0, 4):
                problems.append(f"{shown} belongs to PID {pid} (System, e.g. http.sys); refused")
            if kind == "wildcard":
                problems.append(f"{shown} is bound to every interface (a wildcard binding); bind the dev server to "
                                "127.0.0.1")
            elif kind == "mapped":
                problems.append(f"{shown} is an IPv4-mapped binding; refused")
            elif kind != "loopback":
                problems.append(f"{shown} is not a loopback address; refused")
        pids = sorted({pid for _, pid in rows})
        if len(pids) > 1:
            problems.append(f"more than one process listens on port {port} (PIDs {', '.join(map(str, pids))}); refused")
        addresses = {address for address, _ in rows}
        for origin in origins:
            wanted = "::1" if origin.startswith("[") else "127.0.0.1"
            if rows and wanted not in addresses:
                problems.append(f"nothing listens on {origin} itself (listening: "
                                f"{', '.join(sorted(addresses))})")
        owner = None
        if len(pids) == 1 and pids[0] not in (0, 4):
            owner, why = describe(pids[0])
            problems += why
        report.append({"port": port, "origins": origins,
                       "listeners": [{"address": address, "pid": pid} for address, pid in rows],
                       "owner": owner, "problems": problems})
    return report


def confirmed_owners(plan):
    return {owner["port"]: {"pid": owner["pid"], "created": owner["created"]} for owner in plan["attach"]["owners"]}


def confirm(app, confirmed, project=None, listeners=None):
    """(problems, owners): problems is empty when the listener table shows exactly the confirmed owners (PID and
    creation time) under the listener-table rule; owners are the recorded owner entries."""
    report = examine(app, project, listeners)
    problems, owners = [], []
    for entry in report:
        problems += entry["problems"]
        want, got = confirmed.get(entry["port"]), entry["owner"]
        if not entry["problems"] and (want is None or got is None or got["pid"] != want["pid"] or
                                      got["created"] != want["created"]):
            problems.append(f"port {entry['port']}: the owner is not the confirmed process (confirmed PID "
                            f"{(want or {}).get('pid')}, now PID {(got or {}).get('pid')}"
                            f"{' with another creation time' if got and want and got['pid'] == want['pid'] else ''})")
        elif not entry["problems"]:
            owners.append({"port": entry["port"], "origins": entry["origins"], "pid": got["pid"],
                           "created": got["created"], "image": got["image"], "name": got["name"],
                           "command_line": got["command_line"]})
    return problems, owners


def owners_command(cli, path):
    """consult.py attach-owners: who owns each attached port, for the user's confirmation. Writes nothing."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ValueError("The attach-owners file cannot be read as JSON") from None
    if not isinstance(data, dict) or set(data) != {"project", "app"}:
        raise ValueError('The attach-owners file must be {"project": "<absolute project directory>", '
                         '"app": ["<host:port>", ...]}')
    project = data["project"]
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z]:[\\/].*|/.*", project, re.S):
        raise ValueError("project must be the absolute project directory")
    origins = parse_app(data["app"])
    report = examine(origins, project)
    problems = [problem for entry in report for problem in entry["problems"]]
    result = {"state": "refused" if problems else "ready", "app": origins, "ports": report}
    if problems:
        result["reason"] = "Attach refused: " + "; ".join(problems)
    else:
        result["owners"] = [{"port": e["port"], "pid": e["owner"]["pid"], "created": e["owner"]["created"]}
                            for e in report]
        result["attached"] = image_pid_list([{**e["owner"], "port": e["port"]} for e in report])
    return result


def image_pid_list(owners):
    """`<image>:<PID>` of each attached process, once each (DS-ATTACH's list; the scope line names only these)."""
    seen = []
    for owner in owners:
        shown = f"{owner.get('name') or ntpath.basename(owner.get('image') or '?')}:{owner['pid']}"
        if shown not in seen:
            seen.append(shown)
    return seen


# --- the supervisor of an attached exercise (I8 attach parts, I12 bounds, I14, U10) ---

class AttachSupervisor(supervisor.Supervisor):
    """Holds the owned proxy port and a SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION handle to each attached
    owner (OWNER_ACCESS; never terminate rights), re-verifies each owner by PID and creation time, then polls the
    listener table every TIMING["listener_poll"] seconds until finish; any change (an owner exited, another process or
    binding on an attached port) runs the ADR 0004 stop path for Codex and stops the exercise. No app job: ending ends
    registered repro and check jobs only. Bounds (I12) count from the attach confirmation (this start)."""

    def __init__(self, consult, directory, plan, config):
        self.consult, self.directory, self.plan = consult, Path(directory), plan
        self.timing = {**supervisor.TIMING, **TIMING, **(config.get("timing") or {})}
        self.app, self.ports = plan["summary"]["app"], []  # the attached ports are never checked at an end (AT-7)
        self.target = plan["summary"]["target"]
        self.commands = {"install": [], "start": []}
        self.confirmed = confirmed_owners(plan)
        me = winjob.current_identity()
        self.state = {"version": 1, "mode": MODE, "pid": me["pid"], "created": me["created"], "state": "starting",
                      "proxy_port": plan["browser"]["proxy_port"], "started_at": time.time(), "apps": [],
                      "members": [], "owner_access": OWNER_ACCESS, "polls": 0}
        self.job = self.proxy = None
        self.processes, self.handled, self.lock = [], set(), threading.Lock()
        self.handles = {}

    def start(self):
        port = self.plan["browser"]["proxy_port"]
        if port in ports_of(self.app):
            raise supervisor.StartFailed("The owned proxy port is one of the attached ports; refused")
        try:
            self.proxy = browser.ProxyHolder(port)
        except ValueError as error:
            raise supervisor.StartFailed(str(error)) from None
        for owner in self.plan["attach"]["owners"]:
            if owner["pid"] in self.handles:
                continue
            handle = winjob.open_verified(owner["pid"], owner["created"], OWNER_ACCESS)
            if not handle:
                raise supervisor.StartFailed(f"The attached process PID {owner['pid']} ({owner.get('name')}) is no "
                                             "longer the confirmed process; nothing was attached")
            self.handles[owner["pid"]] = handle
        problems = self.changes()
        if problems:
            raise supervisor.StartFailed("The attached servers changed since they were confirmed: " +
                                         "; ".join(problems))
        self.write(state="attached", attached_at=time.time(), polled_at=time.time(),
                   owners=[{"pid": o["pid"], "name": o.get("name")} for o in self.plan["attach"]["owners"]])

    def changes(self):
        problems = [f"PID {pid} exited" for pid, handle in self.handles.items() if winjob.wait_handle(handle, 0)]
        found, _ = confirm(self.app, self.confirmed)
        return problems + found

    def watch(self):
        last_snapshot = last_poll = 0.0
        collected_at, bound_tried, changed = None, False, False
        while True:
            data = self.request()
            if data and self.end_by_request(data):
                return
            if not changed and time.monotonic() - last_poll >= self.timing["listener_poll"]:
                last_poll = time.monotonic()
                try:
                    problems = self.changes()
                except Exception as error:  # an unreadable table is a change: the confirmation no longer holds
                    problems = [f"the listener table could not be read ({type(error).__name__})"]
                self.state["polls"] += 1
                self.write(polled_at=time.time())
                if problems:
                    changed = True
                    if self.stop_all("the attached servers changed: " + "; ".join(problems), "owner_changed",
                                     "changed"):
                        return
            if time.monotonic() - last_snapshot >= self.timing["snapshot"]:
                last_snapshot = time.monotonic()
                self.snapshot()
            now = time.time()
            if collected_at is None and (self.directory / "collected").exists():
                collected_at = now
            which = "6 h after the attach confirmation" if now - self.state["started_at"] >= \
                self.timing["bound_after_start"] else "2 h after collect" if collected_at is not None and \
                now - collected_at >= self.timing["bound_after_collect"] else None
            if which and not bound_tried:
                bound_tried = True
                if self.bound(which):
                    return
            time.sleep(self.timing["poll"])

    def bound(self, which):
        return self.stop_all(which, "bound_ended", "bound")

    def stop_all(self, reason, final, key):
        """Stop Codex (ADR 0004), confirm I15's processes ended, end repro and check jobs, remove the target, release
        the proxy; anything unconfirmed keeps proxy and target and records stop_unconfirmed or end_unconfirmed."""
        record = {"reason": reason, "at": time.time(), "codex": self.stop_codex()}
        if not record["codex"]["confirmed"]:
            self.write(state="stop_unconfirmed", **{key: record})
            return False
        record["browser"] = supervisor.codex_processes_ended(
            self.directory, self.plan, supervisor.own_processes(self.directory) | {self.state["pid"]},
            self.timing["browser_patience"])
        if not record["browser"]["confirmed"]:
            self.write(state="stop_unconfirmed", **{key: record})
            return False
        order = []
        if not self.end_jobs(order):
            self.write(state="end_unconfirmed", order=order, **{key: record})
            return False
        import exercise
        record["removal"] = exercise.remove_target(self.directory)
        self.release()
        self.write(state=final, order=order, ended_at=time.time(), **{key: record})
        return True

    def end_jobs(self, order):
        repro = supervisor.end_repro_jobs(self.directory, order, self.timing["end_patience"])
        self.write(repro=repro, listeners=[])
        return repro["confirmed"]

    def release(self):
        if self.proxy is not None:
            self.proxy.close()
            self.proxy = None
        for handle in self.handles.values():
            winjob.close_handle(handle)
        self.handles = {}


# --- the real-definition check (I14: every exercise, never cached, after attach-start) ---

def navigation_class(error, text):
    """How a navigation ended: loaded, allowlist (the MCP allowlist's own refusal, P5), net::ERR_* (a network or
    proxy error), error or no answer."""
    text = text or ""
    if error is None:
        return "no answer"
    if ALLOWLIST_REFUSAL in text:
        return "allowlist"
    found = re.search(r"net::(ERR_[A-Z0-9_]+)", text)
    if found:
        return "net::" + found.group(1)
    return "loaded" if error is False else "error"


def _free_port(avoid):
    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        if port not in avoid:
            return port
    raise ValueError("No free loopback port for the real-definition check")


def _pages(session):
    _, text = session.client.tool("list_pages", {}, timeout=30)
    return {int(m.group(1)) for m in re.finditer(r"^(\d+):", text or "", re.M)}


def check_items(session, plan):
    """The real-definition check's items on an open browser session of the exercise's real definition: each attached
    port reachable (navigation level, any HTTP response); a free loopback port, an external host and the other
    loopback spellings at the attached port numbers each refused by the MCP allowlist itself (not merely a network
    error: the proxy layer is proven by the port-substituted guard); an isolated context under the same limits."""
    items = []

    def add(item, ok, detail=""):
        items.append({"item": item, "ok": bool(ok), "detail": str(detail)[:600]})

    app = plan["summary"]["app"]
    ports = sorted(ports_of(app))
    free = _free_port({*ports, plan["browser"]["proxy_port"]})

    def visit(url, page=None):
        if page is None:
            error, text = session.tool("navigate_page", timeout=NAVIGATION_TIMEOUT, type="url", url=url)
        else:
            try:
                error, text = session.client.tool("navigate_page", {"pageId": page, "type": "url", "url": url},
                                                  timeout=NAVIGATION_TIMEOUT)
            except Exception as failure:  # an unanswered call ends the check (every later item fails)
                session.stuck = str(failure)
                error, text = None, str(failure)
        return navigation_class(error, text), redact(text or "")

    for origin in app:
        kind, text = visit(f"http://{origin}/")
        add(f"attached-{origin}-reachable", kind == "loaded", f"{kind}: {text[:200]}")
    blocked = [("free-loopback-port", f"http://127.0.0.1:{free}/"), ("external-host", "http://example.com/")]
    for port in ports:
        for spelling in ("localhost", "127.0.0.1", "[::1]", "127.0.0.2"):
            origin = f"{spelling}:{port}"
            if origin not in app:
                blocked.append((f"spelling-{spelling}-{port}", f"http://{origin}/"))
    for label, url in blocked:
        kind, text = visit(url)
        add(f"{label}-refused-by-the-allowlist", kind == "allowlist", f"{url}: {kind}: {text[:200]}")
    # An isolated context obeys the same limits.
    try:
        before = _pages(session)
        error, text = session.client.tool("new_page", {"url": f"http://{app[0]}/",
                                                        "isolatedContext": "ask-codex-check"},
                                          timeout=NAVIGATION_TIMEOUT)
        created = sorted(_pages(session) - before)
    except Exception as failure:
        error, text, created = None, str(failure), []
    kind = navigation_class(error, text)
    add("isolated-context-reaches-the-attached-port", kind == "loaded" and created, f"{kind}: {redact(text or '')[:200]}")
    if created:
        for label, url in blocked[:2]:
            kind, text = visit(url, created[0])
            add(f"isolated-context-{label}-refused-by-the-allowlist", kind == "allowlist", f"{url}: {kind}: {text[:200]}")
        try:
            session.client.tool("close_page", {"pageId": created[0]}, timeout=30)
        except Exception:
            pass
    else:
        add("isolated-context-free-loopback-port-refused-by-the-allowlist", False, "no isolated page was created")
    return items


def real_check(cli, directory, plan):
    """Run the real-definition check in its own browser session (repro.open_session with the `check` purpose: own
    siblings, nonce, proxy port and a kill-on-close job registered so that finish and the bounds end it)."""
    import repro
    session = repro.Session()
    items = []
    try:
        with repro.open_session(cli, directory, plan, session, purpose=CHECK_PURPOSE) as opened:
            items = check_items(opened, plan)
    except Exception as error:
        items.append({"item": "real-definition-session", "ok": False,
                      "detail": redact(str(error) if isinstance(error, ValueError) else type(error).__name__)[:600]})
    items.append({"item": "real-definition-session-ended", "ok": session.ended or not session.started,
                  "detail": "the check's job reports no active process" if session.ended else
                  "no browser was started" if not session.started else "the check's job was not confirmed ended"})
    return {"passed": all(item["ok"] for item in items) and len(items) > 1, "items": items}


# --- the tripwire (AT-1) ---

def _decoded(command):
    """The command plus every -EncodedCommand payload it carries, decoded (UTF-16LE base64, as PowerShell takes it)."""
    texts = [command]
    for payload in ENCODED.findall(command):
        try:
            texts.append(base64.b64decode(payload + "=" * (-len(payload) % 4), validate=False).decode("utf-16-le",
                                                                                                    "replace"))
        except (binascii.Error, ValueError):
            continue
    return "\n".join(texts)


def tripwire(events, app):
    """Every Codex command_execution (once per item) that names an attached port or an HTTP client of HTTP_CLIENTS;
    [{"command": <redacted, cut>, "names": [...]}]."""
    ports = sorted(ports_of(app))
    found, seen = [], set()
    try:
        lines = Path(events).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "command_execution":
            continue
        command = item.get("command")
        if not isinstance(command, str):
            continue
        key = item.get("id") or command
        if key in seen:
            continue
        seen.add(key)
        text = _decoded(command)
        names = [f"port {port}" for port in ports if re.search(rf"(?<![0-9]){port}(?![0-9])", text)]
        names += [label for label, pattern in HTTP_CLIENTS if re.search(pattern, text, re.I)]
        if names:
            shown = redact(command)
            found.append({"command": shown if len(shown) <= 500 else shown[:500] + " ...", "names": names})
    return found
