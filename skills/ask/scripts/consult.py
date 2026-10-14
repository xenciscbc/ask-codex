#!/usr/bin/env python3
"""Script-owned consultation boundary. Python 3.11+, Git Bash on Windows."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import exercise
import guard as exercise_guard
import install as browser_install
import models as model_selection
from policy import ConfirmationRequired, resolve
from replies import classify
import repro as reproduction
import target as disposable_target

HERE = Path(__file__).resolve().parent
NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
# Constants of every Codex command line (consultations and exercises); never part of overrides or a summary.
# Child agents stay off: a role file can raise a child's sandbox and bring its own MCP servers (ADR 0008,
# .scratch/subagent-boundary). The feature switch too, because an enabled multi_agent_v2 feature in the user's or
# a trusted project's config defeats agents.enabled=false alone; command-line -c outranks config files.
# No approval lifts the run out of read-only: a resolved auto_review reviewer drops exec's headless Never and
# approved an escalation (.scratch/approval-boundary ticket 01, probe p9), and a trusted project's config can set
# either key, so both are pinned here. No execpolicy .rules file (user or project) is loaded either: an `allow`
# rule can run a command outside the sandbox whatever the approval policy (inferred from source, not probed).
EXEC_CONSTANTS = ("--disable", "apps", "-c", "agents.enabled=false", "-c", "features.multi_agent_v2.enabled=false",
                  "-c", 'approval_policy="never"', "-c", 'approvals_reviewer="user"', "--ignore-rules")


def cli():
    # This module as the exercise lifecycle sees it (also when run as __main__ or through runpy).
    return sys.modules[__name__]


class AlreadyAttempted(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def bash():
    if os.name == "nt":
        for root in (os.environ.get("ProgramFiles", "C:/Program Files"), "C:/Program Files"):
            candidate = Path(root) / "Git/bin/bash.exe"
            if candidate.exists():
                return str(candidate)
        raise ValueError("Git Bash is required on Windows")
    found = shutil.which("bash")
    if not found:
        raise ValueError("bash is required")
    return found


def shell_environment():
    env = os.environ.copy()
    if os.name == "nt":
        git = Path(bash()).parent.parent
        env["PATH"] = os.pathsep.join([str(git / "usr/bin"), str(git / "bin"), env.get("PATH", "")])
    return env


def command(args, cwd):
    # Shell source is constant; argv crosses Windows/MSYS via a data file.
    with tempfile.TemporaryDirectory(prefix="ask-codex-argv-") as temporary:
        argv = Path(temporary) / "argv"
        invocation = invocation_for(args, argv)
        result = subprocess.run(invocation, cwd=cwd, env=shell_environment(), capture_output=True, encoding="utf-8", timeout=60)
    if result.returncode:
        raise ValueError(f"Codex preflight command failed (exit {result.returncode}); check CLI installation, login and configuration")
    return result.stdout


def invocation_for(args, path):
    if any("\0" in arg for arg in args):
        raise ValueError("NUL is not allowed in arguments")
    path.write_bytes(b"\0".join(arg.encode("utf-8") for arg in args) + b"\0")
    return [bash(), (HERE / "_exec.sh").as_posix(), path.as_posix()]


def listing(project, overrides=()):
    servers = json.loads(command(["codex", "mcp", "list", "--json", *overrides], project))
    if not isinstance(servers, list) or any(not isinstance(s, dict) or
            not isinstance(s.get("name"), str) or not NAME.fullmatch(s["name"]) or
            not isinstance(s.get("enabled"), bool) for s in servers):
        raise ValueError("Invalid MCP listing or server name")
    if len({s["name"] for s in servers}) != len(servers):
        raise ValueError("Duplicate MCP server name")
    return servers


def mcp_get(project, name, overrides=()):
    server = json.loads(command(["codex", "mcp", "get", name, "--json", *overrides], project))
    if not isinstance(server, dict):
        raise ValueError("Invalid MCP server definition")
    return server


def which(name):
    # Resolved with the environment the script runs Codex with (plan I13, N-1), from PATH's absolute entries only:
    # never the current directory (shutil.which searches it first on Windows) and never a relative PATH entry.
    suffixes = (".exe",) if os.name == "nt" else ("",)
    for entry in shell_environment().get("PATH", "").split(os.pathsep):
        entry = entry.strip().strip('"')
        if not entry or not Path(entry).is_absolute():
            continue
        for suffix in suffixes:
            candidate = Path(entry) / (name + suffix)
            if candidate.is_file():
                return str(candidate)
    return None


def timer():
    override = os.environ.get("EVAL_ASK_CODEX_TIMEOUT_MINUTES")
    valid = override is not None and re.fullmatch(r"[1-9][0-9]*", override)
    return {"interval_minutes": int(override) if valid else 30,
            "source": "override" if valid else "default" if override is None else "ignored_override"}


def validate(request):
    if not isinstance(request, dict) or not isinstance(request.get("prompt"), str) or not request["prompt"].strip():
        raise ValueError("A prepared consultation prompt is required")
    project = Path(request["project"]).resolve(strict=True)
    models = request.get("models")
    if not isinstance(models, list) or not 1 <= len(models) <= 2:
        raise ValueError("A consultation takes one or two different models")
    names = []
    for model in models:
        if not isinstance(model, dict):
            raise ValueError("Each model choice must be an object")
        name = model.get("model")
        if name is not None and (not isinstance(name, str) or not NAME.fullmatch(name)):
            raise ValueError("Invalid model slug")
        if model.get("effort") not in ("medium", "high", "xhigh", "max", "ultra"):
            raise ValueError("Invalid consultation effort")
        if model["effort"] == "ultra" and not model.get("explicit_ultra"):
            raise ValueError("ultra requires an explicit user choice")
        names.append(name)
    if len(set(names)) != len(names) or (len(names) == 2 and None in names):
        raise ValueError("Parallel consultation needs two explicit different models")
    if reply_schema_of(request) == "discussion" and len(names) != 1:
        raise ValueError("A discussion takes exactly one model")
    return project


def reply_schema_of(request):
    schema = request.get("reply_schema", "consultation")
    if schema not in ("consultation", "discussion"):
        raise ValueError("Invalid reply schema")
    return schema


def preflight(request, neutral):
    project = validate(request)
    policy, overrides = resolve(request, project, neutral, listing)
    return {"project": str(project), "models": request["models"], "reply_schema": reply_schema_of(request), **policy}, overrides


def prepare(request_path, base):
    request = read_json(request_path)
    if exercise.is_request(request):
        return exercise.prepare(cli(), request, base)
    validate(request)
    with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
        summary, overrides = preflight(request, neutral)
    parent = Path(base).resolve() / "ask-codex"
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="run.", dir=parent))
    write_json(directory / "plan.json", {"version": 1, "request": request, "summary": summary, "timer": timer(),
                                        "overrides": overrides, "directory": str(directory)})
    return {"state": "prepared", "directory": str(directory), "summary": summary}


def plan_at(directory):
    # Non-strict, like prepare: some volumes (e.g. a RAM disk) cannot report a
    # final path, and a strict resolve fails there with a bare OSError.
    directory = Path(directory).resolve()
    plan = read_json(directory / "plan.json")
    if plan.get("version") != 1 or plan.get("directory") != str(directory) or directory.parent.name != "ask-codex" or not directory.name.startswith("run."):
        raise ValueError("Not an owned consultation run directory")
    return directory, plan


def remove_run(directory, plan):
    # On Windows a process can briefly hold a run file open after the run ends (e.g. a
    # Codex notify hook that inherited the worker's std handles); one bounded window
    # covers the whole removal, then the error stands.
    deadline = time.monotonic() + float(os.environ.get("ASK_CODEX_CLEANUP_WINDOW_S", "30"))

    def patiently(operation, path):
        while True:
            try:
                return operation(path)
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.25)

    # Preserve the ownership receipt until deletion succeeds, so a locked log does
    # not leave an unmanageable half-deleted directory on Windows.
    for child in directory.iterdir():
        if child.name == "plan.json":
            continue
        if child.is_dir() and not child.is_symlink():
            patiently(shutil.rmtree, child)
        else:
            patiently(Path.unlink, child)
    (directory / "plan.json").unlink()
    try:
        patiently(Path.rmdir, directory)
    except OSError:
        write_json(directory / "plan.json", plan)
        raise


def run(directory):
    directory, plan = plan_at(directory)
    if exercise.is_plan(plan):
        exercise.require_platform()
        exercise.claim_run(cli(), directory)  # `started` with this call's identity (C2 follow-up 7)
    else:
        try:
            with (directory / "started").open("x"):
                pass  # Never replay an execution attempt.
        except FileExistsError:
            raise AlreadyAttempted() from None
    if exercise.is_plan(plan):
        try:
            return run_exercise(directory, plan)
        except BaseException as error:
            # Interrupted (any exception, KeyboardInterrupt, ...) before Codex started: leave the failure receipt, so
            # finish and cleanup do not take the run for one still launching. main() replaces it with its own
            # result for the errors it reports.
            if not (directory / "clock.json").exists() and not (directory / "execution-error.json").exists():
                try:
                    write_json(directory / "execution-error.json",
                               {"state": "failed", "reason": f"The exercise run was interrupted before Codex started "
                                                             f"({type(error).__name__}); no automatic retry"})
                except OSError:
                    pass
            raise
    with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
        summary, overrides = preflight(plan["request"], neutral)
    if summary != plan["summary"] or overrides != plan["overrides"]:
        raise ValueError("Effective configuration changed; prepare and review a new consultation")

    def argv(model, child):
        args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
                "-C", Path(plan["summary"]["project"]).as_posix()]
        if model.get("model"):
            args += ["-m", model["model"]]
        return [*args, "-c", f'model_reasoning_effort="{model["effort"]}"', *overrides, *EXEC_CONSTANTS,
                "--output-schema", (HERE.parent / f"{plan['summary']['reply_schema']}.schema.json").as_posix(),
                "-o", (child / "last-message.json").as_posix(), "-"]

    return launch(directory, plan, argv, plan["summary"]["project"])


def run_exercise(directory, plan):
    # Guard (I6), identities, placement and the guard pass again, then the running supervisor, which holds the app
    # and the owned proxy port (C4, I8); its watcher stops Codex if the supervisor dies (U10). A failure ends the
    # app and removes the target at once.
    watcher = exercise.before_launch(cli(), directory, plan)
    try:
        schema = HERE.parent / f"{exercise.REPLY_SCHEMA}.schema.json"
        result = launch(directory, plan,
                        lambda model, child: exercise.codex_argv(plan, model, child, EXEC_CONSTANTS, schema),
                        plan["summary"]["target"])
    except Exception as error:
        # launch() returns launch_failed once a process may have started; an exception here is earlier.
        watcher.disarm()
        reason = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: exercise launch failed"
        raise ValueError(reason + exercise.removal_note(exercise.end_and_remove(cli(), directory, plan))) from None
    finally:
        watcher.disarm()
    if watcher.fired is not None:
        result["supervisor_died"] = {"at": watcher.fired, "codex_stop": "requested through the ADR 0004 stop path"}
    outcome = exercise.after_run(cli(), directory, plan)
    if outcome is not None:
        result["target_removed"] = outcome["target_removed"]
        result["ended"] = outcome["ended"]
        if not outcome["target_removed"]:
            result["retained_location"] = outcome.get("retained_location", str(directory))
    return result


def launch(directory, plan, argv, cwd):
    workers = []
    with ExitStack() as streams:
        launches = []
        # Prepare every file and handle before starting any billable process.
        for index, model in enumerate(plan["request"]["models"]):
            child = directory / str(index)
            child.mkdir()
            prompt = child / "prompt.md"
            prompt.write_text(plan["request"]["prompt"], encoding="utf-8")
            args = argv(model, child)
            invocation = invocation_for([bash(), (HERE / "run.sh").as_posix(), child.as_posix(), "--", *args], child / "argv")
            handles = {"stdin": streams.enter_context(prompt.open("rb")),
                       "stdout": streams.enter_context((child / "events.jsonl").open("wb")),
                       "stderr": streams.enter_context((child / "stderr.log").open("wb"))}
            write_json(child / "launch-pending.json", {"exit_code": -1, "reason": "Consultation did not start"})
            launches.append((child, invocation, handles))
        write_json(directory / "clock.json", {"started": time.time(), "next_check": time.time() + plan["timer"]["interval_minutes"] * 60})
        try:
            for child, invocation, handles in launches:
                worker = subprocess.Popen(invocation, cwd=cwd, env=shell_environment(), **handles)
                workers.append((worker, child))
                (child / "launch-pending.json").unlink()
            # Supervision is part of the launcher lifetime too. A failed
            # completion receipt must not abandon another billable worker.
            while workers:
                for worker, child in list(workers):
                    code = worker.poll()
                    if code is not None:
                        write_json(child / "result.json", {"exit_code": code})
                        workers.remove((worker, child))
                if workers:
                    time.sleep(0.1)
        except (OSError, ValueError, subprocess.SubprocessError):
            # Stop started processes before any recovery bookkeeping that may
            # itself fail on a damaged/unwritable filesystem.
            stop_requested = [child.name for _, child in workers if result_for(child) is None]
            failure = {"reason": "Consultation launcher failed; no automatic retry", "stop_requested": stop_requested}
            stopped = stop(directory, "stop", "none", set(stop_requested))
            failure["stop_requested"] = [s["index"] for s in stopped["stops"]]
            try:
                write_json(directory / "launch-error.json", failure)
            except OSError:
                pass
            for worker, child in workers:
                try:
                    code = worker.wait(timeout=5)
                    write_json(child / "result.json", {"exit_code": code})
                except (OSError, subprocess.TimeoutExpired):
                    pass  # run.sh writes its own durable completion receipt.
            return {"state": "launch_failed", "directory": str(directory), **failure,
                    "termination": stopped}
    return {"state": "finished", "directory": str(directory)}


def result_for(child):
    # The wrapper receipt is written only after descendant cleanup/watchers end.
    # Unlike exit-code, it also works if the Python launcher lost its Popen.
    for name in ("launcher-result.json", "result.json"):
        if (child / name).exists():
            return read_json(child / name)
    if (child.parent / "launch-error.json").exists() and (child / "launch-pending.json").exists():
        return read_json(child / "launch-pending.json")
    return None


def stop_status(child):
    if (child / "stop-status.json").exists():
        return read_json(child / "stop-status.json")
    launch_error = child.parent / "launch-error.json"
    requested = launch_error.exists() and child.name in read_json(launch_error).get("stop_requested", [])
    if requested or (child / "stop-request").exists():
        return {"confirmed": False, "status": "unconfirmed_stop",
                "reason": "Cancellation requested without durable verification",
                "retained_location": str(child.parent)}
    return None


def snapshot(directory, plan):
    if (directory / "execution-error.json").exists():
        return {**read_json(directory / "execution-error.json"), "directory": str(directory)}
    runs = []
    now = time.time()
    clock = read_json(directory / "clock.json") if (directory / "clock.json").exists() else None
    for index, model in enumerate(plan["request"]["models"]):
        child = directory / str(index)
        event_type, event_age = None, now - clock["started"] if clock else 0
        events = child / "events.jsonl"
        if events.exists() and events.stat().st_size:
            event_age = max(0, now - events.stat().st_mtime)
            try:
                # Read only the final bounded portion, not the entire event history.
                with events.open("rb") as source:
                    source.seek(max(0, events.stat().st_size - 65536))
                    event_type = json.loads(source.read().splitlines()[-1]).get("type")
            except (ValueError, IndexError):
                event_type = "unknown"
        state = "finished" if result_for(child) is not None else "running" if clock else "prepared"
        if stop_status(child) is not None:
            stopped = stop_status(child)
            state = "stopped" if stopped.get("confirmed") else "stop_unconfirmed"
        runs.append({"model": model.get("model"), "state": state, "last_event": event_type, "event_age_seconds": event_age})
    state = "finished" if all(r["state"] in ("finished", "stopped") for r in runs) else "running" if clock else "prepared"
    if not any(r["state"] == "running" for r in runs) and any(r["state"] == "stop_unconfirmed" for r in runs):
        state = "stop_unconfirmed"
    return {"state": state, "directory": str(directory), "timer": plan["timer"], "runs": runs,
            "elapsed_seconds": max(0, now - clock["started"]) if clock else 0}


def wait_for(directory, seconds):
    directory, plan = plan_at(directory)
    if exercise.is_plan(plan):
        exercise.require_platform()
    if not 0 <= seconds <= 60:
        raise ValueError("Wait duration must be between 0 and 60 seconds")
    end = time.monotonic() + seconds
    while True:
        status = snapshot(directory, plan)
        if status["state"] != "running":
            return status
        clock = read_json(directory / "clock.json")
        remaining = clock["next_check"] - time.time()
        if remaining <= 0:
            interval = plan["timer"]["interval_minutes"] * 60
            active = [r for r in status["runs"] if r["state"] == "running"]
            stale = [r for r in active if r["event_age_seconds"] > interval / 6]
            status["check"] = True
            if stale:
                status.update(state="decision_required", recommendation="wait" if all(r["event_age_seconds"] <= interval / 2 for r in stale) else "stop")
                record_check(directory, clock, status)
                return status
            record_check(directory, clock, status)
            clock["next_check"] = time.time() + interval
            write_json(directory / "clock.json", clock)
            return status
        left = min(end - time.monotonic(), remaining)
        if left <= 0:
            return status
        time.sleep(min(0.2, left))


def record_check(directory, clock, status):
    checks = clock.setdefault("checks", [])
    if not checks or checks[-1]["deadline"] != clock["next_check"]:
        checks.append({"deadline": clock["next_check"], "state": status["state"],
                       "elapsed_seconds": status["elapsed_seconds"], "runs": status["runs"],
                       "recommendation": status.get("recommendation")})
        write_json(directory / "clock.json", clock)


def continue_wait(directory):
    directory, plan = plan_at(directory)
    if exercise.is_plan(plan):
        exercise.require_platform()
    clock = read_json(directory / "clock.json")
    clock["next_check"] = time.time() + plan["timer"]["interval_minutes"] * 60
    write_json(directory / "clock.json", clock)
    return snapshot(directory, plan)


def collect(directory, after_delivery):
    directory, plan = plan_at(directory)
    if exercise.is_plan(plan):
        return exercise.collect(cli(), directory, plan, after_delivery)
    if (directory / "execution-error.json").exists() and not (directory / "clock.json").exists():
        output = read_json(directory / "execution-error.json")
        after_delivery.append(lambda: remove_run(directory, plan))
        return output
    runs = []
    for index, model in enumerate(plan["request"]["models"]):
        child = directory / str(index)
        if stop_status(child) is not None:
            stopped = stop_status(child)
            runs.append({"model": model.get("model"), "effort": model["effort"],
                         "state": "stopped" if stopped["confirmed"] else "stop_unconfirmed", "stop": stopped})
            continue
        if result_for(child) is None:
            return {"state": "running", "directory": str(directory)}
        code = result_for(child)["exit_code"]
        result = {"model": model.get("model"), "effort": model["effort"], "state": "failed", "exit_code": code}
        reply = child / "last-message.json"
        if code == 0 and reply.exists() and reply.stat().st_size:
            try:
                text = reply.read_text(encoding="utf-8")
                if text.strip():
                    result.update(state="completed", reply=classify(text, plan["summary"].get("reply_schema", "consultation")))
            except UnicodeError:
                pass
        if result["state"] == "failed":
            result["reason"] = "Codex execution failed" if code else "Codex returned no usable reply"
            errors = (child / "stderr.log").read_text(encoding="utf-8", errors="replace") if (child / "stderr.log").exists() else ""
            if any(token in errors.lower() for token in ("not logged in", "unauthorized", "codex login")):
                result["reason"] = "Codex is not logged in; run ! codex login, then request a new consultation"
        if result_for(child).get("reason"):
            result["reason"] = result_for(child)["reason"]
        runs.append(result)
    output = {"state": "collected", "directory": str(directory), "summary": plan["summary"], "timer": plan["timer"], "runs": runs,
              "checks": read_json(directory / "clock.json").get("checks", [])}
    if (directory / "launch-error.json").exists():
        output["launch_error"] = read_json(directory / "launch-error.json")
    unresolved = any(r["state"] == "stop_unconfirmed" for r in runs)
    if unresolved:
        (directory / "retained").touch()
        output["retained_location"] = str(directory)
    elif any(r["state"] == "stopped" for r in runs) and not all(result_for(directory / str(i)) is not None for i in range(len(runs))):
        output.update(state="settling", retained_location=str(directory))
    elif (directory / "retained").exists():
        # Destructive work runs only after the complete JSON has been flushed.
        def prune_content():
            plan["request"].pop("prompt", None)
            write_json(directory / "plan.json", plan)
            for i in range(len(runs)):
                for name in ("prompt.md", "last-message.json", "argv", "events.jsonl"):
                    (directory / str(i) / name).unlink(missing_ok=True)
        after_delivery.append(prune_content)
        output["retained_location"] = str(directory)
    else:
        after_delivery.append(lambda: remove_run(directory, plan))
    return output


def stop(directory, recommended, offered, only_children=None):
    directory, plan = plan_at(directory)
    if not exercise.is_plan(plan):
        return stop_codex(directory, plan, recommended, offered, only_children)
    # An exercise's app and target go once its Codex tree is confirmed ended, then I15's processes and the app
    # (I3, I8, I12, I15); anything unconfirmed keeps everything.
    return exercise.stop(cli(), directory, plan, recommended, offered, only_children)


def stop_codex(directory, plan, recommended, offered, only_children=None):
    statuses = []
    for index, model in enumerate(plan["request"]["models"]):
        child = directory / str(index)
        if only_children is not None and child.name not in only_children:
            continue
        if result_for(child) is not None and stop_status(child) is None:
            continue  # Finished opinions are held, not retroactively stopped.
        if not child.exists():
            raise ValueError("Run has not started; discard the prepared run instead")
        args = [bash(), (HERE / "stop.sh").as_posix(), child.as_posix(), "--interval",
                str(plan["timer"]["interval_minutes"]), "--interval-source",
                "override" if plan["timer"]["source"] == "override" else "default",
                "--recommended", recommended, "--offered", offered]
        try:
            (child / "stop-request").touch()
            with tempfile.TemporaryDirectory(prefix="ask-codex-stop-") as temporary:
                invocation = invocation_for(args, Path(temporary) / "argv")
                process = subprocess.Popen(invocation, env=shell_environment(), stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL)
                process.wait()
            status = read_json(child / "stop-status.json")
        except (OSError, ValueError, subprocess.SubprocessError):
            status = {"confirmed": False, "status": "unconfirmed_stop",
                      "reason": "Stopper could not return verifiable status", "retained_location": str(directory)}
            try:
                (child / "stop-request").touch()  # launcher can still honor cancellation
                write_json(child / "stop-status.json", status)
            except OSError:
                pass
        statuses.append({"index": str(index), "model": model.get("model"), **status})
        if not status["confirmed"]:
            try:
                (directory / "retained").touch()
            except OSError:
                pass
    if not statuses:
        return {"state": "finished", "directory": str(directory), "stops": []}
    return {"state": "stopped" if all(s["confirmed"] for s in statuses) else "stop_unconfirmed",
            "directory": str(directory), "stops": statuses}


def cleanup(directory):
    directory, plan = plan_at(directory)
    if exercise.is_plan(plan):
        exercise.require_platform()
        exercise.refuse_while_launching(directory)
    if (directory / "clock.json").exists():
        for index in range(len(plan["request"]["models"])):
            child = directory / str(index)
            if result_for(child) is None:
                raise ValueError("Cannot clean up: run has not settled")
            if stop_status(child) is not None and not stop_status(child)["confirmed"]:
                raise ValueError("Cannot clean up: process-tree stop is unconfirmed")
    if exercise.is_plan(plan):
        outcome = exercise.cleanup(cli(), directory, plan)
        if outcome["state"] != "removed":
            return outcome
        remove_run(directory, plan)
        return {"state": "cleaned", "ended": outcome["ended"]}
    remove_run(directory, plan)
    return {"state": "cleaned"}


# Exercise-only actions: the platform layer is selected (I13) before any of its functions is looked up.
EXERCISE_ACTIONS = ("target-create", "target-remove", "guard", "browser-install", "exercise-deps", "app-start",
                    "finish", "repro", "evidence-keep")
# Actions that take a second file argument: repro <run directory> <steps file>, evidence-keep <run directory> <keep file>.
SECOND_ARGUMENT = ("repro", "evidence-keep")
# --result <file>: an operation that can outlast one Bash tool call (the guard's browser checks, app-start's install
# and start commands, ending and removing a target) runs in the background and leaves its result in a file that
# `wait-result` waits on in the foreground (C4 review item 30). Seconds after which a pending result is reported lost.
RESULT_BOUNDS = {"guard": 3600, "finish": 1800, "stop": 1800, "cleanup": 1800, "repro": 900}
MAX_RESULT_WAIT = 60


def result_bound(action, path):
    if action != "app-start":
        return RESULT_BOUNDS[action]
    import supervisor
    try:
        _, plan = plan_at(path)
        installs = len((plan["request"].get("commands") or {}).get("install") or [])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        installs = 0
    timing = supervisor.TIMING
    # app-start's own wait (supervisor.wait_started) plus its ending and removal on a failure.
    return int(timing["install_timeout"] * installs + timing["start_timeout"] + 60 + 300)


def start_result(path, action, bound):
    """Create the result file exclusively with a pending record before the operation does anything."""
    path = Path(path)
    if not path.is_absolute() or not path.parent.is_dir():
        raise ValueError("--result needs an absolute file path in an existing directory")
    pending = {"state": "pending", "action": action, "started_at": time.time(), "bound_seconds": bound}
    try:
        with path.open("x", encoding="utf-8") as written:
            written.write(json.dumps(pending))
    except FileExistsError:
        raise ValueError("The --result file already exists; give a new file name") from None


def finish_result(path, result):
    path = Path(path)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=True), encoding="utf-8")
    temporary.replace(path)


def wait_result(path, seconds):
    """Block in the foreground until the result file holds the operation's result, or `seconds` pass."""
    if not 0 <= seconds <= MAX_RESULT_WAIT:
        raise ValueError(f"Wait duration must be between 0 and {MAX_RESULT_WAIT} seconds")
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("wait-result needs the absolute path given to --result")
    end = time.monotonic() + seconds
    while True:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            value = None
        except (OSError, ValueError):
            value = {"state": "pending"}  # being written
        if isinstance(value, dict) and value.get("state") != "pending":
            return value
        if isinstance(value, dict) and type(value.get("started_at")) in (int, float) and \
                type(value.get("bound_seconds")) in (int, float) and \
                time.time() - value["started_at"] > value["bound_seconds"]:
            return {"state": "lost", "action": value.get("action"),
                    "elapsed_seconds": round(time.time() - value["started_at"]),
                    "reason": f"The {value.get('action')} operation recorded no result within "
                              f"{value['bound_seconds']} seconds; its process may have ended without one"}
        if time.monotonic() >= end:
            if value is None:
                return {"state": "missing", "reason": "No result file yet: the operation has not started"}
            started = value.get("started_at")
            return {"state": "pending", "action": value.get("action"),
                    "elapsed_seconds": round(time.time() - started) if type(started) in (int, float) else None}
        time.sleep(min(0.5, max(0.0, end - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("resolve", "prepare", "run", "collect", "wait", "continue", "stop", "cleanup",
                                           "finish", "target-create", "target-remove", "guard", "browser-install",
                                           "exercise-deps", "app-start", "wait-result", "repro", "evidence-keep"))
    parser.add_argument("path", nargs="?")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--base", default=tempfile.gettempdir())
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--recommended", choices=("wait", "stop"), default="stop")
    parser.add_argument("--offered", choices=("wait,stop", "none"), default="none")
    parser.add_argument("--result")
    args = parser.parse_args()
    if args.path is None and args.action not in ("browser-install", "exercise-deps"):
        parser.error(f"{args.action} needs a path")
    if (args.file is None) == (args.action in SECOND_ARGUMENT):
        parser.error(f"{args.action} takes a run directory and a file" if args.action in SECOND_ARGUMENT else
                     f"{args.action} takes one path")
    if args.result is not None and args.action not in (*RESULT_BOUNDS, "app-start"):
        parser.error(f"--result applies to {', '.join((*RESULT_BOUNDS, 'app-start'))} only")
    if args.result is not None:
        try:
            start_result(args.result, args.action, result_bound(args.action, args.path))
        except (ValueError, OSError) as error:
            print(json.dumps({"state": "failed", "reason": str(error) if isinstance(error, ValueError) else
                              f"{type(error).__name__}: the result file could not be created; nothing was done"},
                             ensure_ascii=True), flush=True)
            return 1
    record_failure = True
    after_delivery = []
    try:
        if args.action in EXERCISE_ACTIONS:
            exercise.require_platform()  # I13: the platform layer, before any of it is looked up
        if args.action == "wait-result":
            result = wait_result(args.path, args.seconds)
        elif args.action == "resolve":
            result = model_selection.resolve(read_json(args.path))
        elif args.action == "prepare":
            result = prepare(args.path, args.base)
        elif args.action == "wait":
            result = wait_for(args.path, args.seconds)
        elif args.action == "continue":
            result = continue_wait(args.path)
        elif args.action == "collect":
            result = collect(args.path, after_delivery)
        elif args.action == "stop":
            result = stop(args.path, args.recommended, args.offered)
        elif args.action == "target-create":
            # Disposable target of an exercise (target.py; Windows only).
            result = disposable_target.create_command(args.path, args.base)
        elif args.action == "target-remove":
            result = disposable_target.remove_command(args.path)
        elif args.action == "finish":
            result = exercise.finish(cli(), args.path)
        elif args.action == "app-start":
            # The app's processes of a guarded exercise under its supervisor (supervisor.py, C4).
            result = exercise.app_start(cli(), args.path)
        elif args.action == "guard":
            # Dependency check and browser guard of a prepared exercise, before any app process (guard.py, I7).
            result = exercise_guard.guard_exercise(cli(), args.path)
        elif args.action == "browser-install":
            # The pinned browser MCP server into the user-level state directory (install.py, I5).
            result = browser_install.install(cli())
        elif args.action == "exercise-deps":
            result = exercise_guard.dependency_report(cli())
        elif args.action == "repro":
            # One reproduction of a bug claim in the exercise's restricted browser (repro.py, C6, I10).
            result = reproduction.repro(cli(), args.path, args.file)
        elif args.action == "evidence-keep":
            # Chosen evidence moved out of the target before finish (repro.py, C6, I9).
            result = reproduction.keep(cli(), args.path, args.file)
        else:
            result = globals()[args.action](args.path)
    except ConfirmationRequired as error:
        result = {"state": "confirmation_required", "pending": error.pending}
    except AlreadyAttempted:
        record_failure = False
        result = {"state": "failed", "reason": "This consultation execution was already attempted; do not replay it"}
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        result = {"state": "failed", "reason": str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else f"{type(error).__name__}: consultation operation failed"}
    if record_failure and args.action == "run" and result["state"] in ("failed", "confirmation_required"):
        try:
            directory, _ = plan_at(args.path)
            # A replay failure must not poison the original, possibly still-active run.
            if not (directory / "clock.json").exists():
                write_json(directory / "execution-error.json", result)
        except (OSError, ValueError, KeyError):
            pass
    if args.result is not None:
        try:
            finish_result(args.result, result)
        except OSError:
            pass  # stdout still carries the result; wait-result reports the operation lost after its bound
    try:
        # ASCII-safe JSON preserves Unicode values even on Windows legacy code pages.
        print(json.dumps(result, ensure_ascii=True), flush=True)
    except (OSError, UnicodeError):
        try:
            sys.stdout.close()
        except OSError:
            pass
        print(json.dumps({"state": "delivery_failed", "retained_location": result.get("directory", args.path),
                          "reason": "Output could not be delivered; collect the retained run again"
                          if args.action == "collect" else "Output could not be delivered; inspect operation state"}),
              file=sys.stderr, flush=True)
        return 1
    for finish in after_delivery:
        try:
            finish()
        except OSError:
            # The reply is already delivered on stdout. Report cleanup separately
            # without replacing it or appending a second stdout JSON document.
            print(json.dumps({"state": "cleanup_failed", "retained_location": args.path}),
                  file=sys.stderr, flush=True)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
