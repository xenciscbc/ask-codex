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
import models as model_selection
from policy import ConfirmationRequired, resolve
from replies import classify

HERE = Path(__file__).resolve().parent
NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


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
    return project


def preflight(request, neutral):
    project = validate(request)
    policy, overrides = resolve(request, project, neutral, listing)
    return {"project": str(project), "models": request["models"], **policy}, overrides


def prepare(request_path, base):
    request = read_json(request_path)
    validate(request)
    with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
        summary, overrides = preflight(request, neutral)
    parent = Path(base).resolve() / "ask-codex"
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="run.", dir=parent))
    override = os.environ.get("EVAL_ASK_CODEX_TIMEOUT_MINUTES")
    valid = override is not None and re.fullmatch(r"[1-9][0-9]*", override)
    timer = {"interval_minutes": int(override) if valid else 30,
             "source": "override" if valid else "default" if override is None else "ignored_override"}
    write_json(directory / "plan.json", {"version": 1, "request": request, "summary": summary, "timer": timer,
                                        "overrides": overrides, "directory": str(directory)})
    return {"state": "prepared", "directory": str(directory), "summary": summary}


def plan_at(directory):
    directory = Path(directory).resolve(strict=True)
    plan = read_json(directory / "plan.json")
    if plan.get("version") != 1 or plan.get("directory") != str(directory) or directory.parent.name != "ask-codex" or not directory.name.startswith("run."):
        raise ValueError("Not an owned consultation run directory")
    return directory, plan


def remove_run(directory, plan):
    # Preserve the ownership receipt until deletion succeeds, so a locked log does
    # not leave an unmanageable half-deleted directory on Windows.
    for child in directory.iterdir():
        if child.name == "plan.json":
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    (directory / "plan.json").unlink()
    try:
        directory.rmdir()
    except OSError:
        write_json(directory / "plan.json", plan)
        raise


def run(directory):
    directory, plan = plan_at(directory)
    try:
        with (directory / "started").open("x"):
            pass  # Never replay an execution attempt.
    except FileExistsError:
        raise AlreadyAttempted() from None
    with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
        summary, overrides = preflight(plan["request"], neutral)
    if summary != plan["summary"] or overrides != plan["overrides"]:
        raise ValueError("Effective configuration changed; prepare and review a new consultation")
    workers = []
    with ExitStack() as streams:
        launches = []
        # Prepare every file and handle before starting any billable process.
        for index, model in enumerate(plan["request"]["models"]):
            child = directory / str(index)
            child.mkdir()
            prompt = child / "prompt.md"
            prompt.write_text(plan["request"]["prompt"], encoding="utf-8")
            args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
                    "-C", Path(plan["summary"]["project"]).as_posix()]
            if model.get("model"):
                args += ["-m", model["model"]]
            args += ["-c", f'model_reasoning_effort="{model["effort"]}"', *overrides,
                     "--disable", "apps", "--output-schema", (HERE.parent / "consultation.schema.json").as_posix(),
                     "-o", (child / "last-message.json").as_posix(), "-"]
            invocation = invocation_for([bash(), (HERE / "run.sh").as_posix(), child.as_posix(), "--", *args], child / "argv")
            handles = {"stdin": streams.enter_context(prompt.open("rb")),
                       "stdout": streams.enter_context((child / "events.jsonl").open("wb")),
                       "stderr": streams.enter_context((child / "stderr.log").open("wb"))}
            write_json(child / "launch-pending.json", {"exit_code": -1, "reason": "Consultation did not start"})
            launches.append((child, invocation, handles))
        write_json(directory / "clock.json", {"started": time.time(), "next_check": time.time() + plan["timer"]["interval_minutes"] * 60})
        try:
            for child, invocation, handles in launches:
                worker = subprocess.Popen(invocation, cwd=plan["summary"]["project"], env=shell_environment(), **handles)
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
    clock = read_json(directory / "clock.json")
    clock["next_check"] = time.time() + plan["timer"]["interval_minutes"] * 60
    write_json(directory / "clock.json", clock)
    return snapshot(directory, plan)


def collect(directory, after_delivery):
    directory, plan = plan_at(directory)
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
                    result.update(state="completed", reply=classify(text))
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
    if (directory / "clock.json").exists():
        for index in range(len(plan["request"]["models"])):
            child = directory / str(index)
            if result_for(child) is None:
                raise ValueError("Cannot clean up: run has not settled")
            if stop_status(child) is not None and not stop_status(child)["confirmed"]:
                raise ValueError("Cannot clean up: process-tree stop is unconfirmed")
    remove_run(directory, plan)
    return {"state": "cleaned"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("resolve", "prepare", "run", "collect", "wait", "continue", "stop", "cleanup"))
    parser.add_argument("path")
    parser.add_argument("--base", default=tempfile.gettempdir())
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--recommended", choices=("wait", "stop"), default="stop")
    parser.add_argument("--offered", choices=("wait,stop", "none"), default="none")
    args = parser.parse_args()
    record_failure = True
    after_delivery = []
    try:
        if args.action == "resolve":
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
