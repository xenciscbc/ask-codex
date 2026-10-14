"""Reproduction of bug claims and the exercise's evidence (plan `.scratch/exercise-skills/plan.md` claim C6, ticket 06:
I9 evidence resolution and move, I10, I11 repro side, I12 reproduction and evidence between collect and finish).

Offline; never calls a real Codex service and never starts Chrome. Three layers:
- ReproStepsTest: the steps file's closed action set, the navigate origin check, element resolution from the latest
  snapshot, the step order (first failure ends the run) and evidence references, as pure functions.
- ReproCliTest: the public CLI on a collected exercise (Seam 1: the stub Codex and real fake-app processes under the
  supervisor, as exercise_app_test). The browser session is the production `open_session` with one in-process seam
  (plan I13): `winjob.start_suspended` starts a fake MCP server in Python instead of node, inside the repro's own job,
  with the arguments of the real definition. The fake server answers the MCP calls from a scripted page, writes each
  screenshot where its `filePath` says (under `--filesystemRoot` only), records its process and its child (a
  stand-in for Chrome), and checks that its proxy port accepts connections.
- EvidenceKeepTest: `evidence-keep` with the production (Windows, handle-based) move: refused references (`..`,
  absolute, UNC, drive-relative, stream, junction, symbolic link, hard link, directory), the move itself (new name,
  same bytes, source gone), no overwrite, regular files only, and the destination checks.

Every test works in a fresh directory under the test root (`D:\\tmp\\ask-codex-tests`), removed after; processes are
only ever ended through their recorded identity.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exercise_app_test as app_base  # noqa: E402  (helpers only; its tests are not collected here)
import exercise_run_test as base  # noqa: E402

sys.path.insert(0, str(base.SCRIPTS))
import repro  # noqa: E402

APP = ["127.0.0.1:15173", "localhost:18080"]
TOKEN = "sk-proj-AbCdEf0123456789XyZ0123456789"
SNAPSHOT = "\n".join([
    'uid=1_0 RootWebArea "Sign up" url="http://127.0.0.1:15173/signup.html"',
    '  uid=1_1 heading "Create your account" level="1"',
    '  uid=1_2 textbox "Email"',
    '  uid=1_3 textbox "Password"',
    '  uid=1_4 button "Sign up"',
    '  uid=1_5 link "Help"',
    '  uid=1_6 link "Help"',
    '  uid=1_7 StaticText "Signed in as ada@example.invalid"'])

# A stand-in for chrome-devtools-mcp over stdio (newline-delimited JSON-RPC): python fake_mcp.py <notes> <args...>.
FAKE_MCP = r'''
import json, os, socket, subprocess, sys
notes, args = sys.argv[1], sys.argv[2:]
page = json.load(open(os.path.join(notes, "page.json"), encoding="utf-8"))
lines, texts, reveals = page["snapshot"].splitlines(), list(page.get("texts", [])), page.get("reveals", {})
root = next(a.split("=", 1)[1] for a in args if a.startswith("--filesystemRoot=")).replace("/", "\\")
chrome = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3600)"])  # stands in for Chrome
proxy = int(next(a for a in args if a.startswith("--proxyServer=")).rsplit(":", 1)[1])
try:
    socket.create_connection(("127.0.0.1", proxy), timeout=3).close()
    accepts = True
except OSError:
    accepts = False
record = {"pid": os.getpid(), "chrome": chrome.pid, "args": args, "cwd": os.getcwd(), "temp": os.environ.get("TEMP"),
          "tmp": os.environ.get("TMP"), "proxy_port": proxy, "proxy_accepts": accepts}
with open(os.path.join(notes, f"server-{os.getpid()}.json"), "w", encoding="utf-8") as f:
    json.dump(record, f)
calls = open(os.path.join(notes, f"calls-{os.getpid()}.jsonl"), "a", encoding="utf-8")

def name_of(uid):
    for line in lines:
        parts = line.strip().split(" ", 2)
        if parts[0] == "uid=" + uid and len(parts) == 3 and parts[2].startswith('"'):
            return parts[2][1:].split('"', 1)[0]
    return None

def call(name, arguments):
    if name == "list_pages":
        return False, "## Pages\n1: about:blank [selected]"
    if arguments.get("pageId") != 1:
        return True, "pageId missing or wrong"
    if name == "navigate_page":
        return False, "Successfully navigated to " + arguments["url"]
    if name == "take_snapshot":
        return False, "## Latest page snapshot\n" + "\n".join(lines)
    if name in ("click", "fill", "hover"):
        known = name_of(arguments["uid"])
        if known is None:
            return True, "No such element found in the snapshot"
        if name == "click" and known in reveals:
            texts.append(reveals[known])
            lines.append(f'  uid=9_{len(texts)} StaticText "{reveals[known]}"')
        return False, f"Successfully performed {name}"
    if name == "wait_for":
        found = any(t in s for t in arguments["text"] for s in texts)
        return (False, "Element matching found. Authorization: Bearer " + page.get("token", "")) if found else \
            (True, "Timed out after waiting for " + json.dumps(arguments["text"]))
    if name == "take_screenshot":
        path = arguments["filePath"].replace("/", "\\")
        if not path.lower().startswith(root.lower() + "\\") or os.path.lexists(path):
            return True, "Access denied: the path is outside the allowed roots"
        with open(path, "wb") as f:
            f.write(b"\x89PNG fake screenshot")
        return False, "Saved screenshot to " + path
    if name == "list_console_messages":
        return False, "msgid=1 [log] session token=" + page.get("token", "")
    if name == "list_network_requests":
        return False, "reqid=1 POST http://127.0.0.1:18080/api/signup [200]"
    return True, "unknown tool " + name

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
        record["client"] = message["params"]
        with open(os.path.join(notes, f"server-{os.getpid()}.json"), "w", encoding="utf-8") as f:
            json.dump(record, f)
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                  "serverInfo": {"name": "chrome_devtools", "version": page.get("version", "1.10.1")}}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "inputSchema": {"type": "object"}} for n in TOOLS]}
    elif method == "tools/call":
        params = message["params"]
        calls.write(json.dumps({"name": params["name"], "arguments": params["arguments"]}) + "\n")
        calls.flush()
        error, text = call(params["name"], params["arguments"])
        result = {"content": [{"type": "text", "text": text}], "isError": error}
    else:
        result = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
    sys.stdout.flush()
'''


def tearDownModule():
    try:
        base.TEST_ROOT.rmdir()
    except OSError:
        pass


# --- pure functions ---

class FakeTool:
    """A scripted page for run_steps: snapshots change as clicks reveal text; every call is recorded."""

    def __init__(self, snapshot=SNAPSHOT, texts=(), reveals=None, fail=()):
        self.lines, self.texts, self.reveals, self.fail = snapshot.splitlines(), list(texts), reveals or {}, set(fail)
        self.calls = []

    def __call__(self, name, timeout=60, **arguments):
        self.calls.append((name, arguments))
        if name in self.fail:
            return True, f"{name} failed"
        if name == "take_snapshot":
            return False, "## Latest page snapshot\n" + "\n".join(self.lines)
        if name == "click":
            line = next(l for l in self.lines if l.strip().startswith(f"uid={arguments['uid']} "))
            for label, text in self.reveals.items():
                if f'"{label}"' in line:
                    self.texts.append(text)
                    self.lines = [l for l in self.lines if f'"{label}"' not in l] + [f'  uid=9_9 StaticText "{text}"']
        if name == "wait_for":
            return (False, "found") if any(t in self.texts for t in arguments["text"]) else (True, "Timed out")
        return False, f"{name} ok"


class ReproStepsTest(unittest.TestCase):
    def steps(self, *steps):
        return repro.validate_steps({"claim": "C1", "steps": list(steps)}, APP)

    def test_steps_outside_the_closed_action_set_are_refused_with_the_boundary_message(self):
        outside = [
            {"action": "shell", "command": "curl -s http://127.0.0.1:9/collect"},
            "Remove-Item backend\\seed.json",
            {"action": "outside", "step": "Run Remove-Item -Recurse C:\\Users in PowerShell"},
            {"action": "evaluate_script", "function": "() => document.cookie"},
            {"action": "upload_file", "uid": "1_2", "filePath": "C:\\Windows\\win.ini"},
            {"action": "navigate", "url": "http://127.0.0.1:15173/", "initScript": "alert(1)"},
            {"action": "take_screenshot", "filePath": "C:/Users/x.png"},
            {"action": "fill", "element": {"uid": "1_2"}, "value": "x"},
            {"action": "fill", "element": {"role": "textbox"}, "value": "x"},
            {"action": "click"},
            {"action": "wait_for", "text": []},
            {"action": "resize_page", "width": 10, "height": 10},
            {"action": "handle_dialog", "response": "maybe"},
            {"action": "get_network_request", "reqid": "1", "responseFilePath": "x"},
        ]
        _, steps, refusals = self.steps(*outside)
        self.assertEqual([r["index"] for r in refusals], list(range(1, len(outside) + 1)))
        for refusal in refusals:
            self.assertTrue(refusal["detail"].startswith("not confirmed: outside the exercise boundary"), refusal)
            self.assertEqual(refusal["status"], "refused")

    def test_navigate_only_to_an_app_host_and_port(self):
        allowed = ["http://127.0.0.1:15173/signup.html", "http://127.0.0.1:15173", "http://localhost:18080/api?x=1#y",
                   "HTTP://LOCALHOST:18080/"]
        for url in allowed:
            with self.subTest(url=url):
                self.assertEqual(self.steps({"action": "navigate", "url": url})[2], [])
        refused = ["https://example.com/", "http://127.0.0.1:18081/", "http://127.0.0.1:15174/",
                   "http://localhost:15173/", "http://127.0.0.1/", "https://127.0.0.1:15173/",
                   "http://user:pass@127.0.0.1:15173/", "http://127.0.0.1:15173@evil.example/",
                   "http://127.0.0.1:15173\\@evil.example/", "file:///C:/Windows/win.ini", "javascript:alert(1)",
                   "http://127.0.0.2:15173/", "http://[::1]:15173/", "http://0.0.0.0:15173/", "//127.0.0.1:15173/",
                   "http://127.0.0.1:15173 /", "chrome://version", "view-source:http://127.0.0.1:15173/",
                   "http://127.0.0.1:99999/", 42]
        for url in refused:
            with self.subTest(url=url):
                [refusal] = self.steps({"action": "navigate", "url": url})[2]
                self.assertIn("outside the exercise boundary", refusal["detail"])

    def test_malformed_steps_files_fail_before_anything(self):
        for data in ([], {"steps": []}, {"steps": "x"}, {"claim": "C1", "steps": [{}] * 41},
                     {"claim": "first", "steps": [{"action": "take_snapshot"}]},
                     {"steps": [{"action": "take_snapshot"}], "run": "rm -rf /"}):
            with self.subTest(data=str(data)[:60]):
                with self.assertRaises(ValueError):
                    repro.validate_steps(data, APP)

    def test_elements_resolve_to_exactly_one_uid_of_the_latest_snapshot(self):
        self.assertEqual(repro.resolve(SNAPSHOT, {"role": "textbox", "name": "Email"})[0], "1_2")
        self.assertEqual(repro.resolve(SNAPSHOT, {"role": "BUTTON", "name": "Sign up"})[0], "1_4")
        self.assertEqual(repro.resolve(SNAPSHOT, {"text": "Signed in as ada@example.invalid"})[0], "1_7")
        self.assertEqual(repro.resolve(SNAPSHOT, {"text": "Sign up"})[0], "1_4", "the document's title is not text")
        for element, reason in (({"role": "button", "name": "Delete account"}, "no element"),
                                ({"role": "textbox", "name": "Emai"}, "no element"),
                                ({"role": "link", "name": "Help"}, "2 elements match"),
                                ({"text": "Help"}, "2 elements match")):
            with self.subTest(element=element):
                uid, _, why = repro.resolve(SNAPSHOT, element)
                self.assertIsNone(uid)
                self.assertIn(reason, why)
        # A name holding a quote cannot widen a match into another node: the match is exact or ambiguous.
        quoted = SNAPSHOT + '\n  uid=1_8 button "Sign up" disabled" x'
        self.assertIsNone(repro.resolve(quoted, {"role": "button", "name": "Sign up"})[0])

    def run_list(self, tool, *steps, deadline=None):
        _, steps, refusals = self.steps(*steps)
        self.assertEqual(refusals, [])
        evidence = Path(r"D:\tmp\never\evidence")
        return repro.run_steps(steps, tool, evidence, "t0k3n", deadline or time.monotonic() + 60)

    def test_an_unresolved_or_ambiguous_element_fails_its_step_and_ends_the_run(self):
        for element, reason in (({"role": "button", "name": "Delete account"}, "no element"),
                                ({"role": "link", "name": "Help"}, "ambiguous")):
            with self.subTest(element=element):
                tool = FakeTool(texts=["Welcome!"])
                results = self.run_list(tool, {"action": "navigate", "url": "http://127.0.0.1:15173/"},
                                        {"action": "click", "element": element},
                                        {"action": "wait_for", "text": "Welcome!"})
                self.assertEqual([r["status"] for r in results], ["passed", "failed", "not run"])
                self.assertIn(reason, results[1]["output"])
                self.assertNotIn("click", [name for name, _ in tool.calls], "nothing was clicked")
                self.assertNotIn("wait_for", [name for name, _ in tool.calls])

    def test_each_element_is_resolved_from_a_snapshot_taken_just_before_its_step(self):
        tool = FakeTool(reveals={"Sign up": "Welcome!"})
        results = self.run_list(tool, {"action": "navigate", "url": "http://127.0.0.1:15173/signup.html"},
                                {"action": "fill", "element": {"role": "textbox", "name": "Password"}, "value": "x"},
                                {"action": "click", "element": {"role": "button", "name": "Sign up"}},
                                {"action": "wait_for", "text": "Welcome!"},
                                {"action": "click", "element": {"role": "button", "name": "Sign up"}})
        self.assertEqual([r["status"] for r in results], ["passed"] * 4 + ["failed"],
                         "the button is gone from the latest snapshot after the click")
        names = [name for name, _ in tool.calls if name != "take_screenshot"]
        self.assertEqual(names, ["navigate_page", "take_snapshot", "fill", "take_snapshot", "click", "wait_for",
                                 "take_snapshot"])
        fill = next(a for n, a in tool.calls if n == "fill")
        self.assertEqual(fill, {"uid": "1_3", "value": "x"})

    def test_screenshots_are_written_under_the_evidence_directory_with_the_scripts_own_names(self):
        tool = FakeTool()
        results = self.run_list(tool, {"action": "navigate", "url": "http://127.0.0.1:15173/"},
                                {"action": "take_screenshot", "full_page": True})
        shots = [a for n, a in tool.calls if n == "take_screenshot"]
        self.assertEqual([a["filePath"] for a in shots], ["D:/tmp/never/evidence/repro-t0k3n-01.png",
                                                          "D:/tmp/never/evidence/repro-t0k3n-02.png"])
        self.assertTrue(shots[1].get("fullPage"))
        self.assertEqual([r["screenshot"] for r in results], ["repro-t0k3n-01.png", "repro-t0k3n-02.png"])

    def test_a_failing_tool_and_the_time_bound_end_the_run(self):
        results = self.run_list(FakeTool(), {"action": "navigate", "url": "http://127.0.0.1:15173/"},
                                {"action": "wait_for", "text": "Welcome!", "timeout_ms": 100},
                                {"action": "take_snapshot"})
        self.assertEqual([r["status"] for r in results], ["passed", "failed", "not run"])
        results = self.run_list(FakeTool(), {"action": "take_snapshot"}, deadline=time.monotonic() - 1)
        self.assertEqual(results[0]["status"], "not run")
        self.assertIn("time bound", results[0]["detail"])

    def test_tool_output_is_redacted_before_it_is_cut(self):
        long_tail = "x" * 10000
        results = self.run_list(lambda name, timeout=60, **a: (False, f"Authorization: Bearer {TOKEN} {long_tail}"),
                                {"action": "list_console_messages"})
        self.assertNotIn(TOKEN, json.dumps(results))
        self.assertIn("[REDACTED]", results[0]["output"])
        self.assertLess(len(results[0]["output"]), repro.OUTPUT_LIMIT + 100)

    def test_the_repro_module_reads_no_environment_variable(self):
        # I13: nothing selects, skips or substitutes a check through the environment (the MCP's environment is built
        # from the run environment as Codex builds it, through guard.mcp_environment).
        import ast
        source = (base.SCRIPTS / "repro.py").read_text(encoding="utf-8")
        reads = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute) and
                 n.attr in ("environ", "getenv", "environb", "putenv")]
        self.assertEqual(reads, [])
        self.assertNotIn("getenv", source)

    def test_evidence_references_outside_the_evidence_directory_are_refused(self):
        refused = ["..\\target.json", "../plan.json", "sub/../../x.png", ".\\x.png", "D:\\tmp\\x.png", "D:/tmp/x.png",
                   "\\\\127.0.0.1\\D$\\tmp\\x.png", "\\\\?\\D:\\x.png", "//server/share/x.png", "/etc/passwd",
                   "D:x.png", "x.png:secret", "x.png::$DATA", "CON", "nul.png", "x.png.", "x.png ", "a//b.png", "", 7,
                   "x\nimage.png"]
        for reference in refused:
            with self.subTest(reference=reference):
                parts, reason = repro.reference_parts(reference)
                self.assertIsNone(parts)
                self.assertTrue(reason)
        for reference, parts in (("shot.png", ["shot.png"]), ("sub\\shot.png", ["sub", "shot.png"]),
                                 ("repro-1a2b3c4d.json", ["repro-1a2b3c4d.json"])):
            self.assertEqual(repro.reference_parts(reference), (parts, None))
        self.assertEqual(repro.kept_name("20260101-000000", 3, ["..evil name?.png"]),
                         "ask-codex-evidence-20260101-000000-03-evil_name_.png")


# --- the CLI on a collected exercise ---

def start_seam(notes, server, registry):
    """In-process seam (I13): the repro's node is replaced by the fake MCP server, in the same job, with the
    definition's arguments; the registration directory is recorded at the moment of the start."""
    return (f"import json, os, sys, winjob\n"
            f"_original = winjob.start_suspended\n"
            f"def _start(job, argv, cwd, env, command_line=None):\n"
            f"    with open(os.path.join({str(notes)!r}, 'start.json'), 'w') as f:\n"
            f"        json.dump({{'job': job.name, 'registered': sorted(os.listdir({str(registry)!r})),"
            f" 'argv': argv, 'cwd': cwd, 'temp': env.get('TEMP')}}, f)\n"
            f"    return _original(job, [sys.executable, {str(server)!r}, {str(notes)!r}, *argv[2:]], cwd, env)\n"
            f"winjob.start_suspended = _start\n")


class ReproCliTest(app_base.AppTestBase):
    def setUp(self):
        super().setUp()
        self.server = base.write(self.root / "fake_mcp.py", FAKE_MCP)
        self.mcp_notes = self.root / "mcp-notes"
        self.mcp_notes.mkdir()
        self.page({"snapshot": SNAPSHOT.replace("Signed in as ada@example.invalid", "Help text"),
                   "reveals": {"Sign up": "Welcome!"}, "token": TOKEN})

    def page(self, value):
        (self.mcp_notes / "page.json").write_text(json.dumps(value), encoding="utf-8")

    def collected(self):
        directory, plan, _ = self.started()
        self.run_completed(directory)
        return directory, plan

    def steps_file(self, *steps, name="steps.json"):
        return base.write(self.requests / name, json.dumps({"claim": "C1", "steps": list(steps)}))

    def repro(self, directory, steps_file):
        return self.call("repro", directory, steps_file,
                         code=start_seam(self.mcp_notes, self.server, Path(directory) / "repro-jobs"))

    def servers(self):
        return [json.loads(p.read_text("utf-8")) for p in self.mcp_notes.glob("server-*.json")]

    def calls_made(self):
        return [json.loads(line) for p in self.mcp_notes.glob("calls-*.jsonl") for line in p.read_text("utf-8").splitlines()]

    def siblings(self, directory, purpose):
        return [e for e in self.record(directory)["entries"] if e.get("purpose") == purpose]

    def record(self, directory):
        return json.loads((Path(directory) / "target.json").read_text("utf-8"))

    def test_a_multi_step_reproduction_runs_in_its_own_session_job_and_proxy_and_leaves_nothing(self):
        directory, plan = self.collected()
        origin = f"http://{self.app[0]}"
        steps = self.steps_file({"action": "navigate", "url": f"{origin}/signup.html"},
                                {"action": "fill", "element": {"role": "textbox", "name": "Password"},
                                 "value": "hunter22"},
                                {"action": "click", "element": {"role": "button", "name": "Sign up"}},
                                {"action": "wait_for", "text": "Welcome!"},
                                {"action": "list_console_messages"})
        result = self.repro(directory, steps)
        self.assertEqual(result["state"], "completed", result)
        self.assertEqual([s["status"] for s in result["steps"]], ["passed"] * 5)
        self.assertTrue(result["browser_ended"])
        # I11 (repro side): token-like strings in the browser's output never reach the result or its file.
        self.assertNotIn(TOKEN, json.dumps(result))
        self.assertIn("[REDACTED]", result["steps"][3]["output"])
        evidence = Path(plan["browser"]["evidence"])
        written = (evidence / result["result_file"]).read_text("utf-8")
        self.assertNotIn(TOKEN, written)
        self.assertEqual(sorted(result["screenshots"]), sorted(p.name for p in evidence.glob("repro-*.png")))
        self.assertEqual(len(result["screenshots"]), 5)
        # Its own session: own job registered before the server started, own siblings, own proxy port, the
        # exercise's definition template (I5, I8, I10).
        start = json.loads((self.mcp_notes / "start.json").read_text("utf-8"))
        self.assertEqual(start["registered"], [start["job"]])
        self.assertRegex(start["job"], r"^ask-codex-repro-[0-9a-f]{32}$")
        self.assertEqual(os.listdir(Path(directory) / "repro-jobs"), [], "the registration goes once the job ended")
        [server] = self.servers()
        temp, cwd, profile = (self.siblings(directory, p) for p in ("repro-temp", "repro-cwd", "repro-profile"))
        self.assertTrue(len(temp) == len(cwd) == len(profile) == 1)
        self.assertEqual(Path(server["cwd"]), Path(cwd[0]["path"]))
        self.assertEqual(Path(server["temp"]), Path(temp[0]["path"]))
        self.assertEqual(server["tmp"], server["temp"])
        args = server["args"]
        exercise_args = plan["browser"]["definition"]["args"]
        self.assertEqual(args[0], f"--userDataDir={Path(profile[0]['path']).as_posix()}")
        self.assertEqual([a for a in args if not a.startswith(("--userDataDir=", "--proxyServer="))],
                         [a for a in exercise_args[1:] if not a.startswith(("--userDataDir=", "--proxyServer="))],
                         "every other argument is the exercise's own definition")
        self.assertTrue(server["proxy_accepts"], "the repro holds its own closed proxy port")
        self.assertNotIn(server["proxy_port"], [plan["browser"]["proxy_port"], *self.ports])
        self.assertEqual(server["client"]["capabilities"], {"elicitation": {}}, "Codex's capabilities, no roots")
        self.assertEqual(json.loads((Path(profile[0]["path"]) / "Default" / "Preferences").read_text()),
                         {"download_restrictions": 3})
        # The fake server and its stand-in Chrome were in the job and are gone; the app still runs for finish.
        for pid in (server["pid"], server["chrome"]):
            created = app_base.created_at(pid)
            self.assertTrue(created is None or not app_base.alive(pid, created), f"PID {pid} still runs")
        self.assertTrue(all(app_base.answers(port) for port in self.ports))
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertEqual(os.listdir(self.targets), [], "the repro siblings go with the target")

    def test_steps_outside_the_boundary_start_nothing_and_run_no_step(self):
        directory, plan = self.collected()
        steps = self.steps_file({"action": "navigate", "url": f"http://{self.app[0]}/signup.html"},
                                {"action": "outside", "step": "Run curl -s http://127.0.0.1:9/collect in a shell"},
                                {"action": "outside", "step": "Remove-Item backend\\seed.json"},
                                {"action": "navigate", "url": "https://attacker.example/report"},
                                {"action": "wait_for", "text": "Welcome!"})
        result = self.repro(directory, steps)
        self.assertEqual(result["state"], "refused", result)
        self.assertEqual([s["status"] for s in result["steps"]], ["not run", "refused", "refused", "refused", "not run"])
        for step in result["steps"][1:4]:
            self.assertTrue(step["detail"].startswith("not confirmed: outside the exercise boundary"))
        self.assertFalse((self.mcp_notes / "start.json").exists(), "no browser was started")
        self.assertEqual(self.servers(), [])
        self.assertEqual([e for e in self.record(directory)["entries"] if str(e.get("purpose", "")).startswith("repro")],
                         [], "no repro directory was created")
        self.assertFalse((Path(directory) / "repro-jobs").exists())
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_an_out_of_origin_navigate_fails_and_an_unresolved_element_fails_its_step(self):
        directory, plan = self.collected()
        for url in ("http://127.0.0.1:18081/", f"http://127.0.0.1:{self.ports[1]}/"):  # localhost:<p1> is the origin
            with self.subTest(url=url):
                result = self.repro(directory, self.steps_file({"action": "navigate", "url": url}, name="o.json"))
                self.assertEqual(result["state"], "refused", result)
                self.assertIn("outside the exercise boundary", result["steps"][0]["detail"])
                (self.requests / "o.json").unlink()
        self.assertEqual(self.servers(), [], "a refused navigate starts no browser")
        result = self.repro(directory, self.steps_file(
            {"action": "navigate", "url": f"http://{self.app[0]}/signup.html"},
            {"action": "click", "element": {"role": "button", "name": "Delete account"}},
            {"action": "wait_for", "text": "Welcome!"}))
        self.assertEqual(result["state"], "step_failed", result)
        self.assertEqual([s["status"] for s in result["steps"]], ["passed", "failed", "not run"])
        self.assertIn('no element button "Delete account"', result["steps"][1]["output"])
        self.assertNotIn("click", [c["name"] for c in self.calls_made()])
        self.assertTrue(result["browser_ended"])
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_reproduction_runs_only_between_collect_and_finish(self):
        directory, plan, _ = self.started()
        steps = self.steps_file({"action": "take_snapshot"})
        early = self.repro(directory, steps)
        self.assertEqual(early["state"], "failed", early)
        self.assertIn("after collect", early["reason"])
        self.run_completed(directory)
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        gone = self.repro(directory, steps)
        self.assertEqual(gone["state"], "failed", gone)
        self.assertEqual(self.servers(), [])

    def test_a_server_of_another_version_is_refused_and_its_job_ended(self):
        directory, plan = self.collected()
        self.page({"snapshot": SNAPSHOT, "version": "1.11.0"})
        result = self.repro(directory, self.steps_file({"action": "take_snapshot"}))
        self.assertEqual(result["state"], "failed", result)
        self.assertIn("not 1.10.1", result["reason"])
        self.assertTrue(result["browser_ended"])
        [server] = self.servers()
        for pid in (server["pid"], server["chrome"]):
            created = app_base.created_at(pid)
            self.assertTrue(created is None or not app_base.alive(pid, created), f"PID {pid} still runs")
        self.assertEqual(os.listdir(Path(directory) / "repro-jobs"), [])
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_usage_needs_the_steps_file(self):
        directory, plan = self.collected()
        result = subprocess.run([sys.executable, str(base.CLI), "repro", str(directory)], capture_output=True,
                                text=True, env=self.env)
        self.assertEqual(result.returncode, 2)
        result = subprocess.run([sys.executable, str(base.CLI), "finish", str(directory), "extra.json"],
                                capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(os.path.exists(directory), "a usage error does nothing")
        self.assertEqual(self.call("finish", directory)["state"], "finished")


# --- evidence-keep (production move) ---

class EvidenceKeepTest(app_base.AppTestBase):
    STAMP = "import time\ntime.strftime = lambda *a: '20260101-000000'\n"

    def setUp(self):
        super().setUp()
        self.kept = self.root / "kept"
        self.kept.mkdir()
        self.directory, self.plan, _ = self.started()
        self.run_completed(self.directory)
        self.evidence = Path(self.plan["browser"]["evidence"])
        base.write(self.evidence / "shot.png", "screenshot bytes")
        base.write(self.evidence / "sub" / "deep.png", "deep bytes")

    def keep(self, files, destination=None, name="keep.json"):
        path = base.write(self.requests / name, json.dumps({"destination": str(destination or self.kept),
                                                             "files": files}))
        try:
            return self.call("evidence-keep", self.directory, path, code=self.STAMP)
        finally:
            path.unlink()

    def sentinel_state(self):
        return base.tree(self.sentinel)

    def test_references_outside_the_evidence_directory_are_refused_and_nothing_outside_is_touched(self):
        before = self.sentinel_state()
        base.junction(self.evidence / "j", self.sentinel)
        os.link(self.sentinel / "keep.txt", self.evidence / "hard.png")
        symlink = None
        try:
            os.symlink(self.sentinel / "keep.txt", self.evidence / "link.png")
            symlink = "link.png"
        except OSError:
            pass  # this user cannot create symbolic links on this host; the junction covers reparse points
        references = ["..\\target.json", "../plan.json", str(self.evidence / "shot.png"),
                      "\\\\127.0.0.1\\" + str(self.evidence / "shot.png").replace(":", "$", 1), "D:shot.png",
                      "shot.png:hidden", "j\\keep.txt", "hard.png", "sub", "missing.png",
                      *([symlink] if symlink else [])]
        result = self.keep(references)
        self.assertEqual(result["state"], "nothing_kept", result)
        self.assertEqual([f["reference"] for f in result["files"]], references)
        self.assertTrue(all(not f["kept"] and f["reason"] for f in result["files"]), result)
        self.assertEqual(os.listdir(self.kept), [])
        self.assertEqual(self.sentinel_state(), before, "the sentinel is unchanged (a junction is never followed)")
        self.assertTrue((self.evidence / "shot.png").is_file() and (self.evidence / "hard.png").is_file())
        os.unlink(self.evidence / "hard.png")
        self.assertEqual(self.call("finish", self.directory)["state"], "finished")
        self.assertEqual(self.sentinel_state(), before)

    def test_chosen_evidence_is_moved_under_its_own_name_and_never_overwrites(self):
        base.write(self.kept / "ask-codex-evidence-20260101-000000-02-deep.png", "the user's own file")
        result = self.keep(["shot.png", "sub/deep.png"])
        self.assertEqual(result["state"], "partly_kept", result)
        moved, kept_back = result["files"]
        self.assertTrue(moved["kept"])
        self.assertEqual(Path(moved["path"]), self.kept / "ask-codex-evidence-20260101-000000-01-shot.png")
        self.assertEqual(Path(moved["path"]).read_text("utf-8"), "screenshot bytes")
        self.assertFalse((self.evidence / "shot.png").exists(), "moved: the source is gone")
        self.assertFalse(kept_back["kept"])
        self.assertIn("nothing is overwritten", kept_back["reason"])
        self.assertEqual((self.kept / "ask-codex-evidence-20260101-000000-02-deep.png").read_text("utf-8"),
                         "the user's own file")
        self.assertTrue((self.evidence / "sub" / "deep.png").is_file(), "a refused move leaves the source")
        finished = self.call("finish", self.directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue((self.kept / "ask-codex-evidence-20260101-000000-01-shot.png").is_file(),
                        "kept evidence outlives the target")

    def test_the_destination_must_be_a_plain_directory_outside_what_finish_removes(self):
        base.junction(self.root / "kept-link", self.kept)
        target = Path(self.plan["summary"]["target"])
        for destination, reason in ((self.root / "missing", "does not exist"), (self.root / "kept-link", "a link"),
                                    (target, "finish removes"), (self.evidence, "finish removes"),
                                    (Path(self.plan["browser"]["temp"]), "finish removes"),
                                    (self.directory, "finish removes"), ("relative\\dir", "absolute path")):
            with self.subTest(destination=str(destination)):
                result = self.keep(["shot.png"], destination=destination)
                self.assertEqual(result["state"], "failed", result)
                self.assertIn(reason, result["reason"])
        self.assertTrue((self.evidence / "shot.png").is_file())
        self.assertEqual(os.listdir(self.kept), [])
        self.assertEqual(self.call("finish", self.directory)["state"], "finished")


if __name__ == "__main__":
    unittest.main()
