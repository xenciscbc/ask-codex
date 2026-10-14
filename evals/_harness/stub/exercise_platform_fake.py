"""Eval fake of the exercise platform layer (plan `.scratch/exercise-skills/plan.md` I13). Never production.

`run-evals.sh` copies this file into `<plugin root>/.eval-stub/` beside the stub `codex`; `platform_layer.py` loads
it from there only when its stub check passes (codex on PATH is `.eval-stub/codex` and reports
`codex-cli 0.0.0-stub`) and replaces exactly the names in REPLACEMENTS. Claude evals run in WSL, where the real
layer (Windows handles, Job Objects, Chrome, the browser guard) cannot run; everything else an exercise does stays
production code: request validation, the lifecycle and its state checks, the browser server definition, the MCP
guard against the stub Codex, the Codex launch, wait, stop, collect with redaction, finish's ordering.

What the fake does instead:
- target: copies the project (regular files and directories only, decided by lstat and never followed; links and
  every other entry — device node, FIFO, socket, e.g. the eval sandbox's /dev/null masks on paths such as
  `.mcp.json` — are never opened, not copied, and listed in `skipped_links`; the real copy's fixed names, secret
  patterns and the request's extra names excluded unless a named env file) into a stand-in root
  `<base>/ask-codex/eval-root.<run suffix>/<target name>`. It never writes under the requested target root and does
  not check that it exists; it refuses a root that is relative, equal to the project, inside it or containing it,
  and an unconfirmed one. The summary's `target_root` is the requested path, as the real layer reports it.
  Sibling directories go into the stand-in root; removal deletes recorded entries only, never through a link.
- guard: no browser; writes the pass record (`guard.json`) with source `ran`, or `cache` (passed 30 minutes ago),
  or fails, as `exercise_fake.guard` in the copy's `.stub/scenario.json` says (default `ran`).
- app start: runs no command; records each command as "not run" and reports the app started, or a start failure
  when `exercise_fake.app_start` is `fail`.
- processes: nothing is started, so nothing needs ending; ending reports every item confirmed ended.
- dependency report: node and Chrome are not looked up; the codex version is the stub's, compared with the tested
  version by guard.codex_notice (production).
"""
import fnmatch
import json
import os
from pathlib import Path
import random
import secrets
import shutil
import stat
import tempfile
import time

import exercise
import guard
import supervisor
import target

HERE = Path(__file__).resolve().parent
FINGERPRINT = "eval-fake-fingerprint"
NOT_RUN = "eval fake: this command was not run (the eval platform fake starts no process)\n"


def _norm(path):
    return os.path.normcase(os.path.normpath(os.path.abspath(str(path))))


def _inside(child, parent):
    child, parent = _norm(child), _norm(parent)
    return child == parent or child.startswith(parent.rstrip(os.sep) + os.sep)


def _scenario(target_path):
    try:
        data = json.loads((Path(target_path) / ".stub" / "scenario.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    fake = data.get("exercise_fake") if isinstance(data, dict) else None
    return fake if isinstance(fake, dict) else {}


def _write_record(directory, record):
    path = Path(directory) / target.RECORD
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(record), encoding="utf-8")
    temporary.replace(path)


def _plain_directory(path):
    return os.path.isdir(path) and not os.path.islink(path)


# --- target (target.create, create_sibling, remove; exercise._new_run_directory, make_evidence, verify_entries) ---

def new_run_directory(base, project):
    resolved = Path(base).resolve()
    if _inside(resolved, project):
        raise target.TargetError("The run directory must not be inside the project")
    parent = resolved / "ask-codex"
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run.", dir=parent))


def _excluded(name, relative, spec):
    folded = name.casefold()
    if folded in target.FIXED_NAMES or folded in spec["extra"]:
        return True
    if relative.casefold() in spec["named"]:
        return False
    return any(fnmatch.fnmatchcase(folded, pattern) for pattern in target.SECRET_PATTERNS)


def create(request, make_run_directory):
    project = request.get("project")
    root = request.get("target_root")
    if not isinstance(project, str) or not os.path.isabs(project) or not os.path.isdir(project):
        raise target.TargetError("The project must be an existing absolute directory")
    if not isinstance(root, dict) or root.get("confirmed_by_user") is not True or \
            not isinstance(root.get("path"), str) or not os.path.isabs(root["path"]):
        raise target.TargetError("The target root must be an absolute path confirmed by the user")
    project = os.path.realpath(project)
    if _inside(root["path"], project) or _inside(project, root["path"]):
        raise target.TargetError("The target root must be neither inside the project nor contain it")
    name = request.get("target_name") or f"ask-codex-target-{secrets.token_hex(4)}"
    if not target.TARGET_NAME.fullmatch(name):
        raise target.TargetError("Invalid target name")
    named = {}
    for item in request.get("env_files", []) or []:
        named[str(item).replace("\\", "/").casefold()] = str(item)
    spec = {"named": named, "extra": {str(n).casefold() for n in request.get("exclude_names", []) or []}}
    directory, owns = make_run_directory(project)
    directory = Path(directory).resolve()
    stand_in = directory.parent / f"eval-root.{directory.name.split('.', 1)[1]}"
    stand_in.mkdir()
    target_path = stand_in / name
    record = {"version": target.VERSION, "directory": str(directory), "owns_run_directory": owns, "project": project,
              "root": {"path": str(stand_in), "requested": root["path"]},
              "entries": [{"kind": "target", "path": str(target_path), "state": "pending"}], "copy": "pending"}
    _write_record(directory, record)
    target_path.mkdir()
    record["entries"][0]["state"] = "created"
    _write_record(directory, record)
    skipped, excluded, copied, found = [], [], {"files": 0, "directories": 0, "bytes": 0}, set()
    for current, dirs, files in os.walk(project, followlinks=False):
        relative_dir = os.path.relpath(current, project)
        for entry in sorted(dirs + files):
            source = os.path.join(current, entry)
            relative = entry if relative_dir == "." else f"{relative_dir}/{entry}".replace("\\", "/")
            if os.path.islink(source):
                skipped.append(relative)
                if entry in dirs:
                    dirs.remove(entry)
                continue
            if _excluded(entry, relative, spec):
                excluded.append(relative)
                if entry in dirs:
                    dirs.remove(entry)
                continue
            destination = target_path / relative
            mode = os.lstat(source).st_mode  # never followed; nothing but a regular file is ever opened
            if stat.S_ISDIR(mode):
                destination.mkdir()
                copied["directories"] += 1
            elif not stat.S_ISREG(mode):
                skipped.append(relative)  # device node, FIFO, socket, ...: left behind unread, like a link
                if entry in dirs:
                    dirs.remove(entry)
            else:
                shutil.copyfile(source, destination)
                copied["files"] += 1
                copied["bytes"] += os.path.getsize(source)
                found.add(relative.casefold())
    missing = [shown for folded, shown in named.items() if folded not in found]
    if missing:
        remove(directory)
        return {"state": "failed", "reason": f"Copy failed (named file not found as a regular file in the project: "
                                             f"{', '.join(missing)}); the partial target was removed",
                "target_removed": True}
    record["copy"] = "done"
    _write_record(directory, record)
    return {"state": "created", "directory": str(directory), "target": str(target_path), "root": root["path"],
            "skipped_links": skipped, "excluded": excluded, "git_layouts_excluded": [], "streams_not_copied": [],
            "env_files": sorted(named.values()), "copied": copied}


def create_sibling(run_directory, purpose):
    if not isinstance(purpose, str) or not target.PURPOSE.fullmatch(purpose):
        raise target.TargetError("Invalid sibling purpose")
    directory, record = target.record_at(run_directory)
    [made] = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
    path = Path(record["root"]["path"]) / f"{Path(made['path']).name}.{purpose}-{secrets.token_hex(4)}"
    entry = {"kind": "temp", "purpose": purpose, "path": str(path), "state": "pending"}
    record["entries"].append(entry)
    _write_record(directory, record)
    path.mkdir()
    entry["state"] = "created"
    _write_record(directory, record)
    return str(path)


def remove(run_directory):
    directory, record = target.record_at(run_directory)
    removed, absent, failures = [], [], []
    for entry in reversed(list(record.get("entries", []))):
        path = entry.get("path")
        if not isinstance(path, str) or not _inside(path, record["root"]["path"]):
            failures.append({"path": path, "reason": "not inside the stand-in root"})
            continue
        if os.path.islink(path):
            failures.append({"path": path, "reason": "the entry is a link; it is never followed"})
            continue
        if os.path.lexists(path):
            shutil.rmtree(path)  # links inside are unlinked, never followed
            removed.append(path)
        else:
            absent.append(path)
        record["entries"].remove(entry)
        _write_record(directory, record)
    if failures:
        return {"state": "failed", "reason": "; ".join(f"{f['path']}: {f['reason']}" for f in failures),
                "retained_location": str(directory), "kept": failures}
    try:
        os.rmdir(record["root"]["path"])
    except OSError:
        pass
    if record.get("owns_run_directory"):
        (directory / target.RECORD).unlink()
        try:
            directory.rmdir()
        except OSError:
            pass
    return {"state": "removed", "removed": removed, "absent": absent}


def make_evidence(directory):
    _, record = target.record_at(directory)
    [made] = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
    evidence = Path(made["path"]) / exercise.EVIDENCE
    replaced = os.path.lexists(evidence)
    if replaced:
        if os.path.islink(evidence) or not os.path.isdir(evidence):
            os.unlink(evidence)
        else:
            shutil.rmtree(evidence)
    evidence.mkdir()
    return evidence, replaced


def verify_entries(directory, plan):
    _, record = target.record_at(directory)
    paths = {e.get("path"): e for e in record.get("entries", [])}
    b = plan["browser"]
    for path in (plan["summary"]["target"], b["temp"], b["cwd"], b["profile"]):
        entry = paths.get(path)
        if not entry or entry.get("state") != "created":
            raise ValueError(f"{path} is not a created entry of the target record; exercise not started")
        if not _plain_directory(path):
            raise ValueError(f"{path} no longer matches the target record; exercise not started")
    if not _plain_directory(b["evidence"]):
        raise ValueError("The evidence directory is not a plain directory; exercise not started")


def claim_run(cli, directory):
    """Never replay an execution attempt (exclusive create; a POSIX rename would replace an existing file)."""
    try:
        with open(Path(directory) / "started", "x", encoding="utf-8") as started:
            started.write(json.dumps({"pid": os.getpid(), "created": 0}))
    except FileExistsError:
        raise cli.AlreadyAttempted() from None


# --- browser ---

def node_executable(which):
    return HERE / "eval-fake-node"


def entry_script():
    return HERE / "eval-fake-chrome-devtools-mcp.js"


def local_app_data():
    return HERE / "eval-fake-state"  # never created: only compared by the placement checks


def free_loopback_port():
    return random.randint(20000, 60999)


# --- guard ---

def _guard_record(directory):
    try:
        return json.loads((Path(directory) / "guard.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def guard_exercise(cli, directory, state_dir=None):
    directory, plan = cli.plan_at(directory)
    if not exercise.is_plan(plan):
        raise ValueError("guard applies to exercises only")
    exercise.require_platform()
    if (directory / "started").exists():
        raise ValueError("The exercise run has started; the guard runs before it")
    if (directory / supervisor.CONFIG).exists():
        raise ValueError("The app start was attempted for this exercise; the guard runs before any app process")
    mode = _scenario(plan["summary"]["target"]).get("guard", "ran")
    if mode == "fail":
        items = [{"item": "eval fake", "ok": False, "detail": "the guard failed (eval scenario)"}]
        result = exercise.fail_at_once(cli, directory, plan, "Browser guard failed: eval fake (scenario)")
        return {**result, "guard": {"source": "ran", "passed": False, "failing": items, "items": len(items)}}
    now = time.time()
    passed = now - 1800 if mode == "cache" else now
    source = "cache" if mode == "cache" else "ran"
    cli.write_json(directory / "guard.json", {"fingerprint": FINGERPRINT, "source": source, "passed_at": passed,
                                              "checked_at": now, "facts": {"eval_fake": True}})
    return {"state": "guard_passed", "directory": str(directory),
            "guard": {"source": source, "passed_at": passed, "fingerprint": FINGERPRINT}}


def require_current_pass(cli, directory, plan, state_dir=None):
    record = _guard_record(directory)
    if not record:
        raise ValueError("No browser guard pass for this exercise; run the guard before the app starts")
    if record.get("fingerprint") != FINGERPRINT:
        raise ValueError("The browser guard passed for another configuration; prepare a new exercise")
    passed = record.get("passed_at")
    if type(passed) not in (int, float) or not 0 <= time.time() - passed <= guard.CACHE_SECONDS:
        raise ValueError("The browser guard pass is older than 12 hours; prepare a new exercise")
    return record


def dependency_report(cli, state_dir=None):
    version = guard.codex_version(cli, str(HERE))
    return {"state": "ready", "node": "eval fake (not looked up)", "node_version": "eval-fake",
            "manifest_sha256": "eval-fake", "chrome": "eval fake (not looked up)", "chrome_version": "eval-fake",
            "codex_version": version, "chrome_policy_sha256": "eval-fake", **guard.codex_notice(version)}


# --- supervisor ---

def launch(directory):
    identity = {"pid": os.getpid(), "created": 0, "breakaway": False}
    supervisor._write(Path(directory) / supervisor.PROCESS, identity)
    return identity, None


def wait_started(directory, identity, process, timing, installs):
    directory = Path(directory)
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    commands = plan["request"].get("commands") or {}
    apps = []
    for kind in ("install", "start"):
        for index, command in enumerate(commands.get(kind, []) or []):
            log = f"app-{kind}-{index}.log"
            (directory / log).write_text(NOT_RUN, encoding="utf-8")
            apps.append({"kind": kind, "index": index, "pid": 0, "created": 0, "command": supervisor.shown(command),
                         "exit_code": 0 if kind == "install" else None, "log": log})
    status = {"pid": identity["pid"], "job": "eval-fake-job", "apps": apps, "members": []}
    if _scenario(plan["summary"]["target"]).get("app_start") == "fail":
        status.update(state="start_failed", failure={"reason": "The app did not start (eval scenario)",
                                                     "output": supervisor.output(directory, {"apps": apps})})
    else:
        status["state"] = "app_started"
    supervisor._write(directory / supervisor.STATUS, status)
    return status


def require_started(directory, plan):
    directory = Path(directory)
    current, identity = supervisor.status(directory), supervisor._read(directory / supervisor.PROCESS)
    if not (directory / supervisor.CONFIG).exists() or not isinstance(current, dict) or not isinstance(identity, dict):
        raise ValueError("The app has not been started for this exercise (app-start); Codex does not start")
    if current.get("state") != "app_started":
        raise ValueError(f"The app is not running (supervisor state {current.get('state')}); Codex does not start")
    return identity


class Watcher:
    def __init__(self, identity, on_death):
        self.fired = None

    def disarm(self):
        pass


def own_processes(directory):
    return set()


def codex_processes_ended(directory, plan, exclude, patience=None):
    return {"confirmed": True, "recorded": 0, "terminated": [], "alive": []}


def end_app(directory, plan, timing=None):
    directory = Path(directory)
    if not (directory / supervisor.CONFIG).exists():
        return {"confirmed": True, "state": "not_started", "trees": [], "proxy_released": True}
    current = supervisor.status(directory) or {}
    if current:
        supervisor._write(directory / supervisor.STATUS, {**current, "state": "ended", "ended_at": time.time()})
    trees = [{"kind": a.get("kind"), "index": a.get("index"), "pid": a.get("pid"), "ended": True}
             for a in current.get("apps", []) if isinstance(a, dict)]
    return {"confirmed": True, "how": "eval-fake", "trees": trees, "alive": [], "listeners": [],
            "repro": {"confirmed": True, "jobs": []}, "order": [], "proxy_released": True,
            "supervisor_state": current.get("state")}


def run_alive(directory):
    return None  # process identities mean nothing across eval sandbox calls


REPLACEMENTS = {
    "target": {"create": create, "create_sibling": create_sibling, "remove": remove},
    "exercise": {"_new_run_directory": new_run_directory, "make_evidence": make_evidence,
                 "verify_entries": verify_entries, "claim_run": claim_run},
    "browser": {"node_executable": node_executable, "entry_script": entry_script, "local_app_data": local_app_data,
                "free_loopback_port": free_loopback_port},
    "guard": {"guard_exercise": guard_exercise, "require_current_pass": require_current_pass,
              "dependency_report": dependency_report},
    "supervisor": {"launch": launch, "wait_started": wait_started, "require_started": require_started,
                   "Watcher": Watcher, "own_processes": own_processes, "codex_processes_ended": codex_processes_ended,
                   "end_app": end_app, "run_alive": run_alive},
}
