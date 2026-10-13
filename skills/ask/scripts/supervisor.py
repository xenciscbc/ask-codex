"""The app's processes of an exercise under a supervisor (plan `.scratch/exercise-skills/plan.md` claim C4; I2
post-install condition, I3 precondition, I8, I12 bounds, I15, U10). Windows only.

    consult.py app-start <run directory>   after a current guard pass and before `run`: start the supervisor, which
                                           holds the owned proxy port and the app job for the whole exercise, runs
                                           the install commands, refuses links in the target that resolve outside
                                           it, runs the start commands and confirms that every app port answers
                                           from a loopback-only listener of a process in the job

Request field (exercise.validate checks it at prepare; app-start requires it):

    "commands": {"install": [<command>, ...], "start": [<command>, ...]}
    <command> = {"argv": ["<program>", "<arg>", ...]} or {"shell": "<command line for cmd /d /s /c>"},
                optional "cwd": "<relative directory inside the target>" (default: the target itself),
                optional "env": {"<NAME>": "<value>", ...} (the user-confirmed variables)

Commands run verbatim: an argv command's program is an absolute .exe/.com path or a bare name found on the app
environment's PATH (absolute entries only); a shell command runs as `<system>\\cmd.exe /d /s /c "<command>"`. The
working directory must be inside the target and reached through no link. The environment is the allowlisted system
variables (SYSTEM_ENV) plus the command's own variables.

Supervisor process (`python supervisor.py serve <run directory>`, started by app-start with breakaway from the
caller's job where that is permitted, otherwise without; working directory the run directory's parent, outside the
target). It creates the app job (winjob.Job: unguessable name, an existing name refuses, kill-on-close, no breakaway,
the supervisor holds its only handle and is not a member) and the owned proxy port's listener (browser.ProxyHolder).
Every app command is created suspended, assigned to the job and resumed (winjob.start_suspended), inheriting only
its stdio pipes. Before any command no listener may be on an app port; after the start commands every listener on an
app port number must belong to a process in the job and be bound to loopback, and each app host:port must accept a
connection; otherwise the start fails with the app's output. If the supervisor dies, kill-on-close ends the app.

Run directory files:
    supervisor-config.json   written once by app-start (its exclusive create is the "attempted once" receipt):
                             timing (TIMING, substituted in-process by tests)
    supervisor-process.json  the supervisor's identity (PID + creation time) as app-start started it
    supervisor.json          the supervisor's status: state, job name, app processes (kind, index, PID, creation
                             time, exit code), job members seen, failure and output, end order, bound
    supervisor-request.json  {"id", "action": "end"}: stop, finish and cleanup signal the supervisor through it
    app-<kind>-<n>.log       each command's stdout and stderr
    codex-processes.json     I15: Codex's descendants recorded every 2 s while Codex runs (PID, creation time, image)
    repro-jobs/<job name>    a running repro registers its job here (C6); bounds and finish end it before the app job

States: starting -> app_started; start_failed (the app was ended; app-start removes the target); ended (an end
request; the proxy is released and the supervisor exits); end_unconfirmed (an end could not be confirmed: proxy, job
and target are kept); stop_unconfirmed (a bound's Codex stop or I15 check is unconfirmed: everything is kept);
bound_ended (a lifetime bound ended everything and removed the target; the run directory is left for cleanup).

Lifetime bounds (I12): 2 h after `collect`, 6 h after the app start in any state. At a bound the supervisor runs the
ADR 0004 stop path for the Codex tree if Codex runs, confirms I15's processes ended, ends registered repro jobs and
then the app job, confirms "ended" (no active process in the job, no listener on an app port), removes the target and
exits; an unconfirmed step keeps the proxy listener, the job and the target and records stop_unconfirmed.

I15: while Codex runs, the supervisor records Codex's descendants (from the root run.sh records, verified by its
creation time) every 2 s. At an end, recorded processes are terminated through a handle checked against the recorded
creation time; any process whose command line holds the run's nonce, whose `--user-data-dir` lies in a run-owned
directory, or whose working directory lies in the MCP's cwd or TEMP is recognised and reported, never terminated.
The script's own processes (the CLI call, the supervisor, the run wrapper) are excluded.

U10: `run` holds a SYNCHRONIZE handle to the supervisor (Watcher) and, when it dies while Codex runs, stops the Codex
tree through the ADR 0004 path at once.

The only environment read here builds the app's environment from SYSTEM_ENV (I13: nothing is selected, skipped or
substituted by a variable).
"""
import ipaddress
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import threading
import time

import browser
import target as disposable_target
import winjob

HERE = Path(__file__).resolve().parent
CONFIG, PROCESS, STATUS, REQUEST = ("supervisor-config.json", "supervisor-process.json", "supervisor.json",
                                    "supervisor-request.json")
CODEX_PROCESSES, REPRO_JOBS, LOG = "codex-processes.json", "repro-jobs", "supervisor.log"
APP_JOB_PREFIX, REPRO_JOB_PREFIX = "ask-codex-app", "ask-codex-repro"
APP_JOB = re.compile(r"^ask-codex-app-[0-9a-f]{32}$")
REPRO_JOB = re.compile(r"^ask-codex-repro-[0-9a-f]{32}$")
# Seconds. Tests substitute these in-process in the CLI call that writes supervisor-config.json (I13).
TIMING = {"install_timeout": 1800.0, "start_timeout": 180.0, "end_patience": 15.0, "respond": 30.0,
          "bound_after_collect": 2 * 3600.0, "bound_after_start": 6 * 3600.0, "poll": 0.25, "snapshot": 2.0,
          "browser_patience": 5.0}
MAX_COMMANDS, MAX_ARGS, MAX_ARG, MAX_SHELL, MAX_ENV = 8, 64, 4096, 8000, 64
OUTPUT_TAIL = 4000
SYSTEM_ENV = ("SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATHEXT", "PATH", "TEMP", "TMP", "USERPROFILE",
              "HOMEDRIVE", "HOMEPATH", "USERNAME", "USERDOMAIN", "APPDATA", "LOCALAPPDATA", "PROGRAMDATA",
              "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)",
              "COMMONPROGRAMW6432", "ALLUSERSPROFILE", "PUBLIC", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE",
              "PROCESSOR_IDENTIFIER", "OS", "COMPUTERNAME")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
TERMINAL = ("app_started", "start_failed", "ended", "end_unconfirmed", "stop_unconfirmed", "bound_ended")
DETACHED, NEW_GROUP, BREAKAWAY = 0x8, 0x200, 0x01000000

# Set when this process ends the supervisor on purpose (finish, stop, cleanup, a failure path): a Watcher in the
# same process must not take that for the supervisor's death.
_INTENTIONAL = threading.Event()


# --- files (atomic replace; Windows sharing violations are retried) ---

def _write(path, data):
    path = Path(path)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    deadline = time.monotonic() + 5
    while True:
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


def _read(path):
    deadline = time.monotonic() + 2
    while True:
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (PermissionError, ValueError):
            if time.monotonic() >= deadline:
                return None
            time.sleep(0.05)


def status(directory):
    return _read(Path(directory) / STATUS)


# --- request validation (exercise.validate, at prepare) ---

def _relative_parts(cwd):
    if not isinstance(cwd, str) or len(cwd) > 260 or "\0" in cwd:
        raise ValueError("An app command's working directory must be a relative path inside the target")
    if cwd in ("", "."):
        return []
    if re.match(r"^[A-Za-z]:", cwd) or cwd.startswith(("\\", "/")):
        raise ValueError(f"The working directory {cwd!r} is outside the target (absolute, drive or UNC path); "
                         "give a path relative to the project")
    parts = re.split(r"[\\/]", cwd.rstrip("\\/"))
    for part in parts:
        if part in (".", ".."):
            raise ValueError(f"The working directory {cwd!r} may lead outside the target ('.' or '..')")
        if not disposable_target._valid_component(part):
            raise ValueError(f"The working directory {cwd!r} has an invalid component {part!r}")
    return parts


def _validate_command(command, label):
    if not isinstance(command, dict) or set(command) - {"argv", "shell", "cwd", "env"} or \
            ("argv" in command) == ("shell" in command):
        raise ValueError(f"{label}: a command is {{\"argv\": [...]}} or {{\"shell\": \"...\"}}, with optional cwd "
                         "and env")
    if "argv" in command:
        argv = command["argv"]
        if not isinstance(argv, list) or not 1 <= len(argv) <= MAX_ARGS or any(
                not isinstance(a, str) or not a or len(a) > MAX_ARG or "\0" in a for a in argv):
            raise ValueError(f"{label}: argv must be 1 to {MAX_ARGS} non-empty strings")
    else:
        shell = command["shell"]
        if not isinstance(shell, str) or not shell.strip() or len(shell) > MAX_SHELL or \
                any(c in shell for c in "\0\r\n"):
            raise ValueError(f"{label}: a shell command is one line of at most {MAX_SHELL} characters")
    _relative_parts(command.get("cwd", ""))
    env = command.get("env", {})
    if not isinstance(env, dict) or len(env) > MAX_ENV:
        raise ValueError(f"{label}: env must be an object of at most {MAX_ENV} variables")
    for name, value in env.items():
        if not ENV_NAME.fullmatch(name) or not isinstance(value, str) or len(value) > 32767 or "\0" in value:
            raise ValueError(f"{label}: invalid environment variable {name!r}")


def validate_commands(commands):
    if not isinstance(commands, dict) or set(commands) - {"install", "start"}:
        raise ValueError("commands must be {\"install\": [...], \"start\": [...]}")
    install, start = commands.get("install", []), commands.get("start")
    if not isinstance(install, list) or len(install) > MAX_COMMANDS:
        raise ValueError(f"At most {MAX_COMMANDS} install commands")
    if not isinstance(start, list) or not 1 <= len(start) <= MAX_COMMANDS:
        raise ValueError(f"commands.start needs 1 to {MAX_COMMANDS} app start commands")
    for kind, items in (("install", install), ("start", start)):
        for index, command in enumerate(items):
            _validate_command(command, f"commands.{kind}[{index}]")
    return {"install": install, "start": start}


# --- the app's command, working directory and environment ---

def command_cwd(target, cwd):
    """<target>\\<cwd>: every component an existing plain directory (no link, I8)."""
    path = str(target)
    for part in _relative_parts(cwd):
        path = ntpath.join(path, part)
        try:
            attributes = os.lstat(path).st_file_attributes
        except OSError:
            raise ValueError(f"The working directory {cwd!r} does not exist in the target") from None
        if attributes & disposable_target.ATTR_REPARSE or not attributes & disposable_target.ATTR_DIRECTORY:
            raise ValueError(f"The working directory {cwd!r} passes through a link or is not a directory")
    return path


def app_environment(extra):
    """Allowlisted system variables from this process's environment, then the user-confirmed ones."""
    env = {}
    for key, value in os.environ.items():
        if key.upper() in SYSTEM_ENV:
            env[key.upper()] = value
    for name, value in extra.items():
        for key in [k for k in env if k.upper() == name.upper()]:
            del env[key]
        env[name] = value
    return env


def _env_value(env, name):
    return next((value for key, value in env.items() if key.upper() == name), None)


def program_for(command, env):
    """(application path, command line) for CreateProcessW."""
    if "shell" in command:
        cmd = ntpath.join(winjob.system_directory(), "cmd.exe")
        return cmd, f'"{cmd}" /d /s /c "{command["shell"]}"'
    argv = command["argv"]
    name = argv[0]
    if re.match(r"^[A-Za-z]:[\\/]", name):
        found = name if os.path.isfile(name) else None
    elif any(c in name for c in "\\/:"):
        raise ValueError(f"The program {name!r} must be an absolute path or a name on PATH")
    else:
        found = None
        names = [name] if ntpath.splitext(name)[1] else [name + ".exe", name + ".com"]
        for entry in (_env_value(env, "PATH") or "").split(";"):
            entry = entry.strip().strip('"')
            if not re.match(r"^[A-Za-z]:[\\/]", entry):
                continue
            found = next((ntpath.join(entry, n) for n in names if os.path.isfile(ntpath.join(entry, n))), None)
            if found:
                break
    if not found:
        raise ValueError(f"The program {name!r} was not found")
    if ntpath.splitext(found)[1].lower() not in (".exe", ".com"):
        raise ValueError(f"The program {name!r} is not an .exe or .com file; give batch files as a shell command")
    return found, subprocess.list2cmdline([found, *argv[1:]])


def shown(command):
    return command["shell"] if "shell" in command else subprocess.list2cmdline(command["argv"])


# --- I2 post-install condition: no link inside the target resolves outside it ---

def outside_links(directory):
    """Links (reparse points) in the recorded target that resolve outside it or cannot be resolved; none followed
    while walking."""
    t = disposable_target
    found = []
    with t._placeholders_exposed():
        _, record = t.record_at(directory)
        [entry] = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
        root = t._verified_root(record)
        try:
            handle = t._nt_open(root, ntpath.basename(entry["path"]), t.LIST_DIRECTORY | t.TRAVERSE |
                                t.READ_ATTRIBUTES, t.DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
        finally:
            t._close(root)
        try:
            attributes, _ = t._attribute_tag(handle)
            if attributes & t.ATTR_REPARSE or t._identity(handle) != {"volume_serial": entry.get("volume_serial"),
                                                                       "file_id": entry.get("file_id")}:
                raise ValueError("The target no longer matches the record")
            final = t._final_path(handle).casefold().rstrip("\\")
            _walk_links(handle, entry["path"], (), final, found)
        finally:
            t._close(handle)
    return found


def _walk_links(handle, base, parts, final, found):
    t = disposable_target
    for name, attributes, _, _ in t._list(handle):
        rel = parts + (name,)
        if attributes & (t.ATTR_REPARSE | t.RECALL_ATTRIBUTES):
            path = "\\\\?\\" + ntpath.join(base, *rel)
            try:
                link = t._win_open(path, t.READ_ATTRIBUTES, t.FLAG_BACKUP_SEMANTICS)  # follows the link
                try:
                    resolved = t._final_path(link).casefold().rstrip("\\")
                finally:
                    t._close(link)
            except OSError:
                resolved = None
            if resolved is None or not (resolved == final or resolved.startswith(final + "\\")):
                found.append("/".join(rel) + (" (cannot be resolved)" if resolved is None else ""))
        elif attributes & t.ATTR_DIRECTORY:
            child = t._nt_open(handle, name, t.LIST_DIRECTORY | t.TRAVERSE | t.READ_ATTRIBUTES,
                               t.DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
            try:
                if t._attribute_tag(child)[0] & t.ATTR_REPARSE:
                    found.append("/".join(rel))
                else:
                    _walk_links(child, base, rel, final, found)
            finally:
                t._close(child)


# --- ports ---

def app_ports(app):
    return sorted({int(origin.rsplit(":", 1)[1]) for origin in app})


def _addresses(host):
    return {"127.0.0.1": [(socket.AF_INET, "127.0.0.1")], "[::1]": [(socket.AF_INET6, "::1")],
            "localhost": [(socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")]}[host]


def answers(origin, timeout=1.0):
    host, port = origin.rsplit(":", 1)
    for family, address in _addresses(host):
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.settimeout(timeout)
            try:
                probe.connect((address, int(port)))
                return True
            except OSError:
                continue
    return False


def _loopback(address):
    try:
        return ipaddress.ip_address(address).is_loopback
    except ValueError:
        return False


def listeners_on(ports):
    return [(a, p, pid) for a, p, pid in winjob.tcp_listeners() if p in ports]


def wait_no_listeners(ports, patience):
    deadline = time.monotonic() + patience
    while True:
        left = listeners_on(ports)
        if not left or time.monotonic() >= deadline:
            return [f"{a}:{p} (PID {pid})" for a, p, pid in left]
        time.sleep(0.2)


# --- I15: Codex-launched processes ---

def _within(path, directory):
    def norm(value):
        value = str(value).replace("/", "\\")
        if value.startswith("\\\\?\\"):
            value = value[4:]
        return ntpath.normpath(value).casefold().rstrip("\\")
    p, d = norm(path), norm(directory)
    return p == d or p.startswith(d + "\\")


USER_DATA_DIR = re.compile(r'--user-data-dir=(?:"([^"]*)"|(\S+))', re.I)


def descendants(root, created):
    """Descendants of the process (root, created): a child counts only if created after its parent (PID reuse)."""
    children = {}
    for pid, parent, image in winjob.processes():
        if pid != parent:
            children.setdefault(parent, []).append((pid, image))
    found, queue, seen = [], [(root, created)], {root}
    while queue:
        pid, since = queue.pop()
        for child, image in children.get(pid, []):
            if child in seen:
                continue
            born = winjob.creation_time(child)
            if born is None or born < since:
                continue
            seen.add(child)
            found.append({"pid": child, "created": born, "image": image})
            queue.append((child, born))
    return found


def snapshot_codex(directory):
    """Record Codex's descendants while it runs (I15); the root is the one run.sh recorded, by identity."""
    child = Path(directory) / "0"
    if not (child / "pid").exists() or (child / "launcher-result.json").exists() or (child / "result.json").exists():
        return []
    fields = {}
    for line in (child / "pid").read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        fields[key.strip()] = value.strip()
    if not fields.get("pid", "").isdigit() or not fields.get("identity", "").isdigit():
        return []
    root, identity = int(fields["pid"]), int(fields["identity"])
    created = winjob.creation_time(root)
    if created is None or winjob.dotnet_ticks(created) != identity:
        return []
    found = descendants(root, created)
    if found:
        path = Path(directory) / CODEX_PROCESSES
        recorded = _read(path) or []
        known = {(r["pid"], r["created"]) for r in recorded}
        new = [r for r in found if (r["pid"], r["created"]) not in known]
        if new:
            _write(path, recorded + new)
    return found


def own_processes(directory):
    """PIDs of the script's own processes for this exercise (never counted by I15): the supervisor, the run."""
    own = set()
    for name in (PROCESS, "started"):
        identity = _read(Path(directory) / name)
        if isinstance(identity, dict) and winjob.alive(identity.get("pid"), identity.get("created")):
            own.add(identity["pid"])
    return own


def recognise(directory, plan, exclude):
    b = plan["browser"]
    nonce = plan["summary"]["browser_server"].casefold()
    owned, cwd_owned = (b["cwd"], b["temp"], b["profile"]), (b["cwd"], b["temp"])
    found = []
    for pid, _, image in winjob.processes():
        if pid in exclude or pid in (0, 4):
            continue
        why = None
        line = winjob.command_line(pid)
        if line:
            if nonce in line.casefold():
                why = "its command line holds the run's nonce"
            elif any(_within(a or b_, d) for a, b_ in USER_DATA_DIR.findall(line) for d in owned):
                why = "its --user-data-dir lies in a run-owned directory"
        if why is None:
            cwd = winjob.current_directory(pid)
            if cwd and any(_within(cwd, d) for d in cwd_owned):
                why = "its working directory lies in the MCP's cwd or TEMP"
        if why:
            found.append({"pid": pid, "created": winjob.creation_time(pid), "image": winjob.image_path(pid) or image,
                          "source": "recognised", "why": why})
    return found


def codex_processes_ended(directory, plan, exclude, patience=None):
    """I15 "ended": recorded processes terminated by verified handle; recorded or recognised ones still alive after
    `patience` are reported (PID, image), recognised ones are never terminated."""
    patience = TIMING["browser_patience"] if patience is None else patience
    recorded = [r for r in (_read(Path(directory) / CODEX_PROCESSES) or []) if isinstance(r, dict)]
    terminated = []
    for r in recorded:
        if winjob.terminate_verified(r.get("pid"), r.get("created")) == "terminated":
            terminated.append({"pid": r["pid"], "image": r.get("image")})
    keys = {(r.get("pid"), r.get("created")) for r in recorded}
    deadline = time.monotonic() + patience
    while True:
        alive = [{"pid": r["pid"], "image": r.get("image"), "source": "recorded"} for r in recorded
                 if winjob.alive(r.get("pid"), r.get("created"))]
        alive += [r for r in recognise(directory, plan, exclude) if (r["pid"], r["created"]) not in keys]
        if not alive or time.monotonic() >= deadline:
            return {"confirmed": not alive, "recorded": len(recorded), "terminated": terminated,
                    "alive": [{k: v for k, v in r.items() if k != "created"} for r in alive]}
        time.sleep(0.5)


# --- registered repro jobs (C6 registers; C4 ends them before the app job) ---

def end_repro_jobs(directory, order, patience):
    folder = Path(directory) / REPRO_JOBS
    try:
        attributes = os.lstat(folder).st_file_attributes
    except OSError:
        return {"confirmed": True, "jobs": []}
    if attributes & disposable_target.ATTR_REPARSE or not attributes & disposable_target.ATTR_DIRECTORY:
        return {"confirmed": False, "jobs": [], "reason": "the repro registration directory is not a plain directory"}
    jobs = []
    for name in sorted(os.listdir(folder)):
        if not REPRO_JOB.fullmatch(name):
            jobs.append({"job": name, "ended": False, "reason": "not a repro job name; never opened"})
            continue
        handle = winjob.open_job(name)
        if handle is None:
            jobs.append({"job": name, "ended": True, "state": "gone"})
            continue
        try:
            ended = winjob.job_active(handle) == 0
            if not ended:
                ended = winjob.terminate_job(handle, patience)
                order.append({"job": name, "kind": "repro", "at": time.time(), "ended": ended})
        finally:
            winjob.close_handle(handle)
        jobs.append({"job": name, "ended": ended})
    return {"confirmed": all(j["ended"] for j in jobs), "jobs": jobs}


# --- the supervisor process ---

class StartFailed(Exception):
    pass


class StartStopped(Exception):
    def __init__(self, request):
        super().__init__("stopped")
        self.request = request


class Supervisor:
    def __init__(self, consult, directory, plan, config):
        self.consult, self.directory, self.plan = consult, Path(directory), plan
        self.timing = {**TIMING, **(config.get("timing") or {})}
        self.app = plan["summary"]["app"]
        self.ports = app_ports(self.app)
        self.target = plan["summary"]["target"]
        self.commands = validate_commands(plan["request"].get("commands"))
        me = winjob.current_identity()
        self.state = {"version": 1, "pid": me["pid"], "created": me["created"], "state": "starting",
                      "proxy_port": plan["browser"]["proxy_port"], "started_at": time.time(), "apps": [],
                      "members": []}
        self.job = self.proxy = None
        self.processes, self.handled, self.lock = [], set(), threading.Lock()

    def write(self, **fields):
        self.state.update(fields)
        _write(self.directory / STATUS, self.state)

    def request(self):
        data = _read(self.directory / REQUEST)
        if isinstance(data, dict) and data.get("action") == "end" and isinstance(data.get("id"), str) and \
                data["id"] not in self.handled:
            return data
        return None

    def check_request(self):
        data = self.request()
        if data:
            raise StartStopped(data)

    def main(self):
        self.write()
        try:
            self.start()
        except StartStopped as stopped:
            if self.end_by_request(stopped.request):
                return
        except StartFailed as failure:
            if self.start_failed(str(failure)):
                return
        except Exception as error:  # never leave the app running unreported
            if self.start_failed(f"{type(error).__name__}: the app start failed ({error})"):
                return
        self.watch()

    # start

    def start(self):
        port = self.plan["browser"]["proxy_port"]
        if port in self.ports:
            raise StartFailed("The owned proxy port is one of the app ports; refused")
        try:
            self.proxy = browser.ProxyHolder(port)
        except ValueError as error:
            raise StartFailed(str(error)) from None
        try:
            self.job = winjob.Job(APP_JOB_PREFIX)
        except OSError as error:
            raise StartFailed(f"The app job could not be created: {error}") from None
        self.write(job=self.job.name)
        self.ports_free()
        for index, command in enumerate(self.commands["install"]):
            self.install(index, command)
        if self.commands["install"]:
            links = outside_links(self.directory)
            if links:
                raise StartFailed("After the install commands, links inside the target resolve outside it (I2): "
                                  + ", ".join(links[:20]))
            self.ports_free()
        started = []
        for index, command in enumerate(self.commands["start"]):
            self.check_request()
            started.append(self.launch("start", index, command))
        self.wait_ports(started)
        self.write(state="app_started", app_started_at=time.time())

    def ports_free(self):
        busy = listeners_on(self.ports)
        if busy:
            raise StartFailed("App port(s) in use before the app start: " +
                              ", ".join(f"{a}:{p} (PID {pid})" for a, p, pid in busy))

    def launch(self, kind, index, command):
        try:
            cwd = command_cwd(self.target, command.get("cwd", ""))
            env = app_environment(command.get("env", {}))
            program, line = program_for(command, env)
        except ValueError as error:
            raise StartFailed(f"{kind} command {index + 1}: {error}") from None
        log = self.directory / f"app-{kind}-{index}.log"
        process = winjob.start_suspended(self.job, [program], cwd, env, command_line=line)
        self.processes.append(process)
        process.stdin.close()
        entry = {"kind": kind, "index": index, "pid": process.pid, "created": winjob.handle_creation(process.handle),
                 "log": log.name, "command": shown(command)}
        self.state["apps"].append(entry)
        self.write()
        sink = log.open("ab")
        for stream in (process.stdout, process.stderr):
            threading.Thread(target=self._drain, args=(stream, sink), daemon=True).start()
        return process, entry

    def _drain(self, stream, sink):
        while True:
            try:
                chunk = stream.read(65536)
            except OSError:
                return
            if not chunk:
                return
            with self.lock:
                try:
                    sink.write(chunk)
                    sink.flush()
                except (OSError, ValueError):
                    return

    def install(self, index, command):
        process, entry = self.launch("install", index, command)
        deadline = time.monotonic() + self.timing["install_timeout"]
        while not process.wait(self.timing["poll"]):
            self.check_request()
            if time.monotonic() >= deadline:
                raise StartFailed(f"install command {index + 1} did not finish within "
                                  f"{self.timing['install_timeout']:g} s")
        entry["exit_code"] = process.poll()
        self.write()
        if entry["exit_code"] != 0:
            raise StartFailed(f"install command {index + 1} failed (exit {entry['exit_code']})")

    def exited(self, started):
        """A start command's own process that exited with a non-zero code fails the start (exit 0 is allowed: a
        command may hand the app to a child, as `cmd /c start` does)."""
        for process, entry in started:
            code = process.poll()
            if code is not None and entry.get("exit_code") is None:
                entry["exit_code"] = code
                self.write()
                if code != 0:
                    raise StartFailed(f"start command {entry['index'] + 1} exited with code {code}")

    def wait_ports(self, started):
        deadline = time.monotonic() + self.timing["start_timeout"]
        while True:
            self.check_request()
            self.exited(started)
            found = listeners_on(self.ports)
            members = set(self.job.pids())
            problems, listening = [], set()
            for address, port, pid in found:
                if pid not in members:
                    problems.append(f"{address}:{port} (PID {pid}) does not belong to the app job")
                elif not _loopback(address):
                    problems.append(f"{address}:{port} (PID {pid}) is not bound to loopback only")
                else:
                    listening.add(port)
            if problems:
                raise StartFailed("App listener refused: " + "; ".join(problems))
            waiting = [o for o in self.app if int(o.rsplit(":", 1)[1]) not in listening or not answers(o)]
            if not waiting:
                self.exited(started)
                return
            if self.job.active_processes() == 0:
                raise StartFailed("Every app process exited before " + ", ".join(waiting) + " answered")
            if time.monotonic() >= deadline:
                raise StartFailed(f"App port(s) never answered within {self.timing['start_timeout']:g} s: "
                                  + ", ".join(waiting))
            time.sleep(self.timing["poll"])

    def output(self):
        return output(self.directory, self.state)

    def start_failed(self, reason):
        order = []
        ended = self.end_jobs(order)
        failure = {"reason": reason, "output": self.output()}
        if ended:
            self.release()
            self.write(state="start_failed", failure=failure, order=order, ended_at=time.time())
            return True
        self.write(state="end_unconfirmed", phase="start", failure=failure, order=order)
        return False

    # running

    def watch(self):
        last, collected_at, bound_tried = 0.0, None, False
        while True:
            data = self.request()
            if data and self.end_by_request(data):
                return
            if time.monotonic() - last >= self.timing["snapshot"]:
                last = time.monotonic()
                self.snapshot()
            now = time.time()
            if collected_at is None and (self.directory / "collected").exists():
                collected_at = now
            which = "6 h after the app start" if now - self.state["started_at"] >= self.timing["bound_after_start"] \
                else "2 h after collect" if collected_at is not None and \
                now - collected_at >= self.timing["bound_after_collect"] else None
            if which and not bound_tried:
                bound_tried = True
                if self.bound(which):
                    return
            time.sleep(self.timing["poll"])

    def snapshot(self):
        try:
            snapshot_codex(self.directory)
        except Exception:
            pass
        if self.job is None:
            return
        try:
            known = {(m["pid"], m["created"]) for m in self.state["members"]}
            new = []
            for pid in self.job.pids():
                created = winjob.creation_time(pid)
                if created is not None and (pid, created) not in known:
                    new.append({"pid": pid, "created": created})
            if new:
                self.write(members=self.state["members"] + new)
        except OSError:
            pass

    # ending

    def end_jobs(self, order):
        patience = self.timing["end_patience"]
        repro = end_repro_jobs(self.directory, order, patience)
        app = True
        if self.job is not None:
            app = self.job.terminate(patience)
            order.append({"job": self.job.name, "kind": "app", "at": time.time(), "ended": app})
        # The app ports are the app's once an app process was started; before that a listener is not the app's.
        left = wait_no_listeners(self.ports, patience) if self.state["apps"] else []
        self.write(repro=repro, listeners=left)
        return repro["confirmed"] and app and not left

    def release(self):
        if self.proxy is not None:
            self.proxy.close()
            self.proxy = None
        if self.job is not None:
            self.job.close()
            self.job = None
        for process in self.processes:
            process.close()

    def end_by_request(self, data):
        self.handled.add(data["id"])
        order = []
        if self.end_jobs(order):
            self.release()
            self.write(state="ended", request=data["id"], order=order, ended_at=time.time())
            return True
        self.write(state="end_unconfirmed", request=data["id"], order=order)
        return False

    def stop_codex(self):
        c, child = self.consult, self.directory / "0"
        if not (self.directory / "clock.json").exists() or not child.exists():
            return {"state": "not_started", "confirmed": True}
        stopped = c.stop_status(child)
        if c.result_for(child) is not None and (stopped is None or stopped.get("confirmed")):
            return {"state": "stopped" if stopped else "finished", "confirmed": True}
        try:
            result = c.stop_codex(self.directory, self.plan, "stop", "none")
        except Exception as error:
            return {"state": "stop_unconfirmed", "confirmed": False, "reason": f"{type(error).__name__}: {error}"}
        return {"state": result["state"], "confirmed": result["state"] in ("stopped", "finished"),
                "stops": result.get("stops", [])}

    def bound(self, which):
        record = {"bound": which, "at": time.time(), "codex": self.stop_codex()}
        if not record["codex"]["confirmed"]:
            self.write(state="stop_unconfirmed", bound=record)
            return False
        record["browser"] = codex_processes_ended(self.directory, self.plan, own_processes(self.directory) |
                                                  {os.getpid()}, self.timing["browser_patience"])
        if not record["browser"]["confirmed"]:
            self.write(state="stop_unconfirmed", bound=record)
            return False
        order = []
        if not self.end_jobs(order):
            self.write(state="end_unconfirmed", bound=record, order=order)
            return False
        import exercise
        record["removal"] = exercise.remove_target(self.directory)
        self.release()
        self.write(state="bound_ended", bound=record, order=order, ended_at=time.time())
        return True


def output(directory, state):
    """Each command's output tail (stdout and stderr) for the report."""
    shown_output = []
    for app in (state or {}).get("apps", []):
        log = Path(directory) / str(app.get("log", ""))
        text = ""
        if re.fullmatch(r"app-(install|start)-\d+\.log", log.name) and log.is_file():
            with log.open("rb") as source:
                source.seek(max(0, log.stat().st_size - OUTPUT_TAIL))
                text = source.read().decode("utf-8", "replace")
        shown_output.append({"kind": app.get("kind"), "index": app.get("index"), "command": app.get("command"),
                             "exit_code": app.get("exit_code"), "output": text})
    return shown_output


def serve(directory):
    disposable_target.require_windows()
    import consult
    directory, plan = consult.plan_at(directory)
    config = _read(directory / CONFIG) or {}
    Supervisor(consult, directory, plan, config).main()


# --- the CLI side: start, require, end ---

def command(directory):
    """The supervisor's command line (tests substitute this function in-process)."""
    return [sys.executable, str(HERE / "supervisor.py"), "serve", str(directory)]


def launch(directory):
    """Start the supervisor detached, with breakaway from the caller's job where permitted (I8)."""
    directory = Path(directory)
    log = (directory / LOG).open("ab")
    try:
        try:
            process = subprocess.Popen(command(directory), cwd=str(directory.parent), stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, close_fds=True,
                                       creationflags=DETACHED | NEW_GROUP | BREAKAWAY)
            breakaway = True
        except OSError as error:
            if getattr(error, "winerror", None) != 5:  # ERROR_ACCESS_DENIED: the caller's job forbids breakaway
                raise
            process = subprocess.Popen(command(directory), cwd=str(directory.parent), stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, close_fds=True, creationflags=DETACHED | NEW_GROUP)
            breakaway = False
    finally:
        log.close()
    identity = {"pid": process.pid, "created": winjob.handle_creation(int(process._handle)), "breakaway": breakaway}
    _write(directory / PROCESS, identity)
    return identity, process


def wait_started(directory, identity, process, timing, installs):
    deadline = time.monotonic() + timing["install_timeout"] * installs + timing["start_timeout"] + 60
    while True:
        current = status(directory)
        if isinstance(current, dict) and current.get("pid") == identity["pid"] and current.get("state") in TERMINAL:
            return current
        if process.poll() is not None:
            current = status(directory)
            return {**(current or {}), "state": "died",
                    "failure": {"reason": "The app supervisor ended before the app started",
                                "output": output(directory, current)}}
        if time.monotonic() >= deadline:
            return {**(current or {}), "state": "timeout",
                    "failure": {"reason": "The app start did not finish in time", "output": output(directory, current)}}
        time.sleep(0.2)


def require_started(directory, plan):
    """`run`: the supervisor runs, its app started, it holds the owned proxy port, every app port answers."""
    directory = Path(directory)
    current, identity = status(directory), _read(directory / PROCESS)
    if not (directory / CONFIG).exists() or not isinstance(current, dict) or not isinstance(identity, dict):
        raise ValueError("The app has not been started for this exercise (app-start); Codex does not start")
    if current.get("state") != "app_started":
        raise ValueError(f"The app is not running (supervisor state {current.get('state')}); Codex does not start")
    if current.get("pid") != identity.get("pid") or not winjob.alive(identity.get("pid"), identity.get("created")):
        raise ValueError("The app supervisor is not running; Codex does not start")
    port = plan["browser"]["proxy_port"]
    owners = {pid for _, p, pid in winjob.tcp_listeners() if p == port}
    if owners != {identity["pid"]}:
        raise ValueError("The owned proxy port is not held by the exercise's supervisor; Codex does not start")
    for origin in plan["summary"]["app"]:
        if not answers(origin):
            raise ValueError(f"The app port {origin} no longer answers; Codex does not start")
    return identity


def run_alive(directory):
    """C2 follow-up 7: whether the `run` call recorded in `started` still runs. None when `started` holds no
    identity (it cannot be told), else True or False (PID and creation time)."""
    identity = _read(Path(directory) / "started")
    if not isinstance(identity, dict) or type(identity.get("pid")) is not int or \
            type(identity.get("created")) is not int:
        return None
    return winjob.alive(identity["pid"], identity["created"])


def end_app(directory, plan, timing=None):
    """End the app (I8): signal the supervisor, else end the job by name; confirm independently. Never raises for
    a missing piece; returns the per-item report."""
    directory = Path(directory)
    timing = {**TIMING, **(timing or (_read(directory / CONFIG) or {}).get("timing") or {})}
    patience = timing["end_patience"]
    if not (directory / CONFIG).exists():
        return {"confirmed": True, "state": "not_started", "trees": [], "proxy_released": True}
    _INTENTIONAL.set()
    identity = _read(directory / PROCESS) or {}
    current = status(directory) or {}
    how, request = "supervisor_gone", None
    if winjob.alive(identity.get("pid"), identity.get("created")):
        if current.get("state") in ("ended", "start_failed", "bound_ended"):
            how = "supervisor"
        else:
            request = secrets.token_hex(8)
            _write(directory / REQUEST, {"id": request, "action": "end"})
            deadline = time.monotonic() + timing["respond"]
            how = "no_response"
            while time.monotonic() < deadline:
                current = status(directory) or current
                if current.get("request") == request and current.get("state") in ("ended", "end_unconfirmed"):
                    how = "supervisor" if current["state"] == "ended" else "supervisor_unconfirmed"
                    break
                time.sleep(0.1)
        handle = winjob.open_verified(identity.get("pid"), identity.get("created"), winjob.SYNCHRONIZE)
        if handle:
            try:
                winjob.wait_handle(handle, 10 if how == "supervisor" else 0)
            finally:
                winjob.close_handle(handle)
    # Fallback and independent confirmation: registered repro jobs first, then the app job by name (I8).
    order = []
    repro = end_repro_jobs(directory, order, patience)
    job, job_ended = current.get("job"), True
    if isinstance(job, str) and APP_JOB.fullmatch(job):
        handle = winjob.open_job(job)
        if handle:
            try:
                if winjob.job_active(handle):
                    job_ended = winjob.terminate_job(handle, patience)
                    order.append({"job": job, "kind": "app", "at": time.time(), "ended": job_ended})
                    how = how if how == "supervisor" else "job_by_name"
            finally:
                winjob.close_handle(handle)
    members = [m for m in current.get("apps", []) + current.get("members", []) if isinstance(m, dict)]
    alive = sorted({m["pid"] for m in members if winjob.alive(m.get("pid"), m.get("created"))})
    left = wait_no_listeners(app_ports(plan["summary"]["app"]), patience) if current.get("apps") else []
    supervisor_alive = winjob.alive(identity.get("pid"), identity.get("created"))
    if supervisor_alive and repro["confirmed"] and job_ended and not alive and not left:
        # Everything it held is ended but it did not exit: end it by its verified identity to release the proxy port.
        winjob.terminate_verified(identity["pid"], identity["created"])
        supervisor_alive = winjob.alive(identity.get("pid"), identity.get("created"))
    trees = [{"kind": a.get("kind"), "index": a.get("index"), "pid": a.get("pid"),
              "ended": not winjob.alive(a.get("pid"), a.get("created"))} for a in current.get("apps", [])
             if isinstance(a, dict)]
    confirmed = repro["confirmed"] and job_ended and not alive and not left and not supervisor_alive
    return {"confirmed": confirmed, "how": how, "trees": trees, "alive": alive, "listeners": left, "repro": repro,
            "order": [*current.get("order", []), *order], "proxy_released": not supervisor_alive,
            "supervisor_state": current.get("state")}


class Watcher:
    """U10: a SYNCHRONIZE handle to the supervisor, held by `run`; its death stops the Codex tree at once."""

    def __init__(self, identity, on_death):
        self.handle = winjob.open_verified(identity.get("pid"), identity.get("created"), winjob.SYNCHRONIZE)
        if not self.handle:
            raise ValueError("The app supervisor is not running; Codex does not start")
        self.on_death, self.fired = on_death, None
        self.armed = threading.Event()
        self.armed.set()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while self.armed.is_set():
            if winjob.wait_handle(self.handle, 0.2):
                if self.armed.is_set() and not _INTENTIONAL.is_set():
                    self.fired = time.time()
                    self.on_death(self.armed)
                return

    def disarm(self):
        self.armed.clear()
        if self.thread is not threading.current_thread():
            self.thread.join(timeout=60)
        if self.handle:
            winjob.close_handle(self.handle)
            self.handle = None


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "serve":
        raise SystemExit("usage: supervisor.py serve <run directory>")
    serve(sys.argv[2])
