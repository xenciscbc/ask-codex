"""UI exercise on a disposable target (plan `.scratch/exercise-skills/plan.md` claim C2; I4, I5, I6, I11, I12, I13).

An exercise request (interaction `exercise`, kind `ui`) goes through the same CLI as a consultation:

    consult.py prepare <request.json> [--base <scratch base>]   validate, create run directory + target + sibling
                                                               directories, MCP guard (I6), write plan.json
    consult.py guard <run directory>                           dependency check and browser guard, or a cached
                                                               pass (guard.py, C3); before any app process
    consult.py run <run directory>                             re-check, require a current guard pass for the
                                                               exact fingerprint, hold the owned proxy port,
                                                               start Codex
    consult.py wait|continue <run directory>                   as for a consultation
    consult.py collect <run directory>                         reply (UI schema, redacted); keeps run directory
                                                               and target for reproduction and evidence
    consult.py finish <run directory>                          remove the target (C1), then the run directory
    consult.py stop|cleanup <run directory>                    ADR 0004 stop path, then the target (C1)

Request (unknown keys are refused):

    {"interaction": "exercise", "kind": "ui", "project": "<absolute project directory>", "prompt": "<framing>",
     "models": [<exactly one model choice, as for a consultation>],
     "target_root": {"path": "<absolute directory>", "confirmed_by_user": true},
     "app": ["127.0.0.1:5173", "localhost:8000", "[::1]:3000"], "headed": false, "scope": "<text, may be empty>",
     optional target fields: "target_name", "env_files", "exclude_names", "limits" (target.py)}

Lifecycle (I12, the part that exists without the supervisor of C4): prepare creates the run directory through
C1's handle-based path (never through a link, never inside the project), the target, two recorded sibling
directories under the confirmed root (`mcp-temp` for the MCP's TEMP/TMP, `mcp-cwd` for its working directory,
`mcp-profile` for Chrome's profile, seeded with the preferences that block downloads, U16) and `<target>/evidence` (a top-level `evidence` entry copied from the project is replaced by it; deeper entries of
that name stay). Any failure after the target
exists removes it at once (target.remove: record, identity, no link followed), then the run directory. `run`
re-verifies the plan, the target's identity and the guard, holds the owned proxy port while Codex runs, and
removes the target at once when Codex fails by itself. `collect` returns the reply and keeps everything after a
completed run; after a failed or stopped run it removes the target before answering and the run directory after
delivery. `finish` requires the Codex tree finished or its stop confirmed (`stop_unconfirmed` keeps everything).

Every exercise operation refuses on non-Windows hosts (target.require_windows). Nothing here reads an
environment variable (I13).
"""
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import time

import browser
from policy import PLACEHOLDERS, definition_files
from redact import redact_value
from replies import classify
import target as disposable_target

INTERACTION, KIND, REPLY_SCHEMA = "exercise", "ui", "ui-exercise"
EVIDENCE = "evidence"
TARGET_FIELDS = ("project", "target_root", "target_name", "env_files", "exclude_names", "limits")
REQUEST_FIELDS = frozenset({"interaction", "kind", "prompt", "models", "app", "headed", "scope", *TARGET_FIELDS})
HOSTS = ("127.0.0.1", "localhost", "[::1]")
ORIGIN = re.compile(r"^(?P<host>\[[^\]]*\]|[^:\[\]]*):(?P<port>[^:]*)$")
MAX_APP_PORTS = 8
MAX_SCOPE = 4000
SLUG = re.compile(r"^[A-Za-z0-9_.-]+$")


def is_request(request):
    return isinstance(request, dict) and "interaction" in request


def is_plan(plan):
    return plan.get("interaction") == INTERACTION


def require_platform():
    disposable_target.require_windows()


# --- request validation (before anything is written or any Codex command runs) ---

def validate(request):
    if request.get("interaction") != INTERACTION or request.get("kind") != KIND:
        raise ValueError("An exercise request needs interaction \"exercise\" and kind \"ui\"")
    unknown = set(request) - REQUEST_FIELDS
    if unknown:
        raise ValueError(f"Unknown exercise request fields: {', '.join(sorted(unknown))}")
    if not isinstance(request.get("prompt"), str) or not request["prompt"].strip():
        raise ValueError("A prepared exercise prompt is required")
    models = request.get("models")
    if not isinstance(models, list) or len(models) != 1:
        raise ValueError("An exercise takes exactly one model")
    model = models[0]
    if not isinstance(model, dict):
        raise ValueError("Each model choice must be an object")
    name = model.get("model")
    if name is not None and (not isinstance(name, str) or not SLUG.fullmatch(name)):
        raise ValueError("Invalid model slug")
    if model.get("effort") not in ("medium", "high", "xhigh", "max", "ultra"):
        raise ValueError("Invalid consultation effort")
    if model["effort"] == "ultra" and not model.get("explicit_ultra"):
        raise ValueError("ultra requires an explicit user choice")
    root = request.get("target_root")
    if not isinstance(root, dict) or root.get("confirmed_by_user") is not True:
        raise ValueError("The target root must be confirmed by the user (target_root.confirmed_by_user = true)")
    app = request.get("app")
    if not isinstance(app, list) or not app:
        raise ValueError("An exercise needs at least one app host:port")
    if len(app) > MAX_APP_PORTS:
        raise ValueError(f"An exercise takes at most {MAX_APP_PORTS} app host:ports")
    origins = []
    for item in app:
        match = ORIGIN.fullmatch(item) if isinstance(item, str) else None
        if not match:
            raise ValueError(f"Invalid app host:port {item!r}")
        host, port = match.group("host"), match.group("port")
        if host not in HOSTS:
            raise ValueError(f"The app host {host!r} is not loopback (allowed: {', '.join(HOSTS)})")
        if not re.fullmatch(r"[1-9][0-9]{0,4}", port) or int(port) > 65535:
            raise ValueError(f"Invalid app port {port!r}")
        origin = f"{host}:{int(port)}"
        if origin in origins:
            raise ValueError(f"The app host:port {origin} is listed twice")
        origins.append(origin)
    if not isinstance(request.get("headed"), bool):
        raise ValueError("The headed flag must be true or false")
    scope = request.get("scope")
    if not isinstance(scope, str) or len(scope) > MAX_SCOPE or "\0" in scope:
        raise ValueError(f"The scope must be text of at most {MAX_SCOPE} characters")
    # <target>\evidence is the exercise's own directory: a top-level `evidence` entry the copy brings is replaced
    # (make_evidence), so a named env file under it would be lost; entries of that name at any depth below stay.
    for item in request.get("env_files", []) if isinstance(request.get("env_files"), list) else []:
        if isinstance(item, str) and re.split(r"[\\/]", item)[0].casefold() == EVIDENCE:
            raise ValueError(f"Env file {item!r} lies under the project's top-level {EVIDENCE} directory, which the "
                             "exercise replaces with its own evidence directory")
    target_request = {key: request[key] for key in TARGET_FIELDS if key in request}
    return {"app": origins, "headed": request["headed"], "scope": scope, "target_request": target_request}


# --- MCP: every other server disabled, the browser server alone (I4, I6) ---

def disable_overrides(servers, name):
    """Root-table disable entries for every enabled server, whatever the user's policy or allowlist."""
    if any(s["name"] == name for s in servers):
        raise ValueError("A configured MCP server already has the browser server's name; exercise not started")
    entries = []
    for server in sorted((s for s in servers if s["enabled"]), key=lambda s: s["name"]):
        transport = server.get("transport")
        kind = transport.get("type") if isinstance(transport, dict) else None
        if kind not in PLACEHOLDERS:
            raise ValueError(f"Cannot disable MCP server {server['name']} with transport {kind}; exercise not started")
        entries.append(f'{json.dumps(server["name"])}={{{PLACEHOLDERS[kind]},enabled=false}}')
    return (["-c", "mcp_servers={" + ",".join(entries) + "}"] if entries else []), [
        s["name"] for s in sorted(servers, key=lambda s: s["name"]) if s["enabled"]]


def guard_overrides(overrides, definition):
    return [*overrides, *browser.config_overrides(definition), *browser.approval_constants(definition["name"])]


def check_guard(definition, listed, got):
    """I6: exactly one enabled server, the browser server, with every field equal to the definition."""
    enabled = sorted(s["name"] for s in listed if s["enabled"])
    if enabled != [definition["name"]]:
        raise ValueError("MCP guard: the browser server must be the only enabled MCP server (enabled: "
                         f"{', '.join(enabled) or 'none'}); exercise not started")
    transport = got.get("transport") if isinstance(got.get("transport"), dict) else {}

    def number(value, expected):
        return type(value) in (int, float) and value == expected

    checks = {
        "name": got.get("name") == definition["name"],
        "enabled": got.get("enabled") is True,
        "transport.type": transport.get("type") == "stdio",
        "transport.command": transport.get("command") == definition["command"],
        "transport.args": transport.get("args") == definition["args"],
        "transport.env": transport.get("env") == definition["env"],
        "transport.env_vars": transport.get("env_vars") in ([], None),
        "transport.cwd": transport.get("cwd") == definition["cwd"],
        "enabled_tools": got.get("enabled_tools") == definition["enabled_tools"],
        "disabled_tools": got.get("disabled_tools") in ([], None),
        "startup_timeout_sec": number(got.get("startup_timeout_sec"), definition["startup_timeout_sec"]),
    }
    # codex-cli 0.159.3 does not print the server's default tool approval mode; where a version does, it is prompt.
    for holder, label in ((got, "default_tools_approval_mode"), (transport, "transport.default_tools_approval_mode")):
        if "default_tools_approval_mode" in holder:
            checks[label] = holder["default_tools_approval_mode"] == "prompt"
    failed = sorted(key for key, ok in checks.items() if not ok)
    if failed:
        raise ValueError(f"MCP guard definition mismatch ({', '.join(failed)}); exercise not started")


def guard(cli, target, overrides, definition):
    full = guard_overrides(overrides, definition)
    check_guard(definition, cli.listing(target, full), cli.mcp_get(target, definition["name"], full))


def preflight(cli, target, definition):
    """Definition-file scan, listing and guard, all with the target as project and working directory."""
    if definition_files(Path(target)):
        raise ValueError("The target holds a project Codex configuration; exercise not started")
    overrides, disabled = disable_overrides(cli.listing(Path(target)), definition["name"])
    guard(cli, Path(target), overrides, definition)
    return overrides, disabled


# --- run directory, target and run-owned directories ---

def _new_run_directory(base, project):
    # C1's CLI path: the base counts where it resolves; <base>\ask-codex and run.* are opened or created through
    # handles and never followed (target._new_run_directory). The exercise owns its run directory itself
    # (owns_run_directory false), so C1's removal leaves it for this lifecycle to remove after the target.
    resolved = Path(base).resolve()
    if not re.fullmatch(r"[A-Za-z]:\\.*", str(resolved), re.S):
        raise disposable_target.TargetError("The base must be on a local drive (not UNC, a volume or a device path)")
    if disposable_target._inside(str(resolved), project):
        raise disposable_target.TargetError("The run directory must not be inside the project")
    resolved.mkdir(parents=True, exist_ok=True)
    return disposable_target._new_run_directory(resolved, project)[0]


def _discard_unplanned(directory):
    """A run directory that never got its plan: only the target record (and its temporary) may be inside.
    Callers make sure the record holds no entry first (_abandon)."""
    for name in (disposable_target.RECORD, disposable_target.RECORD + ".tmp"):
        (directory / name).unlink(missing_ok=True)
    directory.rmdir()


def _abandon(directory):
    """`create` was interrupted: remove what its record holds (C1 removal), then the run directory. Returns None
    when everything is gone, else the location that is kept (the record is never deleted while it holds an entry)."""
    entries = []
    if os.path.lexists(Path(directory) / disposable_target.RECORD):
        try:
            record = disposable_target.record_at(directory)[1]
            entries = record.get("entries") if isinstance(record.get("entries"), list) else [None]
        except (ValueError, OSError):
            return str(directory)  # an unreadable record is kept for inspection
    if entries:
        removal = remove_target(directory)
        if removal["state"] != "removed":
            return removal.get("retained_location", str(directory))
    try:
        _discard_unplanned(directory)
    except OSError:
        return str(directory)
    return None


def remove_target(directory):
    """C1 removal of every recorded entry; never raises (failures are reported)."""
    try:
        return disposable_target.remove(directory)
    except Exception as error:  # the record stays; report where
        return {"state": "failed", "reason": f"{error}" if isinstance(error, ValueError) else
                f"{type(error).__name__}: target removal failed", "retained_location": str(directory)}


def target_kept(directory):
    try:
        _, record = disposable_target.record_at(directory)
    except ValueError:
        return False
    return bool(record.get("entries"))


def _identity_matches(handle, entry):
    attributes, _ = disposable_target._attribute_tag(handle)
    return not attributes & disposable_target.ATTR_REPARSE and attributes & disposable_target.ATTR_DIRECTORY and \
        disposable_target._identity(handle) == {"volume_serial": entry.get("volume_serial"), "file_id": entry.get("file_id")}


def verify_entries(directory, plan):
    """Before Codex starts: the root, the target and each sibling still match the record; evidence is a plain
    directory in the target. Opened without following a final link (target.py's primitives)."""
    with disposable_target._placeholders_exposed():
        _, record = disposable_target.record_at(directory)
        root = disposable_target._verified_root(record)
        disposable_target._close(root)
        paths = {e.get("path"): e for e in record.get("entries", [])}
        b = plan["browser"]
        for path in (plan["summary"]["target"], b["temp"], b["cwd"], b["profile"]):
            entry = paths.get(path)
            if not entry or entry.get("state") != "created":
                raise ValueError(f"{path} is not a created entry of the target record; exercise not started")
            handle = disposable_target._win_open(path, disposable_target.READ_ATTRIBUTES,
                                                 disposable_target.FLAG_BACKUP_SEMANTICS |
                                                 disposable_target.FLAG_OPEN_REPARSE_POINT)
            try:
                if not _identity_matches(handle, entry):
                    raise ValueError(f"{path} no longer matches the target record; exercise not started")
            finally:
                disposable_target._close(handle)
        status = os.lstat(b["evidence"])
        if status.st_file_attributes & disposable_target.ATTR_REPARSE or not status.st_file_attributes & 0x10:
            raise ValueError("The evidence directory is not a plain directory; exercise not started")


def make_evidence(directory):
    """Create <target>\\evidence relative to the target's handle, after checking the target against the record.
    A top-level `evidence` entry the copy brought from the project is removed first, handle-relative and without
    following any link (C1's removal routine); entries of that name deeper in the copy are kept. Returns the
    evidence path and whether a copied entry was replaced."""
    t = disposable_target
    replaced = False
    with t._placeholders_exposed():
        _, record = t.record_at(directory)
        [entry] = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
        root = t._verified_root(record)
        try:
            handle = t._nt_open(root, ntpath.basename(entry["path"]),
                                t.LIST_DIRECTORY | t.ADD_SUBDIRECTORY | t.TRAVERSE | t.READ_ATTRIBUTES,
                                t.DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
            try:
                if not _identity_matches(handle, entry):
                    raise ValueError("The target no longer matches the record; exercise not started")
                try:
                    copied = t._nt_open(handle, EVIDENCE, t.DELETE | t.READ_ATTRIBUTES, t.OPEN_REPARSE_POINT)
                except t.NtError as error:
                    if error.status not in (t.STATUS_NAME_NOT_FOUND, t.STATUS_PATH_NOT_FOUND):
                        raise
                    copied = None
                if copied is not None:
                    try:
                        t._remove_open(copied, time.monotonic() + t.REMOVAL_PATIENCE_S)
                    finally:
                        t._close(copied)
                    replaced = True
                t._close(t._create_directory(handle, EVIDENCE))  # exclusive create
            finally:
                t._close(handle)
        finally:
            t._close(root)
    return Path(entry["path"]) / EVIDENCE, replaced


def placement_problems(directory, target, evidence, temp, cwd, profile):
    """R4-1 / I5 / U16: TEMP, cwd and the browser profile are neither equal to, inside nor an ancestor of any path
    the script reads or Codex writes, nor of the target and evidence, nor of each other; TEMP and cwd are empty (the
    profile holds only its seed, checked by browser.profile_problems)."""
    protected = {"run directory": directory, "target record": directory / disposable_target.RECORD,
                 "plan": directory / "plan.json", "stop request": directory / "0" / "stop-request",
                 "stop status": directory / "0" / "stop-status.json", "reply": directory / "0" / "last-message.json",
                 "events": directory / "0" / "events.jsonl", "guard cache": browser.guard_cache_directory(),
                 "package install": browser.install_directory(), "evidence": evidence, "target": target}
    problems = []
    for owned, path in (("MCP TEMP", temp), ("MCP cwd", cwd), ("browser profile", profile)):
        if owned != "browser profile" and os.listdir(path):
            problems.append(f"{owned} is not empty")
        for label, other in protected.items():
            if browser.related(path, other):
                problems.append(f"{owned} overlaps the {label}")
    for (a, x), (b, y) in ((("MCP cwd", cwd), ("MCP TEMP", temp)), (("browser profile", profile), ("MCP TEMP", temp)),
                           (("browser profile", profile), ("MCP cwd", cwd))):
        if browser.related(x, y):
            problems.append(f"{a} overlaps {b}")
    return problems


def _template(spec_or_request, node, entry):
    return browser.template(spec_or_request["app"], spec_or_request["headed"], node, entry)


def prepare(cli, request, base):
    require_platform()
    spec = validate(request)
    node, entry = browser.node_executable(cli.which), browser.entry_script()
    template = _template(spec, node, entry)
    if browser.never_listed(template):
        raise ValueError("The browser server definition carries a forbidden argument")
    made = []

    def make_run_directory(project):
        made.append(_new_run_directory(base, project))
        return made[-1], False

    try:
        created = disposable_target.create(spec["target_request"], make_run_directory)
    except BaseException as error:
        # Interrupted (an exception or e.g. KeyboardInterrupt) possibly after the target was created: remove it
        # through its record; the record is deleted only once it holds no entry.
        kept = _abandon(made[-1]) if made else None
        if kept is not None and isinstance(error, Exception):
            reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: target creation failed"
            raise ValueError(f"{reason}; what was created could not be removed; retained: {kept}") from None
        raise
    if created["state"] != "created":
        if made and created.get("target_removed"):
            try:
                _discard_unplanned(made[-1])
            except OSError:
                created["retained_location"] = str(made[-1])
        return {**created, "state": "failed"}
    directory = Path(created["directory"])
    try:
        temp = disposable_target.create_sibling(directory, "mcp-temp")
        cwd = disposable_target.create_sibling(directory, "mcp-cwd")
        profile = disposable_target.create_sibling(directory, "mcp-profile")
        evidence, replaced = make_evidence(directory)
        port = browser.free_loopback_port()
        nonce = browser.NAME_PREFIX + secrets.token_hex(8)
        definition = browser.instantiate(template, nonce, created["target"], cwd, temp, port, profile)
        if browser.never_listed(definition, profile):
            raise ValueError("The browser server definition carries a forbidden argument")
        problems = placement_problems(directory, Path(created["target"]), evidence, temp, cwd, profile)
        if problems:
            raise ValueError("Run-owned directory placement refused: " + "; ".join(problems))
        browser.seed_profile(profile)  # U16: downloads blocked before any launch
        overrides, disabled = preflight(cli, created["target"], definition)
        _, record = disposable_target.record_at(directory)
        summary = {"interaction": INTERACTION, "kind": KIND, "project": record["project"],
                   "target_root": created["root"], "target": created["target"], "app": spec["app"],
                   "browser": "headed" if spec["headed"] else "headless", "scope": spec["scope"],
                   "models": request["models"], "reply_schema": REPLY_SCHEMA, "allowed_servers": [],
                   "browser_server": nonce, "disabled_servers": disabled}
        copy = {key: created[key] for key in ("skipped_links", "excluded", "git_layouts_excluded",
                                              "streams_not_copied", "env_files", "copied")}
        copy["top_level_evidence_replaced"] = replaced
        cli.write_json(directory / "plan.json", {
            "version": 1, "interaction": INTERACTION, "request": request, "summary": summary, "timer": cli.timer(),
            "overrides": overrides, "directory": str(directory), "copy": copy,
            "browser": {"definition": definition, "proxy_port": port, "temp": temp, "cwd": cwd, "profile": profile,
                        "evidence": str(evidence), "node": str(node), "entry": str(entry)}})
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: exercise preparation failed"
        return fail_at_once(cli, directory, None, reason)
    return {"state": "prepared", "directory": str(directory), "summary": summary, "copy": copy}


def fail_at_once(cli, directory, plan, reason):
    """A failure before Codex: remove the target now, then the run directory; report what is kept."""
    removal = remove_target(directory)
    result = {"state": "failed", "reason": reason, "target_removed": removal["state"] == "removed"}
    if removal["state"] != "removed":
        return {**result, "retained_location": removal.get("retained_location", str(directory)), "removal": removal,
                "record": str(directory)}
    try:
        if plan is None and not (directory / "plan.json").exists():
            _discard_unplanned(directory)
        else:
            cli.remove_run(directory, plan or cli.read_json(directory / "plan.json"))
    except OSError:
        result["retained_location"] = str(directory)
    return result


# --- run ---

def before_launch(cli, directory, plan):
    """Every check again, then the owned proxy port; any failure removes the target at once (raised as ValueError)."""
    try:
        b, request = plan["browser"], plan["request"]
        node, entry = browser.node_executable(cli.which), browser.entry_script()
        rebuilt = browser.instantiate(_template({"app": plan["summary"]["app"], "headed": request["headed"]}, node, entry),
                                      plan["summary"]["browser_server"], plan["summary"]["target"], b["cwd"], b["temp"],
                                      b["proxy_port"], b["profile"])
        if rebuilt != b["definition"] or browser.never_listed(rebuilt, b["profile"]):
            raise ValueError("Effective browser server definition changed; prepare and review a new exercise")
        verify_entries(directory, plan)
        problems = placement_problems(directory, Path(plan["summary"]["target"]), Path(b["evidence"]),
                                      b["temp"], b["cwd"], b["profile"]) + browser.profile_problems(b["profile"])
        if problems:
            raise ValueError("Run-owned directory placement refused: " + "; ".join(problems))
        overrides, _ = preflight(cli, plan["summary"]["target"], b["definition"])
        if overrides != plan["overrides"]:
            raise ValueError("Effective configuration changed; prepare and review a new exercise")
        # I7: a current browser guard pass (at most 12 h old) for this exercise's exact fingerprint, recomputed now.
        import guard
        guard.require_current_pass(cli, directory, plan)
        return browser.ProxyHolder(b["proxy_port"])
    except Exception as error:
        reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: exercise launch check failed"
        removal = remove_target(directory)
        if removal["state"] != "removed":
            reason += f"; the target could not be removed ({removal.get('reason')}); retained: " \
                      f"{removal.get('retained_location', directory)}"
        else:
            reason += "; the target was removed"
        raise ValueError(reason) from None


def codex_argv(plan, model, child, constants, schema):
    definition = plan["browser"]["definition"]
    args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
            "-C", Path(plan["summary"]["target"]).as_posix()]
    if model.get("model"):
        args += ["-m", model["model"]]
    return [*args, "-c", f'model_reasoning_effort="{model["effort"]}"', *plan["overrides"], *constants,
            *browser.config_overrides(definition), *browser.approval_constants(definition["name"]),
            "--output-schema", Path(schema).as_posix(), "-o", (child / "last-message.json").as_posix(), "-"]


def after_run(cli, directory):
    """Codex failed by itself (no stop involved): the target goes at once. A stop removes it in `stop`."""
    child = directory / "0"
    result, stopped = cli.result_for(child), cli.stop_status(child)
    if result is not None and stopped is None and result.get("exit_code") != 0:
        return remove_target(directory)
    return None


# --- collect, finish ---

def collect(cli, directory, plan, after_delivery):
    require_platform()
    if (directory / "execution-error.json").exists() and not (directory / "clock.json").exists():
        output = {**cli.read_json(directory / "execution-error.json"), "directory": str(directory)}
        return _settle(cli, directory, plan, output, after_delivery)
    model, child = plan["request"]["models"][0], directory / "0"
    stopped = cli.stop_status(child)
    if stopped is not None:
        run = {"model": model.get("model"), "effort": model["effort"],
               "state": "stopped" if stopped["confirmed"] else "stop_unconfirmed", "stop": stopped}
    else:
        result = cli.result_for(child)
        if result is None:
            return {"state": "running", "directory": str(directory)}
        code = result["exit_code"]
        run = {"model": model.get("model"), "effort": model["effort"], "state": "failed", "exit_code": code}
        reply = child / "last-message.json"
        if code == 0 and reply.exists() and reply.stat().st_size:
            try:
                text = reply.read_text(encoding="utf-8")
                if text.strip():
                    classified = classify(text, REPLY_SCHEMA)
                    # I11: token-like strings are redacted before Claude sees the reply.
                    run.update(state="completed", reply={**classified, "content": redact_value(classified["content"])})
            except UnicodeError:
                pass
        if run["state"] == "failed":
            run["reason"] = "Codex execution failed" if code else "Codex returned no usable reply"
            errors = (child / "stderr.log").read_text(encoding="utf-8", errors="replace") \
                if (child / "stderr.log").exists() else ""
            if any(token in errors.lower() for token in ("not logged in", "unauthorized", "codex login")):
                run["reason"] = "Codex is not logged in; run ! codex login, then request a new exercise"
        if result.get("reason"):
            run["reason"] = result["reason"]
    output = {"state": "collected", "directory": str(directory), "summary": plan["summary"], "timer": plan["timer"],
              "runs": [run], "checks": cli.read_json(directory / "clock.json").get("checks", [])
              if (directory / "clock.json").exists() else []}
    if (directory / "launch-error.json").exists():
        output["launch_error"] = cli.read_json(directory / "launch-error.json")
    if (directory / "guard.json").exists():
        # Report data: whether the browser guard ran for this exercise or was reused from cache, and when it passed.
        guarded = cli.read_json(directory / "guard.json")
        output["guard"] = {"source": guarded.get("source"), "passed_at": guarded.get("passed_at")}
    if run["state"] == "stop_unconfirmed":
        (directory / "retained").touch()
        return {**output, "retained_location": str(directory), "target_kept": target_kept(directory)}
    if run["state"] == "stopped" and cli.result_for(child) is None:
        return {**output, "state": "settling", "retained_location": str(directory)}
    if run["state"] == "completed":
        # I12: the run directory and the target stay for reproduction and evidence handling until `finish`.
        (directory / "collected").touch()
        return {**output, "target": plan["summary"]["target"], "evidence": plan["browser"]["evidence"],
                "target_kept": target_kept(directory), "next": "finish"}
    return _settle(cli, directory, plan, output, after_delivery)


def _settle(cli, directory, plan, output, after_delivery):
    """Failed or stopped: the target is removed before answering, the run directory after delivery."""
    removal = remove_target(directory)
    if removal["state"] != "removed":
        return {**output, "target_removed": False, "retained_location": removal.get("retained_location", str(directory)),
                "removal": removal}
    after_delivery.append(lambda: cli.remove_run(directory, plan))
    return {**output, "target_removed": True}


def refuse_while_launching(directory):
    """`run` has started its checks (`started`) but has neither started Codex (`clock.json`) nor failed
    (`execution-error.json`): it may be about to launch Codex on the target, so nothing is removed now."""
    if (directory / "started").exists() and not (directory / "clock.json").exists() and \
            not (directory / "execution-error.json").exists():
        raise ValueError("The exercise run is starting (its launch checks have begun and Codex has not started yet); "
                         "nothing is removed. Wait for `run` to return, then collect or finish")


def finish(cli, directory):
    directory, plan = cli.plan_at(directory)
    if not is_plan(plan):
        raise ValueError("finish applies to exercises only; use cleanup for a consultation")
    require_platform()
    refuse_while_launching(directory)
    child = directory / "0"
    if (directory / "clock.json").exists():
        stopped = cli.stop_status(child)
        if stopped is not None and not stopped.get("confirmed"):
            return {"state": "stop_unconfirmed", "directory": str(directory), "retained_location": str(directory),
                    "target_kept": target_kept(directory),
                    "reason": "The Codex process-tree stop is unconfirmed; nothing is removed"}
        if cli.result_for(child) is None:
            raise ValueError("Codex is still running; stop the exercise first")
    removal = remove_target(directory)
    if removal["state"] != "removed":
        return {"state": "failed", "directory": str(directory), "reason": removal.get("reason"),
                "retained_location": removal.get("retained_location", str(directory)), "removal": removal}
    cli.remove_run(directory, plan)
    return {"state": "finished", "target_removed": True, "removed": removal.get("removed", [])}
