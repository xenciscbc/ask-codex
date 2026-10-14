"""C6 live check (plan claim C6, Live): no Codex at all — the stub `codex` (evals/_harness/stub) stands in for every
Codex command, so zero `codex exec` or real Codex calls are made. Real parts: the browser guard (real Chrome and the
pinned chrome-devtools-mcp), the supervisor and the fixture app, and the reproductions.

    python -I .scratch/exercise-skills/evidence/c6-live-check.py <output json>

1. Builds the fixture project D:\\tmp\\ui-exercise-fixture (signup demo: static frontend 127.0.0.1:15173, JSON backend
   127.0.0.1:18080, a seeded data file; planted bug: an empty email is accepted with "Welcome!"), the target root
   D:\\tmp\\ui-exercise-targets and the scratch base D:\\tmp\\c6-base; records a process baseline (PID + creation time).
2. prepare -> guard (real) -> app-start -> run (stub codex) -> wait -> collect.
3. repro 1: a multi-step reproduction (navigate, fill, click, take_snapshot, wait_for the planted text): completed.
   repro 2: an out-of-origin navigate (the sentinel port 18081 and an external URL): refused, nothing started.
   repro 3: an element that does not exist: step_failed at that step, later steps not run.
   After each: the registration directory holds no job, no process created by it is left.
4. evidence-keep: one screenshot moved to D:\\tmp\\c6-kept (new file name, source gone); a `..` reference refused.
5. finish; then every process created after the baseline that is still alive is listed (by creation time), with
   any whose command line names the run's directories flagged; the guard cache entry this run added is removed.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/ask/scripts"
CLI = SCRIPTS / "consult.py"
STUB = REPO / "evals/_harness/stub"
FIXTURE, TARGETS, BASE = Path(r"D:\tmp\ui-exercise-fixture"), Path(r"D:\tmp\ui-exercise-targets"), Path(r"D:\tmp\c6-base")
KEPT, WORK = Path(r"D:\tmp\c6-kept"), Path(r"D:\tmp\c6-work")
sys.path.insert(0, str(SCRIPTS))
import browser  # noqa: E402
import winjob  # noqa: E402

BACKEND = r'''"""Signup demo backend on 127.0.0.1:18080 (standard library only). Planted bug (C6): an empty email is accepted."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(__file__).with_name("seed.json")


class Api(BaseHTTPRequestHandler):
    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:15173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        users = json.loads(DATA.read_text())
        users["users"].append({"email": body.get("email", "")})  # the planted bug: no check of an empty email
        DATA.write_text(json.dumps(users))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.cors()
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Welcome!"}).encode())

    def log_message(self, *args):
        pass


ThreadingHTTPServer(("127.0.0.1", 18080), Api).serve_forever()
'''

SIGNUP = '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Sign up</title></head>
<body>
<h1>Create your account</h1>
<form id="signup">
  <label>Email <input type="email" name="email"></label>
  <label>Password <input type="password" name="password"></label>
  <button type="submit">Sign up</button>
</form>
<p id="message"></p>
<script>
document.getElementById("signup").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  const response = await fetch("http://127.0.0.1:18080/api/signup", {method: "POST", body: JSON.stringify(data)});
  const answer = await response.json();
  document.getElementById("message").textContent = answer.message;
  console.log("signup answered; session token=AbCdEf0123456789XyZ0123456789");
});
</script>
</body>
</html>
'''

REPLY = {"claims": [{"category": "bug", "statement": "Signing up with an empty email shows Welcome!.",
                     "steps": ["Open http://127.0.0.1:15173/signup.html", "Type hunter22 into the textbox named Password",
                               "Click the button named Sign up"],
                     "expected": "An error saying the email is required", "actual": "Welcome!", "viewport": "1280x720",
                     "evidence": ["signup-empty.png"], "confidence": "high", "in_scope": True}],
         "out_of_scope": [], "coverage": {"pages": ["/signup.html"], "flows": ["sign up"], "viewports": ["1280x720"]}}


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def processes():
    """(pid, creation time) -> (parent pid, image) of every process now."""
    found = {}
    for pid, parent, image in winjob.processes():
        created = winjob.creation_time(pid)
        if created is not None:
            found[(pid, created)] = (parent, image)
    return found


def new_alive(before, roots):
    """Processes created after `before` was taken that are alive now (by PID + creation time, never by name), each
    with its image, its parent (and whether that parent existed before), whether its command line names the run's
    directories or nonce, and whether it carries a --user-data-dir inside the run's directories."""
    now, found = processes(), []
    me = winjob.creation_time(os.getpid())
    for (pid, created), (parent, image) in now.items():
        if (pid, created) in before or pid == os.getpid() or created < me:
            continue
        line = (winjob.command_line(pid) or "").casefold()
        data_dirs = [part.split("--user-data-dir=", 1)[1] for part in line.split() if part.startswith("--user-data-dir=")]
        found.append({"pid": pid, "image": winjob.image_path(pid) or image, "parent": parent,
                      "parent_existed_before": any(p == parent for p, _ in before),
                      "names_the_run": any(r in line for r in roots),
                      "has_user_data_dir": bool(data_dirs),
                      "user_data_dir_in_run": any(any(r in d for r in roots) for d in data_dirs)})
    return found


def main(output):
    for path in (FIXTURE, TARGETS, BASE, KEPT, WORK):
        if path.exists():
            raise SystemExit(f"{path} exists; remove it first (reset by deleting D:\\tmp\\ui-exercise-* and c6-*)")
    records, home = WORK / "records", WORK / "home"
    for directory in (TARGETS, BASE, KEPT, records, home):
        directory.mkdir(parents=True)
    write(FIXTURE / "README.md", "# Signup demo (C6 live fixture)\n")
    write(FIXTURE / "backend/server.py", BACKEND)
    write(FIXTURE / "backend/seed.json", json.dumps({"users": [{"email": "ada@example.invalid"}]}))
    write(FIXTURE / "frontend/signup.html", SIGNUP)
    write(FIXTURE / ".stub/scenario.json", json.dumps({"records": str(records), "exec": {"reply": REPLY}}))
    cache = browser.guard_cache_directory()
    cache_before = set(os.listdir(cache)) if cache.exists() else set()
    started_at = time.time()
    baseline = processes()
    env = {**os.environ, "CODEX_HOME": str(home / ".codex"),
           "PATH": os.pathsep.join([str(STUB), os.environ["PATH"]])}
    log = {"started_at": started_at, "fixture": str(FIXTURE), "steps": []}

    def cli(*args, timeout=900):
        began = time.time()
        result = subprocess.run([sys.executable, str(CLI), *map(str, args)], env=env, capture_output=True, text=True,
                                encoding="utf-8", timeout=timeout)
        try:
            value = json.loads(result.stdout)
        except ValueError:
            value = {"stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:]}
        log["steps"].append({"call": [str(a) for a in args[:1]], "seconds": round(time.time() - began, 1),
                             "result": value})
        print(args[0], value.get("state"), flush=True)
        return value

    def registered(directory):
        folder = Path(directory) / "repro-jobs"
        return sorted(os.listdir(folder)) if folder.exists() else []

    request = {"interaction": "exercise", "kind": "ui", "project": str(FIXTURE),
               "prompt": "Exercise type: UI exercise.\nC6 live check (stub codex).",
               "models": [{"model": None, "effort": "medium"}],
               "target_root": {"path": str(TARGETS), "confirmed_by_user": True},
               "app": ["127.0.0.1:15173", "127.0.0.1:18080"], "headed": False, "scope": "the signup form",
               "commands": {"start": [{"argv": [sys.executable, "-I", "backend/server.py"]},
                                      {"argv": [sys.executable, "-I", "-m", "http.server", "15173", "--bind", "127.0.0.1",
                                                "--directory", "frontend"]}]}}
    write(WORK / "request.json", json.dumps(request))
    ready = cli("prepare", WORK / "request.json", "--base", BASE)
    directory = Path(ready["directory"])
    plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
    evidence = Path(plan["browser"]["evidence"])
    cli("guard", directory)
    cli("app-start", directory)
    cli("run", directory)
    cli("wait", directory, "--seconds", "30")
    cli("collect", directory)

    write(WORK / "repro-1.json", json.dumps({"claim": "C1", "steps": [
        {"action": "navigate", "url": "http://127.0.0.1:15173/signup.html"},
        {"action": "take_snapshot"},
        {"action": "fill", "element": {"role": "textbox", "name": "Password"}, "value": "hunter22"},
        {"action": "click", "element": {"role": "button", "name": "Sign up"}},
        {"action": "wait_for", "text": "Welcome!"},
        {"action": "list_console_messages"}]}))
    roots = [str(TARGETS).casefold(), str(BASE).casefold(), plan["summary"]["browser_server"].casefold()]
    before = processes()
    log["repro_1"] = cli("repro", directory, WORK / "repro-1.json")
    log["repro_1_new_processes_alive"] = new_alive(before, roots)
    log["registered_after_repro_1"] = registered(directory)
    write(WORK / "repro-2.json", json.dumps({"claim": "C1", "steps": [
        {"action": "navigate", "url": "http://127.0.0.1:18081/"},
        {"action": "navigate", "url": "https://example.com/"},
        {"action": "wait_for", "text": "Welcome!"}]}))
    before = processes()
    log["repro_2"] = cli("repro", directory, WORK / "repro-2.json")
    log["repro_2_new_processes_alive"] = new_alive(before, roots)
    log["registered_after_repro_2"] = registered(directory)
    write(WORK / "repro-3.json", json.dumps({"claim": "C1", "steps": [
        {"action": "navigate", "url": "http://127.0.0.1:15173/signup.html"},
        {"action": "click", "element": {"role": "button", "name": "Delete account"}},
        {"action": "wait_for", "text": "Welcome!"}]}))
    before = processes()
    log["repro_3"] = cli("repro", directory, WORK / "repro-3.json")
    log["repro_3_new_processes_alive"] = new_alive(before, roots)
    log["registered_after_repro_3"] = registered(directory)
    shots = log["repro_1"].get("screenshots") or []
    log["evidence_before_keep"] = sorted(os.listdir(evidence))
    write(WORK / "keep.json", json.dumps({"destination": str(KEPT), "files": [shots[-1] if shots else "none.png",
                                                                            "..\\target.json"]}))
    log["keep"] = cli("evidence-keep", directory, WORK / "keep.json")
    log["kept_files"] = {name: (KEPT / name).stat().st_size for name in sorted(os.listdir(KEPT))}
    for name in sorted(os.listdir(KEPT))[:1]:
        shutil.copyfile(KEPT / name, Path(output).with_name("c6-live-kept-screenshot.png"))
    log["evidence_after_keep"] = sorted(os.listdir(evidence))
    log["finish"] = cli("finish", directory)
    time.sleep(2)
    left = new_alive(baseline, roots)
    log["processes_created_after_baseline_still_alive"] = left
    log["run_processes_left"] = [p for p in left if p["names_the_run"] or p["user_data_dir_in_run"]]
    log["targets_left"] = sorted(os.listdir(TARGETS))
    log["run_directory_left"] = directory.exists()
    log["exec_sentinel_lines"] = len((records / "exec.sentinel").read_text("utf-8").splitlines())
    log["violations"] = (records / "violations.log").read_text("utf-8") if (records / "violations.log").exists() else ""
    added = (set(os.listdir(cache)) if cache.exists() else set()) - cache_before
    for name in added:
        os.unlink(cache / name)
    log["guard_cache_entries_added_and_removed"] = sorted(added)
    Path(output).write_text(json.dumps(log, indent=1, ensure_ascii=False), encoding="utf-8")
    for path in (FIXTURE, BASE, WORK, KEPT):
        shutil.rmtree(path, ignore_errors=True)
    try:
        TARGETS.rmdir()
    except OSError:
        pass
    print(json.dumps({k: log[k] for k in ("run_processes_left", "targets_left", "run_directory_left",
                                          "exec_sentinel_lines", "violations")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
