"""An exercise runs through the public CLI on a disposable target with the stub Codex (plan C2); offline, never
calls a real Codex service.

Every test works in a fresh directory under the test root (`--test-root`, default D:\\tmp\\ask-codex-tests,
outside any repository), created and removed by the test. Seams are in-process only (plan I13): a bootstrap
patches `browser.local_app_data` (the fake package install and guard cache live under the test directory) in the
CLI process; a fake node.exe is found the way the script finds node, on an absolute PATH entry placed first.
The stub records outside the target (`records` in its scenario), so nothing is written into the copy.
"""
import ast
import ctypes
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
import unittest

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "skills/ask/scripts/consult.py"
SCRIPTS = REPO / "skills/ask/scripts"
SKILL = REPO / "skills/ask"
STUB = REPO / "evals/_harness/stub"
TEST_ROOT = Path(r"D:\tmp\ask-codex-tests")
REPARSE, DIRECTORY = 0x400, 0x10
ENTRY = ("ask-codex", "chrome-devtools-mcp-1.10.1", "node_modules", "chrome-devtools-mcp", "build", "src", "bin",
         "chrome-devtools-mcp.js")

# The spec's tool allowlist, written here literally (never taken from the code under test).
TOOLS = ["navigate_page", "new_page", "list_pages", "select_page", "close_page", "take_screenshot", "take_snapshot",
         "click", "hover", "fill", "fill_form", "type_text", "press_key", "drag", "handle_dialog", "wait_for",
         "resize_page", "emulate", "list_console_messages", "get_console_message", "list_network_requests",
         "get_network_request", "get_css_styles", "lighthouse_audit"]
# `--userDataDir` appears exactly once, naming the run-owned profile (U16); any other form is never present.
NEVER = ["--config", "--browserUrl", "--browser-url", "--wsEndpoint", "--autoConnect", "--isolated",
         "--user-data-dir", "--acceptInsecureCerts", "--allowUnrestrictedPaths", "--slim", "--category",
         "--experimental"]
DISABLED = ('mcp_servers={"blender"={command="ask-codex-disabled",enabled=false},"comfyui"={command="ask-codex-disabled",'
            'enabled=false},"cua_repl"={command="ask-codex-disabled",enabled=false},"node_repl"={command="ask-codex-disabled",'
            'enabled=false},"pencil"={command="ask-codex-disabled",enabled=false}}')
BROWSER_ARGS = ('["<ENTRY>", "--userDataDir=<PROFILE>", "--headless", "--no-javascript-evaluation", "--no-usage-statistics", '
                '"--no-performance-crux", "--redactNetworkHeaders", "--filesystemRoot=<TARGET>/evidence", '
                '"--viewport=1280x720", "--allowedUrlPattern=http://127.0.0.1:15173/*", '
                '"--allowedUrlPattern=http://localhost:18080/*", "--proxyServer=http://127.0.0.1:<PORT>", '
                '"--chromeArg=--proxy-bypass-list=<-loopback>;127.0.0.1:15173;localhost:18080", '
                '"--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]')
BROWSER_ENV = ('{CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY="1",CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS="1",'
               'CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS="1",NODE_OPTIONS="",TEMP="<TEMP>",TMP="<TEMP>"}')
# The exercise command line (the stub's record of the arguments after `codex exec`), per-run values as placeholders.
EXPECTED_ARGV = [
    "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
    "-C", "<TARGET>",
    "-m", "gpt-6-sol",
    "-c", 'model_reasoning_effort="high"',
    "-c", DISABLED,
    "--disable", "apps",
    "-c", "agents.enabled=false",
    "-c", "features.multi_agent_v2.enabled=false",
    "-c", 'approval_policy="never"',
    "-c", 'approvals_reviewer="user"',
    "--ignore-rules",
    "-c", 'mcp_servers.<NONCE>.command="<NODE>"',
    "-c", "mcp_servers.<NONCE>.args=" + BROWSER_ARGS,
    "-c", 'mcp_servers.<NONCE>.cwd="<CWD>"',
    "-c", "mcp_servers.<NONCE>.env=" + BROWSER_ENV,
    "-c", "mcp_servers.<NONCE>.startup_timeout_sec=90",
    "-c", "mcp_servers.<NONCE>.enabled_tools=" + json.dumps(TOOLS),
    *[item for tool in TOOLS for item in ("-c", f'mcp_servers.<NONCE>.tools.{tool}.approval_mode="approve"')],
    "-c", 'mcp_servers.<NONCE>.default_tools_approval_mode="prompt"',
    "--output-schema", "<SKILL_DIR>/ui-exercise.schema.json",
    "-o", "<RUN_DIR>/0/last-message.json",
    "-",
]

UI_REPLY = {
    "claims": [
        {"category": "bug", "statement": "Saving an empty name shows a success message.",
         "steps": ["Open http://127.0.0.1:15173/", "Click the button named Save"], "expected": "A validation error",
         "actual": "Saved: (empty)", "viewport": "1280x720", "evidence": ["save-empty.png"], "confidence": "high",
         "in_scope": True},
        {"category": "ux", "statement": "The Save button gives no feedback while saving.", "steps": [],
         "expected": None, "actual": None, "viewport": None, "evidence": [], "confidence": "low", "in_scope": True},
    ],
    "out_of_scope": ["The footer links point to an external site."],
    "coverage": {"pages": ["/"], "flows": ["save a name"], "viewports": ["1280x720", "390x844"]},
}

BOOTSTRAP = r"""
import json, runpy, shutil, sys
from pathlib import Path
script = sys.argv.pop(1)
seams = json.loads(sys.argv.pop(1))
sys.path.insert(0, str(Path(script).parent))
import browser
browser.local_app_data = lambda: Path(seams["local_app_data"])
# C3 seams (in-process, plan I13): the fake package install is not the pinned one, and these C2 tests do not run
# the browser guard; exercise_guard_test.py covers both.
import guard, install
install.verify_installed = lambda: "test-manifest"
guard.require_current_pass = lambda cli, directory, plan, state_dir=None: {"source": "test"}
if seams.get("code"):
    exec(seams["code"], {"__name__": "seam"})
if seams.get("platform"):
    sys.platform = seams["platform"]
sys.argv[0] = script
runpy.run_path(script, run_name="__main__")
"""

# A fake app (plan C4): listens on each host:port given and accepts and closes every connection.
FAKE_APP = r"""
import socket, sys, threading, time
def serve(sock):
    while True:
        try:
            connection, _ = sock.accept()
        except OSError:
            return
        connection.close()
for spec in sys.argv[1:]:
    host, port = spec.rsplit(":", 1)
    sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
    sock.bind((host, int(port)))
    sock.listen(16)
    threading.Thread(target=serve, args=(sock,), daemon=True).start()
print("listening", flush=True)
while True:
    time.sleep(3600)
"""

SPAWN_FAILURE = """
import subprocess
original = subprocess.Popen
def spawn(*args, **kwargs):
    if kwargs.get('stdin') is not None:
        raise OSError('injected spawn failure')
    return original(*args, **kwargs)
subprocess.Popen = spawn
"""


def extended(path):
    path = str(path)
    return path if path.startswith("\\\\?\\") else "\\\\?\\" + path


def write(path, text="x"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def junction(link, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)


def tree(path):
    """Relative path -> (kind, content) for a directory tree; links are reported, never followed."""
    found = {}
    for entry in os.scandir(extended(path)):
        status = entry.stat(follow_symlinks=False)
        if status.st_file_attributes & REPARSE:
            found[entry.name] = ("link", None)
        elif status.st_file_attributes & DIRECTORY:
            found[entry.name] = ("dir", None)
            found.update({f"{entry.name}/{k}": v for k, v in tree(entry.path).items()})
        else:
            found[entry.name] = ("file", Path(entry.path).read_bytes())
    return found


def scrub(path):
    """Test cleanup only (after every assertion): links are unlinked, never followed."""
    path = extended(path)
    if not os.path.lexists(path):
        return
    status = os.lstat(path)
    if status.st_file_attributes & REPARSE:
        (os.rmdir if status.st_file_attributes & DIRECTORY else os.unlink)(path)
    elif status.st_file_attributes & DIRECTORY:
        for entry in os.scandir(path):
            scrub(entry.path)
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        os.rmdir(path)
    else:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        os.unlink(path)


def related(a, b):
    x = [p for p in os.path.normpath(str(a)).casefold().split("\\") if p]
    y = [p for p in os.path.normpath(str(b)).casefold().split("\\") if p]
    n = min(len(x), len(y))
    return x[:n] == y[:n]


def tearDownModule():
    try:
        TEST_ROOT.rmdir()  # only when every test removed its own directory
    except OSError:
        pass


@unittest.skipUnless(sys.platform == "win32", "the exercise platform layer is Windows only (plan I13)")
class ExerciseRunTest(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="e-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.project, self.targets = self.root / "project", self.root / "targets"
        self.base, self.records, self.requests = self.root / "base", self.root / "records", self.root / "requests"
        self.sentinel, self.local, self.home = self.root / "sentinel", self.root / "localappdata", self.root / "home"
        for directory in (self.project, self.targets, self.base, self.requests, self.sentinel, self.home):
            directory.mkdir()
        write(self.sentinel / "keep.txt", "sentinel content")
        write(self.project / "index.html", "<h1>app</h1>")
        write(self.project / "evidence/old.png", "the project's own evidence entry")
        write(self.project / "fakeapp.py", FAKE_APP)
        self.entry = write(self.local.joinpath(*ENTRY), "// fake entry script, never run")
        self.node = write(self.root / "node" / "node.exe", "fake node, never run")
        self.scenario({"exec": {"reply": UI_REPLY}})
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CODEX_HOME": str(self.home / ".codex"),
                    "PATH": os.pathsep.join([str(self.node.parent), str(STUB), os.environ["PATH"]])}
        self.request = {"interaction": "exercise", "kind": "ui", "project": str(self.project),
                        "prompt": "Exercise the app and report what you find.",
                        "models": [{"model": "gpt-6-sol", "effort": "high"}],
                        "target_root": {"path": str(self.targets), "confirmed_by_user": True},
                        "app": ["127.0.0.1:15173", "localhost:18080"], "headed": False, "scope": "the save form",
                        "target_name": "exercise-target",
                        "commands": {"start": [{"argv": [sys.executable, "fakeapp.py", "127.0.0.1:15173",
                                                         "127.0.0.1:18080"]}]}}

    # --- helpers ---

    def scenario(self, value, directory=None):
        write((directory or self.project) / ".stub/scenario.json", json.dumps({"records": str(self.records), **value}))

    def seams(self, **extra):
        return json.dumps({"local_app_data": str(self.local), **extra})

    def call(self, *args, timeout=120, cwd=None, **extra):
        result = subprocess.run([sys.executable, "-c", BOOTSTRAP, str(CLI), self.seams(**extra), *map(str, args)],
                                env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                                cwd=cwd)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def background(self, *args):
        return subprocess.Popen([sys.executable, "-c", BOOTSTRAP, str(CLI), self.seams(), *map(str, args)],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def prepare(self, request=None, **extra):
        path = self.requests / "request.json"
        path.write_text(json.dumps(self.request if request is None else request), encoding="utf-8")
        return self.call("prepare", path, "--base", self.base, **extra)

    def prepared(self):
        """Prepared, with the app started under its supervisor (C4: Codex runs only after app-start)."""
        ready = self.prepare()
        self.assertEqual(ready["state"], "prepared", ready)
        started = self.call("app-start", ready["directory"])
        self.assertEqual(started["state"], "app_started", started)
        return ready, Path(ready["directory"]), json.loads((Path(ready["directory"]) / "plan.json").read_text("utf-8"))

    def runs(self):
        parent = self.base / "ask-codex"
        return sorted(parent.iterdir()) if parent.exists() else []

    def record(self, directory):
        return json.loads((Path(directory) / "target.json").read_text(encoding="utf-8"))

    def exec_calls(self):
        return sorted((self.records / "exec-calls").glob("*.json")) if (self.records / "exec-calls").exists() else []

    def violations(self):
        path = self.records / "violations.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def assert_all_removed(self, directory):
        self.assertEqual(os.listdir(self.targets), [], "target and every sibling directory removed")
        self.assertFalse(os.path.lexists(directory), "run directory removed")

    def expected_argv(self, plan, directory):
        b = plan["browser"]
        values = {"<TARGET>": Path(plan["summary"]["target"]).as_posix(), "<NONCE>": plan["summary"]["browser_server"],
                  "<NODE>": self.node.as_posix(), "<ENTRY>": self.entry.as_posix(),
                  "<CWD>": Path(b["cwd"]).as_posix(), "<TEMP>": Path(b["temp"]).as_posix(),
                  "<PROFILE>": Path(b["profile"]).as_posix(),
                  "<PORT>": str(b["proxy_port"]), "<RUN_DIR>": Path(directory).as_posix(),
                  "<SKILL_DIR>": SKILL.as_posix()}
        expected = []
        for arg in EXPECTED_ARGV:
            for placeholder, value in values.items():
                arg = arg.replace(placeholder, value)
            expected.append(arg)
        return expected

    def recorded_argv(self):
        return json.loads((self.records / "exec-argv.json").read_text(encoding="utf-8"))

    @staticmethod
    def overrides_of(argv):
        return [argv[i + 1] for i, a in enumerate(argv) if a == "-c"]

    @staticmethod
    def toml_value(argv, key):
        [value] = [v.split("=", 1)[1] for v in ExerciseRunTest.overrides_of(argv) if v.split("=", 1)[0] == key]
        return tomllib.loads("v = " + value)["v"]

    def collect_completed(self, directory):
        self.assertEqual(self.call("run", directory)["state"], "finished")
        self.assertEqual(self.call("wait", directory, "--seconds", "5")["state"], "finished")
        collected = self.call("collect", directory)
        self.assertEqual(collected["state"], "collected", collected)
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        return collected

    # --- the command line (I4, I5) ---

    def test_exercise_command_line_is_the_literal_baseline_with_the_browser_server(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        argv = self.recorded_argv()
        self.assertEqual(argv, self.expected_argv(plan, directory))
        target = Path(plan["summary"]["target"])
        self.assertEqual(argv[argv.index("-C") + 1], target.as_posix())
        self.assertFalse(related(target, self.project), "-C is never the project")
        self.assertEqual(str(target).casefold(), str(self.targets / "exercise-target").casefold())
        [call] = [json.loads(path.read_text(encoding="utf-8")) for path in self.exec_calls()]
        self.assertEqual(Path(call["cwd"]).resolve(), target.resolve(), "the Codex process runs in the target")
        self.assertEqual(self.violations(), "")
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_approval_keys_are_exactly_the_literal_tool_list_and_never_stored(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        argv = self.recorded_argv()
        name = plan["summary"]["browser_server"]
        values = self.overrides_of(argv)
        per_tool = [v for v in values if ".tools." in v]
        self.assertEqual(len(per_tool), 24)
        self.assertEqual(set(per_tool), {f'mcp_servers.{name}.tools.{tool}.approval_mode="approve"' for tool in TOOLS})
        self.assertEqual(values.count(f'mcp_servers.{name}.default_tools_approval_mode="prompt"'), 1)
        approval = [v for v in values if "approv" in v.split("=", 1)[0]]
        self.assertEqual(sorted(approval), sorted([*per_tool, f'mcp_servers.{name}.default_tools_approval_mode="prompt"',
                                                   'approval_policy="never"', 'approvals_reviewer="user"']))
        self.assertEqual([v for v in values if "approv" in v and v not in approval], [])
        tools = [v for v in values if "tools" in v.split("=", 1)[0]]
        self.assertEqual(sorted(tools), sorted([*per_tool, f'mcp_servers.{name}.default_tools_approval_mode="prompt"',
                                                f"mcp_servers.{name}.enabled_tools=" + json.dumps(TOOLS)]))
        self.assertEqual(self.toml_value(argv, f"mcp_servers.{name}.enabled_tools"), TOOLS)
        for absent in ("upload_file", "take_heapsnapshot", "performance_", "evaluate_script"):
            self.assertFalse(any(absent in v for v in values), absent)
        # Never in overrides, summary or plan.json (A5).
        text = (directory / "plan.json").read_text(encoding="utf-8")
        for key in ("approv", "tools.", "default_tools"):
            self.assertNotIn(key, text)
            self.assertNotIn(key, json.dumps(ready["summary"]))
            self.assertFalse(any(key in v for v in plan["overrides"]), plan["overrides"])
        for key in ("read-only", "ephemeral", "agents.enabled", "multi_agent", "ignore-rules", "approval_policy",
                    "apps"):
            self.assertNotIn(key, json.dumps(ready["summary"]))
            self.assertFalse(any(key in v for v in plan["overrides"]))
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_browser_definition_arguments_env_and_launch_are_literal(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        argv = self.recorded_argv()
        name = plan["summary"]["browser_server"]
        self.assertRegex(name, r"^cdt_[0-9a-f]{16}$")
        args = self.toml_value(argv, f"mcp_servers.{name}.args")
        target = Path(plan["summary"]["target"]).as_posix()
        profile = Path(plan["browser"]["profile"]).as_posix()
        self.assertEqual(args, [self.entry.as_posix(), f"--userDataDir={profile}", "--headless",
                                "--no-javascript-evaluation",
                                "--no-usage-statistics", "--no-performance-crux", "--redactNetworkHeaders",
                                f"--filesystemRoot={target}/evidence", "--viewport=1280x720",
                                "--allowedUrlPattern=http://127.0.0.1:15173/*",
                                "--allowedUrlPattern=http://localhost:18080/*",
                                f"--proxyServer=http://127.0.0.1:{plan['browser']['proxy_port']}",
                                "--chromeArg=--proxy-bypass-list=<-loopback>;127.0.0.1:15173;localhost:18080",
                                "--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp"])
        for flag in NEVER:
            self.assertFalse(any(arg.startswith(flag) for arg in args), flag)
        # U16: exactly one user data directory, the run-owned profile; never --isolated.
        self.assertEqual([arg for arg in args if arg.lower().startswith(("--userdatadir", "--user-data-dir"))],
                         [f"--userDataDir={profile}"])
        # node is launched directly (no cmd, no npx), so `<` and `>` reach Chrome literally (P7).
        command = self.toml_value(argv, f"mcp_servers.{name}.command")
        self.assertEqual(command, self.node.as_posix())
        self.assertEqual(Path(command).name, "node.exe")
        self.assertFalse(any(arg.lower() in ("/c", "/d", "/s") or "npx" in arg.lower() for arg in args))
        self.assertIn("--chromeArg=--proxy-bypass-list=<-loopback>;127.0.0.1:15173;localhost:18080", args)
        temp = Path(plan["browser"]["temp"]).as_posix()
        self.assertEqual(self.toml_value(argv, f"mcp_servers.{name}.env"),
                         {"CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY": "1", "CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1",
                          "CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS": "1", "NODE_OPTIONS": "", "TEMP": temp, "TMP": temp})
        self.assertEqual(self.toml_value(argv, f"mcp_servers.{name}.startup_timeout_sec"), 90)
        self.assertEqual(self.toml_value(argv, f"mcp_servers.{name}.cwd"), Path(plan["browser"]["cwd"]).as_posix())
        # The guard saw the same definition through `codex mcp get` (I6), from the target.
        gets = [json.loads(line) for line in (self.records / "mcp-get.log").read_text("utf-8").splitlines()]
        self.assertEqual(len(gets), 2)  # prepare and run
        browser_values = [v for v in self.overrides_of(argv) if v.startswith(f"mcp_servers.{name}.")]
        self.assertEqual(len(browser_values), 31)  # 6 definition fields, 24 tools, the default approval mode
        for get in gets:
            self.assertEqual(get["name"], name)
            self.assertEqual(Path(get["cwd"]).resolve(), Path(plan["summary"]["target"]).resolve())
            # The guard checked exactly the values Codex received (no launcher hop changed them).
            self.assertEqual([v for v in self.overrides_of(get["argv"]) if v.startswith(f"mcp_servers.{name}.")],
                             browser_values)
        lists = [json.loads(line) for line in (self.records / "mcp-list.log").read_text("utf-8").splitlines()]
        self.assertEqual(len(lists), 4)  # plain and guarded listing, at prepare and at run
        for listing in lists:
            self.assertEqual(Path(listing["cwd"]).resolve(), Path(plan["summary"]["target"]).resolve())
        # The owned proxy port is recorded.
        self.assertIsInstance(plan["browser"]["proxy_port"], int)
        self.assertEqual(plan["browser"]["definition"]["args"], args)
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_other_servers_are_disabled_whatever_the_user_policy_and_allowlist(self):
        (self.home / ".claude").mkdir()
        (self.home / ".claude/ask-codex.json").write_text('{"mcp_policy":"minimal-deny","mcp_allow":["comfyui"]}')
        (self.project / ".claude").mkdir()
        (self.project / ".claude/ask-codex.local.json").write_text('{"mcp_allow":["blender","pencil"]}')
        ready, directory, plan = self.prepared()
        self.assertEqual(ready["summary"]["allowed_servers"], [])
        self.assertEqual(ready["summary"]["disabled_servers"], ["blender", "comfyui", "cua_repl", "node_repl", "pencil"])
        self.assertEqual(plan["overrides"], ["-c", DISABLED])
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    # --- prepared summary and validation ---

    def test_prepared_summary_names_interaction_root_ports_browser_mode_and_model(self):
        self.request["headed"] = True
        ready, directory, plan = self.prepared()
        summary = ready["summary"]
        self.assertEqual(summary["interaction"], "exercise")
        self.assertEqual(summary["kind"], "ui")
        self.assertEqual(summary["target_root"].casefold(), str(self.targets).casefold())
        self.assertEqual(summary["app"], ["127.0.0.1:15173", "localhost:18080"])
        self.assertEqual(summary["browser"], "headed")
        self.assertEqual(summary["models"], [{"model": "gpt-6-sol", "effort": "high"}])
        self.assertNotIn("--headless", plan["browser"]["definition"]["args"])
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assertEqual(self.runs(), [])

    def test_validation_refuses_before_anything_is_written_or_codex_runs(self):
        (self.targets / "taken").mkdir()
        base = dict(self.request)
        cases = [
            ("two models", {"models": [{"model": "gpt-6-sol", "effort": "high"}, {"model": "gpt-6-astra", "effort": "medium"}]},
             "exactly one model"),
            ("no model", {"models": []}, "exactly one model"),
            ("existing target", {"target_name": "taken"}, "already exists"),
            ("unconfirmed root", {"target_root": {"path": str(self.targets), "confirmed_by_user": False}}, "confirmed"),
            ("root not confirmed at all", {"target_root": {"path": str(self.targets)}}, "confirmed"),
            ("no ports", {"app": []}, "at least one app"),
            ("not loopback", {"app": ["192.168.1.5:8080"]}, "not loopback"),
            ("wildcard", {"app": ["0.0.0.0:8080"]}, "not loopback"),
            ("other loopback spelling", {"app": ["127.0.0.2:8080"]}, "not loopback"),
            ("external host", {"app": ["example.com:80"]}, "not loopback"),
            ("port zero", {"app": ["127.0.0.1:0"]}, "invalid app port"),
            ("port too high", {"app": ["127.0.0.1:65536"]}, "invalid app port"),
            ("port not a number", {"app": ["127.0.0.1:http"]}, "invalid app port"),
            ("leading zero", {"app": ["127.0.0.1:080"]}, "invalid app port"),
            ("no port", {"app": ["127.0.0.1"]}, "invalid app host:port"),
            ("duplicate", {"app": ["127.0.0.1:15173", "127.0.0.1:15173"]}, "twice"),
            ("headed not a flag", {"headed": "yes"}, "headed"),
            ("unknown field", {"approval_mode": "approve"}, "unknown exercise request fields"),
            ("other kind", {"kind": "api"}, "kind"),
            ("ultra without choice", {"models": [{"model": "gpt-6-sol", "effort": "ultra"}]}, "ultra"),
        ]
        before = tree(self.targets)
        for label, change, expected in cases:
            with self.subTest(case=label):
                refused = self.prepare({**base, **change})
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn(expected.lower(), refused["reason"].lower())
                self.assertEqual(self.runs(), [])
                self.assertEqual(tree(self.targets), before)
        self.assertFalse((self.records / "mcp-list.log").exists(), "no Codex command ran")
        self.assertEqual(self.exec_calls(), [])

    def test_consultation_requests_cannot_select_the_ui_reply_schema(self):
        request = {"project": str(self.project), "prompt": "q", "models": [{"model": "gpt-6-sol", "effort": "high"}],
                   "confirmations": {}, "reply_schema": "ui-exercise"}
        self.assertEqual(self.prepare(request)["state"], "failed")

    # --- MCP guard (I6) ---

    def test_mcp_guard_refusals_remove_the_target_before_codex(self):
        cases = [
            ("second enabled server", {"exercise_extra_enabled": "intruder"}, "only enabled mcp server"),
            ("changed command", {"mcp_get_patch": {"transport": {"command": "C:/other/node.exe"}}}, "transport.command"),
            ("changed argument", {"mcp_get_patch": {"transport": {"args": ["x.js"]}}}, "transport.args"),
            ("changed env", {"mcp_get_patch": {"transport": {"env": {"NODE_OPTIONS": "--require x"}}}}, "transport.env"),
            ("changed cwd", {"mcp_get_patch": {"transport": {"cwd": "D:/elsewhere"}}}, "transport.cwd"),
            ("non-empty env_vars", {"mcp_get_patch": {"transport": {"env_vars": ["GITHUB_TOKEN"]}}}, "transport.env_vars"),
            ("extra enabled tool", {"mcp_get_patch": {"enabled_tools": [*TOOLS, "evaluate_script"]}}, "enabled_tools"),
            ("missing enabled tool", {"mcp_get_patch": {"enabled_tools": TOOLS[:-1]}}, "enabled_tools"),
            ("non-empty disabled_tools", {"mcp_get_patch": {"disabled_tools": ["click"]}}, "disabled_tools"),
            ("changed startup timeout", {"mcp_get_patch": {"startup_timeout_sec": 10.0}}, "startup_timeout_sec"),
            ("server disabled", {"mcp_get_patch": {"enabled": False}}, "enabled"),
            ("default approval printed otherwise", {"mcp_get_prints_default_approval": "approve"},
             "default_tools_approval_mode"),
        ]
        for label, scenario, expected in cases:
            with self.subTest(case=label):
                self.scenario({"exec": {"reply": UI_REPLY}, **scenario})
                refused = self.prepare()
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn(expected, refused["reason"].lower() if expected.islower() else refused["reason"])
                self.assertIn("exercise not started", refused["reason"])
                self.assertTrue(refused["target_removed"], refused)
                self.assertEqual(os.listdir(self.targets), [])
                self.assertEqual(os.listdir(self.base / "ask-codex"), [])
        self.assertEqual(self.exec_calls(), [])

    def test_mcp_guard_accepts_a_printed_default_approval_of_prompt(self):
        self.scenario({"exec": {"reply": UI_REPLY}, "mcp_get_prints_default_approval": True})
        ready, directory, plan = self.prepared()
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_mcp_guard_at_run_aborts_before_codex_and_removes_the_target_at_once(self):
        ready, directory, plan = self.prepared()
        self.scenario({"exec": {"reply": UI_REPLY}, "exercise_extra_enabled": "intruder"},
                      directory=Path(plan["summary"]["target"]))
        refused = self.call("run", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("only enabled MCP server", refused["reason"])
        self.assertIn("the target was removed", refused["reason"])
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.exec_calls(), [])
        collected = self.call("collect", directory)
        self.assertEqual(collected["state"], "failed", collected)
        self.assert_all_removed(directory)

    # --- run-owned directories (I5 placement, R4-1) ---

    def test_mcp_temp_is_a_fresh_recorded_sibling_apart_from_every_script_read_path(self):
        ready, directory, plan = self.prepared()
        b, target = plan["browser"], Path(plan["summary"]["target"])
        temp, cwd, profile = Path(b["temp"]), Path(b["cwd"]), Path(b["profile"])
        for owned in (temp, cwd, profile):
            self.assertEqual(str(owned.parent).casefold(), str(target.parent).casefold(), "sibling of the target")
            self.assertFalse(os.lstat(owned).st_file_attributes & REPARSE)
        for owned in (temp, cwd):
            self.assertEqual(os.listdir(owned), [], "fresh and empty")
        # U16: the profile holds exactly the seed that blocks downloads, written before any launch.
        self.assertEqual(sorted(tree(profile)), ["Default", "Default/Preferences"])
        self.assertEqual((profile / "Default" / "Preferences").read_bytes(), b'{"download_restrictions": 3}')
        protected = [directory, directory / "target.json", directory / "plan.json", directory / "0" / "stop-request",
                     directory / "0" / "stop-status.json", directory / "0" / "last-message.json",
                     directory / "0" / "events.jsonl", self.local / "ask-codex" / "guard-cache",
                     self.local / "ask-codex", target / "evidence", target]
        for path in protected:
            self.assertFalse(related(temp, path), path)
            self.assertFalse(related(cwd, path), path)
            self.assertFalse(related(profile, path), path)
        self.assertFalse(related(temp, cwd))
        self.assertFalse(related(profile, temp))
        self.assertFalse(related(profile, cwd))
        entries = {e["path"]: e for e in self.record(directory)["entries"]}
        for owned, purpose in ((temp, "mcp-temp"), (cwd, "mcp-cwd"), (profile, "mcp-profile")):
            entry = entries[str(owned)]
            self.assertEqual((entry["kind"], entry["purpose"], entry["state"]), ("temp", purpose, "created"))
            self.assertTrue(entry["volume_serial"] and entry["file_id"])
        # The evidence directory is new and empty: the project's own `evidence` entry is never copied.
        self.assertEqual(os.listdir(target / "evidence"), [])
        self.assertEqual(Path(b["evidence"]), target / "evidence")
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assertFalse(os.path.lexists(temp))
        self.assertFalse(os.path.lexists(cwd))
        self.assertFalse(os.path.lexists(profile))

    def test_profile_swapped_for_a_junction_is_neither_used_nor_followed_on_removal(self):
        # U16: the profile directory follows the run-owned TEMP rule (recorded identity, never followed).
        ready, directory, plan = self.prepared()
        profile = Path(plan["browser"]["profile"])
        os.rename(profile, str(profile) + ".moved")
        junction(profile, self.sentinel)
        sentinel = tree(self.sentinel)
        refused = self.call("run", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("no longer matches the target record", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        self.assertEqual(tree(self.sentinel), sentinel, "the junction was not followed")
        self.assertTrue(os.lstat(profile).st_file_attributes & REPARSE, "the swapped entry is kept and reported")
        self.assertFalse(os.path.lexists(plan["summary"]["target"]), "the target itself was removed")
        self.assertEqual([e["path"] for e in self.record(directory)["entries"]], [str(profile)])
        os.rmdir(profile)  # the test's own junction, unlinked
        scrub(str(profile) + ".moved")

    def test_profile_swapped_after_collect_is_not_followed_by_finish(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        profile = Path(plan["browser"]["profile"])
        os.rename(profile, str(profile) + ".moved")
        junction(profile, self.sentinel)
        sentinel = tree(self.sentinel)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "failed", finished)
        self.assertEqual(finished["retained_location"], str(profile))
        self.assertIn("link or junction", finished["reason"])
        self.assertEqual(tree(self.sentinel), sentinel)
        self.assertTrue(directory.exists())
        os.rmdir(profile)
        scrub(str(profile) + ".moved")

    def test_profile_not_holding_exactly_the_seed_refuses_the_run(self):
        # U16: before launch the profile must hold exactly Default/Preferences = {"download_restrictions": 3}.
        cases = [("preferences changed", lambda p: (p / "Default" / "Preferences").write_bytes(b"{}")),
                 ("another file", lambda p: write(p / "Local State", "{}")),
                 ("preferences removed", lambda p: (p / "Default" / "Preferences").unlink())]
        for label, change in cases:
            with self.subTest(case=label):
                ready, directory, plan = self.prepared()
                change(Path(plan["browser"]["profile"]))
                refused = self.call("run", directory)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn("browser profile", refused["reason"])
                self.assertIn("the target was removed", refused["reason"])
                self.assertEqual(self.exec_calls(), [])
                self.assertEqual(self.call("collect", directory)["state"], "failed")
                self.assert_all_removed(directory)

    def test_a_definition_with_isolated_or_another_user_data_dir_is_refused(self):
        for label, replace in (("--isolated", lambda a, profile: "--isolated"),
                               ("another --userDataDir", lambda a, profile: "--userDataDir=D:/elsewhere")):
            with self.subTest(case=label):
                ready, directory, plan = self.prepared()
                definition = plan["browser"]["definition"]
                definition["args"] = [replace(a, plan["browser"]["profile"]) if a.startswith("--userDataDir=") else a
                                      for a in definition["args"]]
                (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                refused = self.call("run", directory)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn("definition changed", refused["reason"])
                self.assertEqual(self.exec_calls(), [])

    def test_mcp_temp_swapped_for_a_junction_is_neither_used_nor_followed_on_removal(self):
        ready, directory, plan = self.prepared()
        temp = Path(plan["browser"]["temp"])
        os.rename(temp, str(temp) + ".moved")
        junction(temp, self.sentinel)
        sentinel = tree(self.sentinel)
        refused = self.call("run", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("no longer matches the target record", refused["reason"])
        self.assertIn("could not be removed", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        self.assertEqual(tree(self.sentinel), sentinel, "the junction was not followed")
        self.assertTrue(os.lstat(temp).st_file_attributes & REPARSE, "the swapped entry is kept and reported")
        self.assertFalse(os.path.lexists(plan["summary"]["target"]), "the target itself was removed")
        self.assertEqual([e["path"] for e in self.record(directory)["entries"]], [str(temp)])
        collected = self.call("collect", directory)
        self.assertFalse(collected["target_removed"], collected)
        self.assertEqual(collected["retained_location"], str(temp))
        self.assertTrue(directory.exists(), "the record stays while an entry is kept")
        os.rmdir(temp)  # the test's own junction, unlinked
        os.rename(str(temp) + ".moved", temp)

    def test_target_swapped_for_a_junction_during_prepare_gets_no_evidence_directory_and_is_not_followed(self):
        swap = f"""
import json, os, subprocess, target
from pathlib import Path
original = target.create_sibling
def create_sibling(run_directory, purpose):
    path = original(run_directory, purpose)
    if purpose == "mcp-cwd":
        swapped = json.loads((Path(run_directory) / "target.json").read_text("utf-8"))["entries"][0]["path"]
        os.rename(swapped, swapped + ".moved")
        subprocess.run(["cmd", "/c", "mklink", "/J", swapped, {str(self.sentinel)!r}], check=True, capture_output=True)
    return path
target.create_sibling = create_sibling
"""
        sentinel = tree(self.sentinel)
        refused = self.prepare(code=swap)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("no longer matches the record", refused["reason"])
        self.assertFalse(refused["target_removed"], refused)
        self.assertEqual(tree(self.sentinel), sentinel, "no evidence directory or anything else written through it")
        swapped = self.targets / "exercise-target"
        self.assertTrue(os.lstat(swapped).st_file_attributes & REPARSE, "the junction is kept, not followed")
        self.assertEqual(self.exec_calls(), [])
        os.rmdir(swapped)  # the test's own junction, unlinked
        os.rename(str(swapped) + ".moved", swapped)

    # --- interrupted creation, launching run, top-level evidence, node lookup (code review 1: N1, N2, d, N4) ---

    def raw_prepare(self, code):
        path = self.requests / "request.json"
        path.write_text(json.dumps(self.request), encoding="utf-8")
        return subprocess.run([sys.executable, "-c", BOOTSTRAP, str(CLI), self.seams(code=code), "prepare", str(path),
                               "--base", str(self.base)], env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=120)

    def test_interrupted_copy_removes_the_created_target_through_its_record(self):
        interrupt = "import target\ndef run(*args, **kwargs):\n    raise KeyboardInterrupt()\ntarget._Copy.run = run\n"
        result = self.raw_prepare(interrupt)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("KeyboardInterrupt", result.stderr)
        self.assertEqual(os.listdir(self.targets), [], "the created target was removed through its record")
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.exec_calls(), [])

    def test_interruption_before_the_identity_is_recorded_keeps_record_and_target(self):
        interrupt = """
import target
original, calls = target._write_record, []
def write(directory, record):
    calls.append(1)
    if len(calls) == 2:  # the write that records the created target's identity
        raise KeyboardInterrupt()
    return original(directory, record)
target._write_record = write
"""
        result = self.raw_prepare(interrupt)
        self.assertNotEqual(result.returncode, 0)
        [directory] = self.runs()
        entries = self.record(directory)["entries"]
        self.assertEqual([(e["path"].casefold(), e["state"]) for e in entries],
                         [(str(self.targets / "exercise-target").casefold(), "pending")])
        self.assertTrue((self.targets / "exercise-target").exists(), "kept together with its record, never orphaned")

    def test_run_interrupted_before_codex_leaves_a_failure_receipt_so_finish_proceeds(self):
        ready, directory, plan = self.prepared()
        interrupt = "import exercise\ndef before_launch(*args, **kwargs):\n    raise KeyboardInterrupt()\n" \
                    "exercise.before_launch = before_launch\n"
        result = subprocess.run([sys.executable, "-c", BOOTSTRAP, str(CLI), self.seams(code=interrupt), "run",
                                 str(directory)], env=self.env, capture_output=True, text=True, encoding="utf-8",
                                timeout=120)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("KeyboardInterrupt", result.stderr)
        self.assertTrue((directory / "started").exists())
        receipt = json.loads((directory / "execution-error.json").read_text(encoding="utf-8"))
        self.assertIn("interrupted before Codex started", receipt["reason"])
        self.assertEqual(self.exec_calls(), [])
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assert_all_removed(directory)

    def test_finish_and_cleanup_refuse_while_run_is_launching(self):
        ready, directory, plan = self.prepared()
        (directory / "started").touch()  # run's checks have begun; no clock.json and no execution-error.json yet
        for action in ("finish", "cleanup"):
            with self.subTest(action=action):
                refused = self.call(action, directory)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn("run is starting", refused["reason"])
                self.assertTrue(Path(plan["summary"]["target"]).exists())
                self.assertTrue((directory / "plan.json").exists())
        (directory / "started").unlink()
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assert_all_removed(directory)

    def test_only_the_top_level_evidence_entry_is_replaced(self):
        write(self.project / "src/evidence/keep.txt", "nested, copied")
        write(self.project / "src/evidence/.env.local", "NESTED=1")
        self.request["env_files"] = ["src/evidence/.env.local"]
        ready, directory, plan = self.prepared()
        target = Path(plan["summary"]["target"])
        self.assertEqual(os.listdir(target / "evidence"), [], "the project's top-level evidence entry is replaced")
        self.assertEqual((target / "src/evidence/keep.txt").read_text(encoding="utf-8"), "nested, copied")
        self.assertEqual((target / "src/evidence/.env.local").read_text(encoding="utf-8"), "NESTED=1")
        self.assertTrue(ready["copy"]["top_level_evidence_replaced"])
        self.assertFalse(any("evidence" in name for name in ready["copy"]["excluded"]), ready["copy"]["excluded"])
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        for named in (["evidence/.env"], ["Evidence\\sub\\.env.test"]):
            with self.subTest(env_files=named):
                self.request["env_files"] = named
                refused = self.prepare()
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn("top-level evidence", refused["reason"])
                self.assertEqual(self.runs(), [])

    def test_node_is_found_on_absolute_path_entries_only(self):
        cwd = self.root / "cwd"
        write(cwd / "node.exe", "a node.exe in the working directory, never used")
        write(cwd / "relnode" / "node.exe", "a node.exe on a relative PATH entry, never used")
        self.env["PATH"] = os.pathsep.join(["relnode", str(self.node.parent), str(STUB), os.environ["PATH"]])
        ready = self.prepare(cwd=cwd)
        self.assertEqual(ready["state"], "prepared", ready)
        plan = json.loads((Path(ready["directory"]) / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["browser"]["definition"]["command"], self.node.as_posix())
        self.assertEqual(self.call("finish", ready["directory"])["state"], "finished")

    def test_mcp_temp_swapped_after_collect_is_not_followed_by_finish(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        temp = Path(plan["browser"]["temp"])
        os.rename(temp, str(temp) + ".moved")
        junction(temp, self.sentinel)
        sentinel = tree(self.sentinel)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "failed", finished)
        self.assertEqual(finished["retained_location"], str(temp))
        self.assertIn("link or junction", finished["reason"])
        self.assertEqual(tree(self.sentinel), sentinel)
        self.assertFalse(os.path.lexists(plan["summary"]["target"]))
        self.assertTrue(directory.exists())
        os.rmdir(temp)
        os.rename(str(temp) + ".moved", temp)

    # --- lifecycle (I12) ---

    def test_collect_keeps_run_directory_and_target_then_finish_removes_them(self):
        ready, directory, plan = self.prepared()
        target = Path(plan["summary"]["target"])
        self.assertEqual(sorted(tree(target)), [".stub", ".stub/scenario.json", "evidence", "fakeapp.py", "index.html"])
        collected = self.collect_completed(directory)
        reply = collected["runs"][0]["reply"]
        self.assertEqual(reply["format"], "structured", reply)
        self.assertEqual(reply["content"], UI_REPLY)
        self.assertEqual(collected["target"], str(target))
        self.assertTrue(collected["target_kept"])
        self.assertEqual(collected["next"], "finish")
        self.assertTrue(target.exists() and directory.exists())
        self.assertEqual(self.call("collect", directory)["runs"][0]["reply"]["content"], UI_REPLY, "collect again")
        # Codex wrote nothing into the copy (records live outside it).
        self.assertEqual(sorted(tree(target)), [".stub", ".stub/scenario.json", "evidence", "fakeapp.py", "index.html"])
        self.assertEqual(self.call("cleanup", self.root)["state"], "failed", "an arbitrary directory is refused")
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(finished["target_removed"])
        self.assert_all_removed(directory)
        self.assertEqual(self.violations(), "")

    def test_codex_failure_removes_the_target_at_once(self):
        self.scenario({"exec": {"mode": "fail"}})
        ready, directory, plan = self.prepared()
        ran = self.call("run", directory)
        self.assertEqual(ran["state"], "finished", ran)
        self.assertTrue(ran["target_removed"], ran)
        self.assertEqual(os.listdir(self.targets), [], "target and siblings gone before collect")
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "failed", collected)
        self.assertNotIn("reply", collected["runs"][0])
        self.assert_all_removed(directory)

    def test_unusable_reply_removes_the_target_at_collect(self):
        self.scenario({"exec": {"mode": "unreadable"}})
        ready, directory, plan = self.prepared()
        self.assertEqual(self.call("run", directory)["state"], "finished")
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "failed", collected)
        self.assertTrue(collected["target_removed"])
        self.assert_all_removed(directory)

    def test_launch_failure_removes_the_target_at_once(self):
        ready, directory, plan = self.prepared()
        launched = self.call("run", directory, code=SPAWN_FAILURE)
        self.assertEqual(launched["state"], "launch_failed", launched)
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.exec_calls(), [])
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "failed", collected)
        self.assert_all_removed(directory)

    def test_taken_proxy_port_refuses_the_run_and_removes_the_target(self):
        # C4: the supervisor holds the owned proxy port from app-start on, so a taken port refuses the app start
        # (and so the run): no app process, no Codex, target and run directory removed.
        ready = self.prepare()
        directory = Path(ready["directory"])
        plan = json.loads((directory / "plan.json").read_text("utf-8"))
        squatter = socket.socket()
        self.addCleanup(squatter.close)
        squatter.bind(("127.0.0.1", plan["browser"]["proxy_port"]))
        squatter.listen(1)
        refused = self.call("app-start", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("owned proxy port", refused["reason"])
        self.assertTrue(refused["target_removed"], refused)
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.exec_calls(), [])
        self.assertEqual(self.runs(), [])

    def test_run_is_never_replayed(self):
        ready, directory, plan = self.prepared()
        self.collect_completed(directory)
        self.assertEqual(self.call("run", directory)["state"], "failed")
        self.assertEqual(len(self.exec_calls()), 1)
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_proxy_port_is_held_while_codex_runs_and_stop_removes_the_target(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 20, "event_every_s": 0.2}})
        self.env["ASK_CODEX_STOP_WINDOW_S"] = "1"
        ready, directory, plan = self.prepared()
        port = plan["browser"]["proxy_port"]
        with self.background("run", directory) as process:
            try:
                deadline = time.monotonic() + 30
                while not (self.records / "exec-argv.json").exists():
                    self.assertLess(time.monotonic(), deadline, "Codex never started")
                    time.sleep(0.2)
                with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                    client.settimeout(5)
                    self.assertEqual(client.recv(16), b"", "the owned proxy accepts and closes at once")
                with socket.socket() as other, self.assertRaises(OSError):
                    other.bind(("127.0.0.1", port))
                self.assertEqual(self.call("finish", directory)["state"], "failed", "finish waits for Codex")
                self.assertTrue(Path(plan["summary"]["target"]).exists())
                stopped = self.call("stop", directory)
            finally:
                process.communicate(timeout=60)
        self.assertIn(stopped["state"], ("stopped", "stop_unconfirmed"), stopped)
        if stopped["state"] == "stopped":
            self.assertTrue(stopped["target_removed"], stopped)
            self.assertEqual(os.listdir(self.targets), [])
        else:
            self.assertTrue(stopped["target_kept"], stopped)
            self.assertTrue(Path(plan["summary"]["target"]).exists(), "an unconfirmed stop keeps the target")
        collected = self.call("collect", directory)
        self.assertNotIn("reply", collected["runs"][0])
        if stopped["state"] == "stopped":
            self.assert_all_removed(directory)

    def test_prepared_exercise_can_be_discarded_by_cleanup(self):
        ready, directory, plan = self.prepared()
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned")
        self.assert_all_removed(directory)

    # --- reply: UI schema and redaction (I11) ---

    def test_reply_is_redacted_before_it_is_returned(self):
        reply = json.loads(json.dumps(UI_REPLY))
        reply["claims"][0]["actual"] = "The page shows Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl"
        reply["claims"][0]["steps"] = ["Run the app with --password hunter2 and --token=abc",
                                       "Open http://admin:s3cret@127.0.0.1:15173/"]
        reply["claims"][0]["evidence"] = ["console: api_key=0123456789abcdef0123456789", "sk-proj-ABCDEFGHIJKLMNOP1234"]
        reply["out_of_scope"] = ["A ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123 token is printed in the footer"]
        self.scenario({"exec": {"reply": reply}})
        ready, directory, plan = self.prepared()
        collected = self.collect_completed(directory)
        content = collected["runs"][0]["reply"]
        self.assertEqual(content["format"], "structured", content)
        text = json.dumps(content)
        for secret in ("eyJhbGciOiJIUzI1NiJ9", "hunter2", "abc\"", "s3cret", "admin:", "0123456789abcdef0123456789",
                       "sk-proj-ABCDEFGHIJKLMNOP1234", "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123"):
            self.assertNotIn(secret, text)
        self.assertIn("[REDACTED]", text)
        self.assertEqual(content["content"]["claims"][1], UI_REPLY["claims"][1], "text without secrets unchanged")
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_malformed_reply_is_unstructured_and_kept_until_finish(self):
        self.scenario({"exec": {"mode": "schema-violation"}})
        ready, directory, plan = self.prepared()
        collected = self.collect_completed(directory)
        self.assertEqual(collected["runs"][0]["reply"]["format"], "unstructured")
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assert_all_removed(directory)

    # --- I13 ---

    def test_exercise_operations_refuse_on_other_platforms(self):
        refused = self.prepare(platform="linux")
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("Windows only", refused["reason"])
        self.assertEqual(self.runs(), [])
        self.assertEqual(os.listdir(self.targets), [])
        ready, directory, plan = self.prepared()
        before = tree(self.targets)
        for args in (("run", directory), ("wait", directory, "--seconds", "0"), ("collect", directory),
                     ("stop", directory), ("cleanup", directory), ("finish", directory), ("continue", directory),
                     ("app-start", directory)):
            with self.subTest(action=args[0]):
                result = self.call(*args, platform="linux")
                self.assertEqual(result["state"], "failed", result)
                self.assertIn("Windows only", result["reason"])
                self.assertEqual(tree(self.targets), before)
        self.assertEqual(self.exec_calls(), [])
        self.assertFalse((directory / "started").exists(), "no execution attempt recorded")
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_new_modules_read_no_environment_variable(self):
        for name in ("exercise.py", "browser.py", "redact.py"):
            with self.subTest(module=name):
                tree_ = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))
                reads = [n for n in ast.walk(tree_) if isinstance(n, ast.Attribute) and
                         n.attr in ("environ", "getenv", "environb", "putenv")]
                self.assertEqual(reads, [])
                self.assertNotIn("getenv", (SCRIPTS / name).read_text(encoding="utf-8"))


class BrowserDefinitionTest(unittest.TestCase):
    """In-process checks of the one definition function (browser.py)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        import browser
        cls.browser = browser

    def instance(self, **values):
        b = self.browser
        template = b.template(["127.0.0.1:15173"], False, Path("C:/nodejs/node.exe"), Path("D:/state/entry.js"))
        values = {"nonce": "cdt_" + "0" * 16, "target": r"D:\t\target", "cwd": r"D:\t\target.mcp-cwd-1",
                  "temp": r"D:\t\target.mcp-temp-1", "proxy_port": 40000,
                  "profile": r"D:\t\target.mcp-profile-1", **values}
        return b.instantiate(template, **values)

    def test_template_placeholders_are_all_replaced_and_paths_are_forward_slashed(self):
        definition = self.instance()
        text = json.dumps(definition)
        for placeholder in ("<nonce>", "<target>", "<cwd>", "<temp>", "<profile>", "<proxy port>"):
            self.assertNotIn(placeholder, text)
        self.assertNotIn("\\\\", text)
        self.assertEqual(definition["env"]["TEMP"], "D:/t/target.mcp-temp-1")
        self.assertEqual(definition["cwd"], "D:/t/target.mcp-cwd-1")
        self.assertIn("--userDataDir=D:/t/target.mcp-profile-1", definition["args"])
        self.assertNotIn("--isolated", definition["args"])
        self.assertEqual(self.browser.never_listed(definition, r"D:\t\target.mcp-profile-1"), [])

    def test_unsafe_per_run_values_are_refused(self):
        for values in ({"nonce": "cdt_x"}, {"nonce": "other_" + "0" * 16}, {"proxy_port": 80}, {"proxy_port": "40000"},
                       {"target": "D:\\t\\<cwd>"}, {"temp": "D:\\t\\x\ny"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.instance(**values)

    def test_a_backslash_in_any_value_is_refused(self):
        definition = self.instance()
        definition["command"] = "C:\\nodejs\\node.exe"
        with self.assertRaises(ValueError):
            self.browser.config_overrides(definition)

    def test_a_codex_configuration_in_the_target_is_refused_before_any_listing(self):
        import exercise

        class NoCodex:
            def listing(self, *args):
                raise AssertionError("no Codex command may run")

            mcp_get = listing

        with tempfile.TemporaryDirectory(prefix="ask-codex-c2-") as directory:
            write(Path(directory) / ".codex/config.toml", "")
            with self.assertRaises(ValueError) as refused:
                exercise.preflight(NoCodex(), directory, self.instance())
            self.assertIn("project Codex configuration", str(refused.exception))

    def test_never_listed_arguments_are_found(self):
        definition = self.instance()
        profile = r"D:\t\target.mcp-profile-1"
        for flag in ("--config=x.json", "--browserUrl=http://127.0.0.1:9222", "--userDataDir=D:/p", "--slim",
                     "--categoryExtensions", "--experimentalScreencast", "--allowUnrestrictedPaths", "--autoConnect",
                     "--isolated", "--user-data-dir=D:/p", "--userDataDir=D:/t/target.mcp-profile-1"):
            with self.subTest(flag=flag):
                self.assertEqual(self.browser.never_listed({**definition, "args": [*definition["args"], flag]},
                                                           profile), [flag])
        # The run-owned profile itself is required: a definition without it (or with --isolated instead) is refused.
        without = [a for a in definition["args"] if not a.startswith("--userDataDir=")]
        self.assertEqual(self.browser.never_listed({**definition, "args": without}, profile),
                         ["(missing) --userDataDir=D:/t/target.mcp-profile-1"])
        self.assertEqual(self.browser.never_listed({**definition, "args": [*without, "--isolated"]}, profile),
                         ["--isolated", "(missing) --userDataDir=D:/t/target.mcp-profile-1"])
        # Another profile than the one the script produced is refused.
        self.assertEqual(self.browser.never_listed(definition, r"D:\t\other-profile"),
                         ["--userDataDir=D:/t/target.mcp-profile-1", "(missing) --userDataDir=D:/t/other-profile"])

    def test_profile_seed_is_exactly_the_download_block(self):
        with tempfile.TemporaryDirectory(prefix="ask-codex-c3-") as directory:
            profile = Path(directory) / "profile"
            profile.mkdir()
            self.browser.seed_profile(profile)
            self.assertEqual(json.loads((profile / "Default" / "Preferences").read_text("utf-8")),
                             {"download_restrictions": 3})
            self.assertEqual(self.browser.profile_problems(profile), [])
            with self.assertRaises(ValueError):
                self.browser.seed_profile(profile)  # never into a non-empty directory


class RedactionTest(unittest.TestCase):
    """Patterns of plan I11, one module (skills/ask/scripts/redact.py)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        import redact
        cls.redact = staticmethod(redact.redact)
        cls.redact_value = staticmethod(redact.redact_value)

    def test_each_pattern_redacts(self):
        cases = {
            "Authorization: Bearer abcDEF1234567890xyz": ("Bearer [REDACTED]", "abcDEF1234567890xyz"),
            "Authorization: Basic dXNlcjpwYXNzd29yZA==": ("Basic [REDACTED]", "dXNlcjpwYXNzd29yZA"),
            "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpM": ("[REDACTED]", "eyJhbGci"),
            "key sk-ABCDEFGHIJKLMNOPQRSTUVWX": ("[REDACTED]", "sk-ABCDEF"),
            "use sk-proj-abcdefghijklmnop_1234": ("[REDACTED]", "sk-proj-"),
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 leaked": ("[REDACTED]", "ghp_"),
            "github_pat_11ABCDEFG0123456789_abcdefghijkl": ("[REDACTED]", "github_pat_"),
            "slack xoxb-1234567890-abcdefghij": ("[REDACTED]", "xoxb-"),
            "api_key=0123456789abcdef0123": ("api_key=[REDACTED]", "0123456789abcdef0123"),
            '"client_secret": "Zm9vYmFyYmF6cXV4MTIzNDU2"': ('"client_secret": "[REDACTED]"', "Zm9vYmFy"),
            "X-Auth-Token: 9f86d081884c7d659a2feaa0c55ad015": ("[REDACTED]", "9f86d081"),
            "password: aGVsbG8gd29ybGQgMTIzNDU2": ("password: [REDACTED]", "aGVsbG8g"),
            "postgres://admin:s3cret@127.0.0.1:5432/db": ("postgres://[REDACTED]@127.0.0.1:5432/db", "s3cret"),
            "https://ghtoken@github.com/x": ("https://[REDACTED]@github.com/x", "ghtoken"),
            "app --password hunter2 --port 80": ("--password [REDACTED] --port 80", "hunter2"),
            "app --token=a": ("--token=[REDACTED]", "=a"),
            "app --db-password 'two words'": ("--db-password '[REDACTED]'", "two words"),
            'app -secret "x y z"': ('-secret "[REDACTED]"', "x y z"),
            "app --api-key K": ("--api-key [REDACTED]", " K"),
            # Plan I11 has no digit condition on a labelled run (code review 1, B2).
            "api_key=AbCdEfGhIjKlMnOpQrStUv": ("api_key=[REDACTED]", "AbCdEfGh"),
            "Authorization: Token sEcReTsEcReTsEcReTx": ("Token [REDACTED]", "sEcReT"),
            "password=CorrectHorseBatteryStaple": ("password=[REDACTED]", "CorrectHorse"),
            # An explicit `=` or `:` after a secret's name: the value whatever its shape (code review 2, B2).
            "DB_PASSWORD=supersecretpassword": ("DB_PASSWORD=[REDACTED]", "supersecret"),
            "JWT_SECRET=supersecretjwtsigningkey": ("JWT_SECRET=[REDACTED]", "supersecretjwt"),
            "apiKey: hunter2": ("apiKey: [REDACTED]", "hunter2"),
            # Exceeding any length never lets a secret through (code review 2, B3).
            "https://" + "u" * 320 + "@host/": ("https://[REDACTED]@host/", "u" * 20),
            '--private-key "-----BEGIN KEY-----\nMIIEvQIBADAN\n-----END KEY-----" --port 1':
                ('--private-key "[REDACTED]" --port 1', "MIIEvQIBADAN"),
            '--token "' + "s" * 5000 + '"': ('--token "[REDACTED]"', "s" * 20),
            "--password          hunter2": ("--password          [REDACTED]", "hunter2"),
            "API_KEY:          0123456789abcdef0123": ("API_KEY:          [REDACTED]", "0123456789"),
            '--token "never closed\nsecond line': ('--token "[REDACTED]', "second line"),
            # Right after `-` or `_` (code review 2, NB2).
            "x-eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.c2lnbmF0dXJl": ("x-[REDACTED]", "eyJhbGci"),
            "key_sk-ABCDEFGHIJKLMNOPQRSTUV": ("key_[REDACTED]", "sk-ABCDEF"),
            "x-ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ0123": ("x-[REDACTED]", "ghp_"),
            # A label holding a secret word that is not its name, then `=` or `:`: a long run that looks like a
            # secret (C2 R1; plan I11 "long hex or base64 runs following token, key, secret, password").
            "passwordhash: 5f4dcc3b5aa765d61d8327deb882cf99": ("passwordhash: [REDACTED]", "5f4dcc3b"),
            "api_keys: 0123456789abcdef0123": ("api_keys: [REDACTED]", "0123456789abcdef"),
            "tokens=AbCdEf0123456789abcd": ("tokens=[REDACTED]", "AbCdEf0123"),
            "secretvalue=Zm9vYmFyYmF6cXV4MTIzNDU2": ("secretvalue=[REDACTED]", "Zm9vYmFy"),
            "apitokens: 9f86d081884c7d659a2feaa0c55ad015": ("apitokens: [REDACTED]", "9f86d081"),
            "X-Auth-Tokens: 9f86d081884c7d659a2feaa0c55ad015": ("X-Auth-Tokens: [REDACTED]", "9f86d081"),
            "keys: aGVsbG8gd29ybGQgMTIzNDU2": ("keys: [REDACTED]", "aGVsbG8g"),
            '"passwordhash": "5f4dcc3b5aa765d61d8327deb882cf99"': ('"passwordhash": "[REDACTED]"', "5f4dcc3b"),
        }
        for text, (kept, gone) in cases.items():
            with self.subTest(text=text):
                result = self.redact(text)
                self.assertIn(kept, result)
                self.assertNotIn(gone, result)

    def test_ordinary_text_is_left_alone(self):
        for text in ("Basic navigation works on every page.", "The bearer of bad news is the save button.",
                     "The keyboard shortcut for the token list is missing.", "password field has no label",
                     "Open http://127.0.0.1:15173/login and click Save", "Viewport 390x844 overflows",
                     "The internationalization keys are shown raw", "git@github.com:org/repo.git",
                     "the token list is empty", "Basic navigation works",
                     "Keyboard: Tab skips the Save button", "risk-assessment-overview-dashboard",
                     "task_ghp_like_name is shown", "tokens: 3"):
            with self.subTest(text=text):
                self.assertEqual(self.redact(text), text)

    def test_hostile_input_is_redacted_in_linear_time(self):
        # Reply text is attacker-influenced; a catastrophic backtrack would hang `collect` (code review 1, B1).
        fragments = ["Bearer abcDEF1234567890xyz", "--password hunter2", "api_key=AbCdEfGhIjKlMnOpQrStUv",
                     "key" * 40, "--" + "key-" * 30, "token-" * 30, "eyJ-" * 30, "http://a:b@127.0.0.1/",
                     "a+" * 40 + "://", "The basic navigation works.", "sk-ABCDEFGHIJKLMNOPQRST", "token" + " " * 40]
        mixed, i = [], 0
        while sum(map(len, mixed)) < 50_000:
            mixed.append(fragments[i % len(fragments)])
            i += 1
        cases = {"flag run": "--" + "key-" * 2500, "token run": "token-" * 2000, "key run": "key" * 3000,
                 "kebab identifiers": "-".join(["identifier"] * 800), "jwt starts": "eyJ-" * 2500,
                 "scheme run": "a+" * 5000 + "://", "spaced label": "token" + " " * 10_000 + "x",
                 "unterminated quotes": "--token '" * 1100, "mixed 50 KB": " ".join(mixed),
                 "spaced colon labels": ("key" + " " * 5000 + ":") * 10,
                 "interleaved quotes 100 KB": ("--key \"" + "--key '") * 7200,
                 "one open quote then 100 KB": '--key "' + "--key 'x " * 11_200,
                 "long userinfo runs": ("a://" + "u" * 2000 + " ") * 25,
                 "word-holding labels then runs": ("tokens:" + "a" * 2000 + " ") * 5 + "tokens=a/" * 1000}
        timings = {}
        for label, text in cases.items():
            with self.subTest(case=label, size=len(text)):
                self.assertGreaterEqual(len(text), 8_000)
                start = time.perf_counter()
                result = self.redact(text)
                timings[label] = time.perf_counter() - start
                self.assertLess(timings[label], 1.0)
                self.assertIsInstance(result, str)
        sys.stderr.write("\nredaction timings: " + ", ".join(f"{k} ({len(cases[k])} chars) {v * 1000:.1f} ms"
                                                              for k, v in timings.items()) + "\n")
        self.assertIn("[REDACTED]", self.redact(" ".join(mixed)))
        self.assertNotIn("hunter2", self.redact(" ".join(mixed)))

    def test_values_are_redacted_recursively_and_structure_is_kept(self):
        value = {"a": ["Bearer abcDEF1234567890xyz", 1, None, True], "b": {"c": "--token=x"}}
        self.assertEqual(self.redact_value(value),
                         {"a": ["Bearer [REDACTED]", 1, None, True], "b": {"c": "--token=[REDACTED]"}})


class UiSchemaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        from replies import classify
        cls.classify = staticmethod(classify)
        cls.schema = json.loads((SKILL / "ui-exercise.schema.json").read_text(encoding="utf-8"))

    def test_schema_follows_the_structural_rules(self):
        nodes = []

        def walk(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    nodes.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(self.schema)
        self.assertEqual(len(nodes), 3)  # the top level, the claim and coverage
        for node in nodes:
            self.assertIs(node.get("additionalProperties"), False)
            self.assertEqual(sorted(node["required"]), sorted(node["properties"]))
        self.assertEqual(sorted(self.schema["properties"]), ["claims", "coverage", "out_of_scope"])
        claim = self.schema["properties"]["claims"]["items"]["properties"]
        self.assertEqual(sorted(claim), sorted(["category", "statement", "steps", "expected", "actual", "viewport",
                                                "evidence", "confidence", "in_scope"]))
        self.assertEqual(claim["category"]["enum"], ["bug", "layout", "ux"])
        for name in ("expected", "actual", "viewport"):
            self.assertEqual(claim[name]["type"], ["string", "null"])
        self.assertEqual(claim["in_scope"]["type"], "boolean")
        for name in ("steps", "evidence"):
            self.assertEqual(claim[name]["type"], "array")
        self.assertEqual(self.schema["properties"]["out_of_scope"]["type"], "array")

    def test_classifier_selects_the_ui_schema_like_the_discussion_schema(self):
        self.assertEqual(self.classify(json.dumps(UI_REPLY), "ui-exercise")["format"], "structured")
        self.assertEqual(self.classify(json.dumps(UI_REPLY), "consultation")["format"], "unstructured")
        broken = []
        for change in ({"category": "crash"}, {"in_scope": "true"}, {"in_scope": 1}, {"steps": "click"},
                       {"expected": 3}, {"extra": "x"}):
            claim = {**UI_REPLY["claims"][0], **change}
            broken.append({**UI_REPLY, "claims": [claim]})
        missing = json.loads(json.dumps(UI_REPLY))
        del missing["claims"][0]["viewport"]
        broken += [missing, {**UI_REPLY, "coverage": ["/"]}, {"claims": []}]
        for value in broken:
            with self.subTest(value=value):
                self.assertEqual(self.classify(json.dumps(value), "ui-exercise")["format"], "unstructured")
        for text in ("plain text", "[1, 2]", "null", "true", ""):
            self.assertEqual(self.classify(text, "ui-exercise")["format"], "unstructured")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--test-root", help="parent of the per-test directories (outside any repository)")
    known, rest = parser.parse_known_args()
    if known.test_root:
        TEST_ROOT = Path(known.test_root)
    unittest.main(argv=[sys.argv[0], *rest])
