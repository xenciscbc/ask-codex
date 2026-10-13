"""Guards of an exercise (plan `.scratch/exercise-skills/plan.md` claim C3: I5 install verification, I7 fingerprint and
cache, I8 guard job, I13 seams); offline, Windows only, never calls a real Codex service and never starts Chrome.

Seams are in-process only (plan I13): the CLI runs through a bootstrap that patches `browser.local_app_data` (so the
package install and the guard cache live under the test directory) and, per test, the guard's dependency facts and
browser checks (`guard.dependencies`, `guard.browser_guard`, `guard.now`); unit tests pass a test-only `state_dir`.
No test sets an environment variable the production path reads; one test sets such variables and shows they are
ignored. Every test works in a fresh directory under the test root (`D:\\tmp\\ask-codex-tests`), removed after.
"""
import ast
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLI = REPO / "skills/ask/scripts/consult.py"
SCRIPTS = REPO / "skills/ask/scripts"
STUB = REPO / "evals/_harness/stub"
TEST_ROOT = Path(r"D:\tmp\ask-codex-tests")
ENTRY = ("ask-codex", "chrome-devtools-mcp-1.10.1", "node_modules", "chrome-devtools-mcp", "build", "src", "bin",
         "chrome-devtools-mcp.js")
REPLY = {"claims": [], "out_of_scope": [], "coverage": {"pages": ["/"], "flows": [], "viewports": ["1280x720"]}}
FACTS = {"node": "C:/fake/node.exe", "node_version": "v24.12.0", "manifest_sha256": "m" * 64,
         "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe", "chrome_version": "154.0.8037.98",
         "codex_version": "codex-cli 0.159.3", "chrome_policy_sha256": "p" * 64}

sys.path.insert(0, str(HERE))
from exercise_run_test import FAKE_APP  # noqa: E402  (the fake app of the run tests, C4)

if sys.platform == "win32":
    sys.path.insert(0, str(SCRIPTS))
    import browser
    import guard
    import install
    import mcp_stdio
    import winjob

BOOTSTRAP = r"""
import json, runpy, sys
from pathlib import Path
script = sys.argv.pop(1)
seams = json.loads(sys.argv.pop(1))
sys.path.insert(0, str(Path(script).parent))
import browser, guard, install
browser.local_app_data = lambda: Path(seams["local_app_data"])
if not seams.get("real_install"):
    install.verify_installed = lambda: "test-manifest"
state = {"guard_runs": 0}
if seams.get("facts") is not None:
    guard.dependencies = lambda cli, cwd, codex_cwd, state_dir=None: dict(seams["facts"])
if seams.get("items") is not None:
    def browser_guard(cli, directory, plan, template, state_dir=None):
        with open(seams["guard_log"], "a", encoding="utf-8") as log:
            log.write(json.dumps({"app": plan["summary"]["app"], "template_args": template["args"]}) + "\n")
        return seams["items"]
    guard.browser_guard = browser_guard
if seams.get("now") is not None:
    guard.now = lambda: seams["now"]
if seams.get("code"):
    exec(seams["code"], {"guard": guard, "install": install, "browser": browser})
sys.argv[0] = script
runpy.run_path(script, run_name="__main__")
"""

PASS = [{"item": "check-page-loads-from-127.0.0.1:15173", "ok": True, "detail": ""},
        {"item": "service-worker-to-free-loopback-port-blocked", "ok": True, "detail": ""}]


def write(path, text="x"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def scrub(path):
    """Test cleanup only: links are unlinked, never followed."""
    path = "\\\\?\\" + str(path) if not str(path).startswith("\\\\?\\") else str(path)
    if not os.path.lexists(path):
        return
    status = os.lstat(path)
    if status.st_file_attributes & 0x400:
        (os.rmdir if status.st_file_attributes & 0x10 else os.unlink)(path)
    elif status.st_file_attributes & 0x10:
        for entry in os.scandir(path):
            scrub(entry.path)
        os.chmod(path, 0o600)
        os.rmdir(path)
    else:
        os.chmod(path, 0o600)
        os.unlink(path)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def tearDownModule():
    try:
        TEST_ROOT.rmdir()
    except OSError:
        pass


@unittest.skipUnless(sys.platform == "win32", "the exercise platform layer is Windows only (plan I13)")
class GuardLifecycleTest(unittest.TestCase):
    """The guard through the public CLI with the stub Codex (Seam 2)."""

    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="g-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.project, self.targets = self.root / "project", self.root / "targets"
        self.base, self.records, self.requests = self.root / "base", self.root / "records", self.root / "requests"
        self.local, self.home = self.root / "localappdata", self.root / "home"
        for directory in (self.project, self.targets, self.base, self.requests, self.home):
            directory.mkdir()
        write(self.project / "index.html", "<h1>app</h1>")
        write(self.project / ".stub/scenario.json", json.dumps({"records": str(self.records),
                                                                "exec": {"reply": REPLY}}))
        write(self.local.joinpath(*ENTRY), "// fake entry script, never run")
        self.node = write(self.root / "node" / "node.exe", "fake node, never run")
        self.guard_log = self.root / "guard-runs.jsonl"
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CODEX_HOME": str(self.home / ".codex"),
                    "PATH": os.pathsep.join([str(self.node.parent), str(STUB), os.environ["PATH"]])}
        self.ports = [free_port(), free_port()]
        self.request = {"interaction": "exercise", "kind": "ui", "project": str(self.project),
                        "prompt": "Exercise the app.", "models": [{"model": "gpt-6-sol", "effort": "high"}],
                        "target_root": {"path": str(self.targets), "confirmed_by_user": True},
                        "app": [f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{self.ports[1]}"], "headed": False,
                        "scope": ""}

    def call(self, *args, env=None, **seams):
        seams = {"local_app_data": str(self.local), "guard_log": str(self.guard_log), **seams}
        result = subprocess.run([sys.executable, "-c", BOOTSTRAP, str(CLI), json.dumps(seams), *map(str, args)],
                                env=env or self.env, capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def prepare(self, name, **change):
        path = self.requests / f"{name}.json"
        path.write_text(json.dumps({**self.request, "target_name": name, **change}), encoding="utf-8")
        ready = self.call("prepare", path, "--base", self.base)
        self.assertEqual(ready["state"], "prepared", ready)
        return Path(ready["directory"])

    def guard_runs(self):
        return self.guard_log.read_text("utf-8").splitlines() if self.guard_log.exists() else []

    def exec_calls(self):
        calls = self.records / "exec-calls"
        return sorted(calls.glob("*.json")) if calls.exists() else []

    def cache_files(self):
        cache = self.local / "ask-codex" / "guard-cache"
        return sorted(p.name for p in cache.iterdir()) if cache.exists() else []

    # --- cache: hit, misses, expiry (ticket 03 Seam 2) ---

    def test_a_pass_is_reused_on_another_target_and_rerun_on_another_port_chrome_or_package(self):
        first = self.prepare("first")
        passed = self.call("guard", first, facts=FACTS, items=PASS)
        self.assertEqual((passed["state"], passed["guard"]["source"]), ("guard_passed", "ran"), passed)
        self.assertEqual(len(self.guard_runs()), 1)
        self.assertEqual(len(self.cache_files()), 1, "one pass in the user-level cache")
        self.assertFalse(any((self.project / name).exists() for name in ("guard-cache", "ask-codex")))
        # Another target (and another nonce, cwd, TEMP and proxy port): the same fingerprint -> cache hit, no run.
        second = self.prepare("second")
        hit = self.call("guard", second, facts=FACTS, items=PASS)
        self.assertEqual(hit["guard"]["source"], "cache", hit)
        self.assertEqual(hit["guard"]["fingerprint"], passed["guard"]["fingerprint"])
        self.assertEqual(hit["guard"]["passed_at"], passed["guard"]["passed_at"])
        self.assertEqual(len(self.guard_runs()), 1, "a cache hit runs no browser guard")
        # Another app port: another fingerprint -> the guard runs again.
        third = self.prepare("third", app=[f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{free_port()}"])
        miss = self.call("guard", third, facts=FACTS, items=PASS)
        self.assertEqual(miss["guard"]["source"], "ran", miss)
        self.assertNotEqual(miss["guard"]["fingerprint"], passed["guard"]["fingerprint"])
        self.assertEqual(len(self.guard_runs()), 2)
        # The headed flag, a Chrome update, another package manifest, node or codex-cli: each a new fingerprint.
        changes = [("headed", {}, {"headed": True}), ("chrome", {"chrome_version": "155.0.8059.40"}, {}),
                   ("package", {"manifest_sha256": "n" * 64}, {}), ("node", {"node_version": "v24.13.0"}, {}),
                   ("codex", {"codex_version": "codex-cli 0.160.0"}, {}),
                   ("policy", {"chrome_policy_sha256": "q" * 64}, {})]
        for label, facts, request in changes:
            with self.subTest(change=label):
                directory = self.prepare(f"change-{label}", **request)
                result = self.call("guard", directory, facts={**FACTS, **facts}, items=PASS)
                self.assertEqual(result["guard"]["source"], "ran", result)
        self.assertEqual(len(self.guard_runs()), 2 + len(changes))
        for directory in (first, second, third):
            self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_a_pass_expires_after_12_hours(self):
        first = self.prepare("first")
        passed = self.call("guard", first, facts=FACTS, items=PASS)
        at = passed["guard"]["passed_at"]
        inside = self.call("guard", self.prepare("inside"), facts=FACTS, items=PASS, now=at + 12 * 3600)
        self.assertEqual(inside["guard"]["source"], "cache", inside)
        expired = self.call("guard", self.prepare("expired"), facts=FACTS, items=PASS, now=at + 12 * 3600 + 1)
        self.assertEqual(expired["guard"]["source"], "ran", expired)
        self.assertEqual(len(self.guard_runs()), 2)

    def test_a_cache_hit_rechecks_that_every_app_port_is_free(self):
        self.call("guard", self.prepare("first"), facts=FACTS, items=PASS)
        second = self.prepare("second")
        for host, family in (("127.0.0.1", socket.AF_INET), ("0.0.0.0", socket.AF_INET), ("::1", socket.AF_INET6)):
            with self.subTest(listener=host):
                directory = self.prepare(f"busy-{family}-{host.replace(':', '').replace('.', '')}")
                with socket.socket(family) as taken:
                    taken.bind((host, self.ports[1]))
                    taken.listen(1)
                    refused = self.call("guard", directory, facts=FACTS, items=PASS)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn(f":{self.ports[1]}", refused["reason"])
                self.assertIn("in use", refused["reason"])
                self.assertTrue(refused["target_removed"], refused)
        self.assertEqual(len(self.guard_runs()), 1)
        self.assertEqual(self.call("guard", second, facts=FACTS, items=PASS)["guard"]["source"], "cache")
        self.assertEqual(self.call("finish", second)["state"], "finished")

    # --- a failed guard: every failing item reported, no app start, no Codex ---

    def test_a_failed_guard_reports_every_failing_item_removes_the_target_and_launches_no_codex(self):
        directory = self.prepare("first")
        items = [{"item": "check-page-loads-from-127.0.0.1:1", "ok": True, "detail": ""},
                 {"item": "service-worker-to-free-loopback-port-blocked", "ok": False, "detail": "arrived"},
                 {"item": "write-into-evidence-succeeds", "ok": False, "detail": "refused"},
                 {"item": "webrtc-yields-no-server-reflexive-candidate", "ok": False, "detail": "srflx"}]
        failed = self.call("guard", directory, facts=FACTS, items=items)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertEqual([i["item"] for i in failed["guard"]["failing"]],
                         ["service-worker-to-free-loopback-port-blocked", "write-into-evidence-succeeds",
                          "webrtc-yields-no-server-reflexive-candidate"])
        self.assertIn("no Codex", failed["reason"])
        self.assertTrue(failed["target_removed"])
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.cache_files(), [], "a failure is never cached")
        self.assertFalse(directory.exists())
        self.assertEqual(self.exec_calls(), [])

    def test_a_dependency_failure_stops_the_exercise_with_a_clear_message(self):
        # Chrome older than 149 (the real dependency check, with the executable's version read as 148).
        directory = self.prepare("deps")
        refused = self.call("guard", directory, items=PASS, code=(
            "guard.file_version = lambda path: '148.0.1.2'\n"
            "guard.node_version = lambda node, cwd: 'v24.12.0'\n"))
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("Chrome stable 149 or later is required (found 148.0.1.2", refused["reason"])
        self.assertTrue(refused["target_removed"])
        self.assertEqual(self.guard_runs(), [], "no browser guard after a failed dependency check")
        # node missing from the run environment: refused before anything is created.
        env = {**self.env, "PATH": os.pathsep.join([str(STUB), os.environ.get("SYSTEMROOT", r"C:\Windows")])}
        path = self.requests / "nonode.json"
        path.write_text(json.dumps({**self.request, "target_name": "nonode"}), encoding="utf-8")
        missing = self.call("prepare", path, "--base", self.base, env=env)
        self.assertEqual(missing["state"], "failed", missing)
        self.assertIn("node is required", missing["reason"])
        self.assertFalse((self.targets / "nonode").exists())
        self.assertEqual(self.exec_calls(), [])

    # --- run requires a current pass for its exact fingerprint ---

    def test_run_without_a_pass_launches_no_codex(self):
        directory = self.prepare("first")
        refused = self.call("run", directory, facts=FACTS)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("No browser guard pass", refused["reason"])
        self.assertIn("the target was removed", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        self.assertEqual(os.listdir(self.targets), [])

    def test_run_refuses_a_pass_for_another_fingerprint_or_older_than_12_hours(self):
        cases = [("chrome updated after the guard", {"facts": {**FACTS, "chrome_version": "155.0.8059.40"}},
                  "fingerprint changed"),
                 ("12 h + 1 s after the pass", {"facts": FACTS, "later": 12 * 3600 + 1}, "older than 12 hours")]
        for label, change, expected in cases:
            with self.subTest(case=label):
                directory = self.prepare(label.split()[0] + str(len(label)))
                passed = self.call("guard", directory, facts=FACTS, items=PASS)
                seams = {"facts": change["facts"]}
                if "later" in change:
                    seams["now"] = passed["guard"]["passed_at"] + change["later"]
                refused = self.call("run", directory, **seams)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn(expected, refused["reason"])
                self.assertEqual(self.exec_calls(), [])

    def test_run_with_a_current_pass_starts_codex_and_collect_names_the_guard(self):
        # C4: Codex runs only after the app started (app-start, which also requires the current pass); each
        # exercise is finished before the next one guards the same app ports.
        write(self.project / "fakeapp.py", FAKE_APP)
        commands = {"start": [{"argv": [sys.executable, "fakeapp.py", *self.request["app"]]}]}
        directory = self.prepare("first", commands=commands)
        passed = self.call("guard", directory, facts=FACTS, items=PASS)
        self.assertEqual(self.call("app-start", directory, facts=FACTS)["state"], "app_started")
        self.assertEqual(self.call("run", directory, facts=FACTS)["state"], "finished")
        self.assertEqual(len(self.exec_calls()), 1)
        collected = self.call("collect", directory, facts=FACTS)
        self.assertEqual(collected["guard"], {"source": "ran", "passed_at": passed["guard"]["passed_at"]}, collected)
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        cached = self.prepare("second", commands=commands)
        self.call("guard", cached, facts=FACTS, items=PASS)
        self.assertEqual(self.call("app-start", cached, facts=FACTS)["state"], "app_started")
        self.call("run", cached, facts=FACTS)
        self.assertEqual(self.call("collect", cached, facts=FACTS)["guard"]["source"], "cache")
        self.assertEqual(self.call("finish", cached)["state"], "finished")

    def test_app_start_requires_a_current_pass_and_the_guard_refuses_after_it(self):
        write(self.project / "fakeapp.py", FAKE_APP)
        commands = {"start": [{"argv": [sys.executable, "fakeapp.py", *self.request["app"]]}]}
        refused = self.call("app-start", self.prepare("nopass", commands=commands), facts=FACTS)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("No browser guard pass", refused["reason"])
        self.assertTrue(refused["target_removed"])
        directory = self.prepare("first", commands=commands)
        self.call("guard", directory, facts=FACTS, items=PASS)
        self.assertEqual(self.call("app-start", directory, facts=FACTS)["state"], "app_started")
        again = self.call("guard", directory, facts=FACTS, items=PASS)
        self.assertEqual(again["state"], "failed", again)
        self.assertIn("guard runs before any app process", again["reason"])
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_production_path_ignores_substitution_environment_variables(self):
        directory = self.prepare("first")
        cache = self.root / "planted-cache"
        planted = self.root / "planted-localappdata" / "ask-codex" / "guard-cache"
        planted.mkdir(parents=True)
        env = {**self.env, "ASK_CODEX_SKIP_GUARD": "1", "ASK_CODEX_GUARD": "pass", "ASK_CODEX_FAKE_GUARD": "1",
               "ASK_CODEX_GUARD_CACHE": str(cache), "ASK_CODEX_STATE_DIR": str(self.root / "planted-localappdata"),
               "LOCALAPPDATA": str(self.root / "planted-localappdata"), "ASK_CODEX_TEST": "1",
               "EVAL_ASK_CODEX_GUARD": "pass"}
        refused = self.call("run", directory, env=env, facts=FACTS)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("No browser guard pass", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        # Static: the guard, install, job and client modules read the environment only to build the MCP's
        # environment and to pass SYSTEMROOT to `node --version` (never to select, skip or substitute).
        allowed = {("guard.py", "node_version"), ("guard.py", "dependency_report"), ("guard.py", "browser_guard"),
                   ("guard.py", "dependencies"), ("install.py", "install")}
        found = set()
        for name in ("guard.py", "install.py", "winjob.py", "mcp_stdio.py", "browser.py"):
            tree = ast.parse((SCRIPTS / name).read_text(encoding="utf-8"))

            def visit(node, function):
                if isinstance(node, (ast.FunctionDef, ast.Lambda)):
                    function = getattr(node, "name", function)
                text = ast.unparse(node) if isinstance(node, (ast.Attribute, ast.Call, ast.Name)) else ""
                if text in ("os.environ", "os.getenv", "environ", "getenv", "os.environb") or \
                        text.endswith("shell_environment()"):
                    found.add((name, function))
                for child in ast.iter_child_nodes(node):
                    visit(child, function)
            visit(tree, "<module>")
        self.assertLessEqual(found, allowed, found)


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class FingerprintAndCacheTest(unittest.TestCase):
    """Unit level with a test-only state directory argument."""

    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="f-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.addCleanup(setattr, guard, "now", guard.now)

    def template(self, app, headed=False):
        return browser.template(app, headed, Path("C:/fake/node.exe"), Path("C:/state/entry.js"))

    def test_fingerprint_is_over_the_template_not_the_per_run_values(self):
        app = ["127.0.0.1:15173", "localhost:18080"]
        template = self.template(app)
        one = browser.instantiate(template, "cdt_" + "1" * 16, "D:/t/one", "D:/t/one.c", "D:/t/one.t", 40001,
                                  "D:/t/one.p")
        two = browser.instantiate(template, "cdt_" + "2" * 16, "D:/t/two", "D:/t/two.c", "D:/t/two.t", 40002,
                                  "D:/t/two.p")
        self.assertNotEqual(one, two)
        self.assertEqual(guard.fingerprint(template, FACTS), guard.fingerprint(self.template(list(app)), FACTS))
        self.assertNotEqual(guard.fingerprint(template, FACTS),
                            guard.fingerprint(self.template(["127.0.0.1:15174", "localhost:18080"]), FACTS))
        self.assertNotEqual(guard.fingerprint(template, FACTS), guard.fingerprint(self.template(app, True), FACTS))
        for key in FACTS:
            with self.subTest(fact=key):
                self.assertNotEqual(guard.fingerprint(template, FACTS),
                                    guard.fingerprint(template, {**FACTS, key: FACTS[key] + "x"}))
        for placeholder in ("<nonce>", "<target>", "<cwd>", "<temp>", "<profile>", "<proxy port>"):
            self.assertIn(placeholder, json.dumps(template))

    def test_cache_is_reused_for_at_most_12_hours(self):
        guard.now = lambda: 1_000_000.0
        guard.store_pass(self.root, "f" * 64, {"fingerprint": "f" * 64, "passed_at": 1_000_000.0})
        self.assertTrue((self.root / "guard-cache" / ("f" * 64 + ".json")).is_file())
        for offset, hit in ((0, True), (12 * 3600, True), (12 * 3600 + 1, False), (-1, False)):
            with self.subTest(offset=offset):
                guard.now = lambda: 1_000_000.0 + offset
                self.assertEqual(guard.cached_pass(self.root, "f" * 64) is not None, hit)
        guard.now = lambda: 1_000_000.0
        self.assertIsNone(guard.cached_pass(self.root, "e" * 64), "another fingerprint misses")
        # A record naming another fingerprint under this name is not a pass.
        (self.root / "guard-cache" / ("d" * 64 + ".json")).write_text(
            json.dumps({"fingerprint": "f" * 64, "passed_at": 1_000_000.0}), encoding="utf-8")
        self.assertIsNone(guard.cached_pass(self.root, "d" * 64))

    def test_mcp_environment_is_codex_defaults_then_the_definition_env(self):
        base = {"Path": "C:\\bin", "SystemRoot": "C:\\Windows", "TEMP": "R:\\Temp", "SECRET_TOKEN": "s",
                "GITHUB_TOKEN": "g", "NODE_OPTIONS": "--require evil.js", "LOCALAPPDATA": "C:\\L"}
        env = guard.mcp_environment(base, {"NODE_OPTIONS": "", "TEMP": "D:/x/t", "TMP": "D:/x/t"})
        self.assertEqual(env, {"PATH": "C:\\bin", "SYSTEMROOT": "C:\\Windows", "LOCALAPPDATA": "C:\\L",
                               "NODE_OPTIONS": "", "TEMP": "D:/x/t", "TMP": "D:/x/t"})

    def test_port_substitution_changes_only_port_numbers(self):
        self.assertEqual(guard.substitute_ports(["127.0.0.1:5173", "[::1]:8000"], {5173: 41001}),
                         ["127.0.0.1:41001", "[::1]:8000"])


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class InstallVerificationTest(unittest.TestCase):
    """I5: the install is verified against the committed manifest before every use; any difference refuses."""

    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="i-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.installed = self.root / f"{browser.PACKAGE}-{browser.VERSION}"

    def fake_install(self):
        """A tree with the manifest's file names (contents differ unless copied from a real install)."""
        real = browser.local_app_data() / "ask-codex" / f"{browser.PACKAGE}-{browser.VERSION}"
        if not real.is_dir():
            self.skipTest("the pinned package is not installed on this host (run consult.py browser-install)")
        shutil.copytree(real, self.installed)

    def test_committed_package_pins_the_version_and_the_manifest_covers_the_entry(self):
        package = json.loads((REPO / "skills/ask/browser-server/package.json").read_text("utf-8"))
        self.assertEqual(package["dependencies"], {"chrome-devtools-mcp": "1.10.1"})
        lock = json.loads((REPO / "skills/ask/browser-server/package-lock.json").read_text("utf-8"))
        self.assertEqual(lock["packages"]["node_modules/chrome-devtools-mcp"]["version"], "1.10.1")
        self.assertTrue(lock["packages"]["node_modules/chrome-devtools-mcp"]["integrity"].startswith("sha512-"))
        manifest, digest = install.manifest()
        self.assertIn("/".join(ENTRY[2:]), manifest["files"])
        self.assertEqual(len(digest), 64)

    def test_a_verified_copy_passes_and_any_tampering_refuses(self):
        self.fake_install()
        expected = install.manifest()[1]
        self.assertEqual(install.verify(self.root), expected)
        entry = self.installed.joinpath(*ENTRY[2:])
        original = entry.read_bytes()
        cases = [
            ("tampered entry script", lambda: entry.write_bytes(original + b"\n// tampered\n"),
             lambda: entry.write_bytes(original), "changed: node_modules/chrome-devtools-mcp/build/src/bin"),
            ("extra file", lambda: write(self.installed / "node_modules/evil.js"),
             lambda: (self.installed / "node_modules/evil.js").unlink(), "not in the manifest: node_modules/evil.js"),
            ("missing file", lambda: entry.rename(str(entry) + ".moved"),
             lambda: Path(str(entry) + ".moved").rename(entry), "missing: node_modules/chrome-devtools-mcp/build"),
        ]
        for label, damage, repair, expected_text in cases:
            with self.subTest(case=label):
                damage()
                with self.assertRaises(install.InstallError) as refused:
                    install.verify(self.root)
                self.assertIn(expected_text, str(refused.exception))
                self.assertIn("nothing is started", str(refused.exception))
                repair()
                self.assertEqual(install.verify(self.root), expected)

    def test_links_inside_or_at_the_install_refuse(self):
        self.fake_install()
        outside = self.root / "outside"
        outside.mkdir()
        link = self.installed / "node_modules" / "linked"
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
        with self.assertRaises(install.InstallError) as refused:
            install.verify(self.root)
        self.assertIn("link or junction", str(refused.exception))
        os.rmdir(link)
        moved = self.root / "moved"
        self.installed.rename(moved)
        subprocess.run(["cmd", "/c", "mklink", "/J", str(self.installed), str(moved)], check=True, capture_output=True)
        with self.assertRaises(install.InstallError) as refused:
            install.verify(self.root)
        self.assertIn("not a plain directory", str(refused.exception))
        os.rmdir(self.installed)

    def test_prepare_refuses_a_tampered_install_before_anything_is_created(self):
        self.fake_install()
        local = self.root / "localappdata"
        (local / "ask-codex").mkdir(parents=True)
        self.installed.rename(local / "ask-codex" / self.installed.name)
        entry = (local / "ask-codex" / self.installed.name).joinpath(*ENTRY[2:])
        entry.write_bytes(entry.read_bytes() + b"\n// tampered\n")
        project, targets, base = self.root / "project", self.root / "targets", self.root / "base"
        for d in (project, targets, base):
            d.mkdir()
        request = self.root / "request.json"
        request.write_text(json.dumps({"interaction": "exercise", "kind": "ui", "project": str(project),
                                       "prompt": "p", "models": [{"model": "m", "effort": "high"}],
                                       "target_root": {"path": str(targets), "confirmed_by_user": True},
                                       "app": ["127.0.0.1:15173"], "headed": False, "scope": ""}), encoding="utf-8")
        result = subprocess.run([sys.executable, "-c", BOOTSTRAP, str(CLI),
                                 json.dumps({"local_app_data": str(local), "real_install": True}), "prepare",
                                 str(request), "--base", str(base)], capture_output=True, text=True,
                                encoding="utf-8", timeout=120,
                                env={**os.environ, "PATH": os.pathsep.join([str(STUB), os.environ["PATH"]])})
        refused = json.loads(result.stdout)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("differs from the committed manifest", refused["reason"])
        self.assertEqual(os.listdir(targets), [])
        self.assertFalse((base / "ask-codex").exists())


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class GuardProcessTest(unittest.TestCase):
    """I8 (guard part): own kill-on-close job, created suspended, assigned, resumed; not a member; stdio only."""

    def test_job_contains_the_child_and_its_descendants_and_ends_them(self):
        job = winjob.Job("ask-codex-test")
        self.addCleanup(job.close)
        code = ("import subprocess, sys, time; c = subprocess.Popen([sys.executable, '-c', 'import time; "
                "time.sleep(60)']); print(c.pid, flush=True); time.sleep(60)")
        process = winjob.start_suspended(job, [sys.executable, "-c", code], str(Path.cwd()),
                                         {"SYSTEMROOT": os.environ["SYSTEMROOT"], "PATH": os.environ["PATH"]})
        self.addCleanup(process.close)
        grandchild = int(process.stdout.readline())
        self.assertIn(process.pid, job.pids())
        self.assertIn(grandchild, job.pids(), "a descendant started at the child's first instruction is in the job")
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.IsProcessInJob.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        member = wintypes.BOOL()
        self.assertTrue(kernel32.IsProcessInJob(kernel32.GetCurrentProcess(), job.handle, ctypes.byref(member)))
        self.assertFalse(member.value, "the guard is not a member of its own job")
        self.assertTrue(job.terminate())
        self.assertEqual(job.active_processes(), 0)

    def test_closing_the_job_handle_ends_the_child(self):
        job = winjob.Job("ask-codex-test")
        process = winjob.start_suspended(job, [sys.executable, "-c", "import time; print(1, flush=True); "
                                               "time.sleep(60)"], str(Path.cwd()),
                                         {"SYSTEMROOT": os.environ["SYSTEMROOT"]})
        self.addCleanup(process.close)
        process.stdout.readline()
        job.close()
        self.assertTrue(process.wait(10), "kill-on-close ended the child when the only handle closed")

    def test_the_child_inherits_only_its_stdio(self):
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        event = kernel32.CreateEventW(None, True, False, None)
        self.addCleanup(kernel32.CloseHandle, wintypes.HANDLE(event))
        self.assertTrue(kernel32.SetHandleInformation(event, 1, 1), "an inheritable handle in the guard")
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.set_inheritable(True)
        self.addCleanup(listener.close)
        job = winjob.Job("ask-codex-test")
        self.addCleanup(job.close)
        code = ("import ctypes, sys; from ctypes import wintypes; k = ctypes.WinDLL('kernel32'); "
                "k.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]; "
                "f = wintypes.DWORD(); print([bool(k.GetHandleInformation(int(h), ctypes.byref(f))) "
                "for h in sys.argv[1:]], flush=True)")
        process = winjob.start_suspended(job, [sys.executable, "-c", code, str(event), str(listener.fileno())],
                                         str(Path.cwd()), {"SYSTEMROOT": os.environ["SYSTEMROOT"]})
        self.addCleanup(process.close)
        self.assertEqual(json.loads(process.stdout.readline().decode().replace("False", "false")
                                    .replace("True", "true")), [False, False])

    def test_a_job_name_that_exists_is_refused(self):
        job = winjob.Job("ask-codex-test")
        self.addCleanup(job.close)
        original = winjob.secrets.token_hex
        winjob.secrets.token_hex = lambda n: job.name.rsplit("-", 1)[1]
        self.addCleanup(setattr, winjob.secrets, "token_hex", original)
        with self.assertRaises(OSError) as refused:
            winjob.Job("ask-codex-test")
        self.assertIn("already exists", str(refused.exception))

    def test_app_ports_are_held_exclusively_and_a_taken_port_is_refused(self):
        port, other = free_port(), free_port()
        held = guard.hold_app_ports([f"127.0.0.1:{port}", f"localhost:{other}"])
        try:
            self.assertEqual(len(held), 3, "127.0.0.1, and both loopback families for localhost")
            # The held loopback addresses cannot be bound by anyone else. (Windows still lets another socket bind
            # the wildcard address on that port; the more specific binding, the guard's, gets the connections, and
            # the guard's final item checks that no other process listens on an app port.)
            for family, address, p in ((socket.AF_INET, "127.0.0.1", port), (socket.AF_INET, "127.0.0.1", other),
                                       (socket.AF_INET6, "::1", other)):
                with socket.socket(family) as intruder, self.assertRaises(OSError):
                    intruder.bind((address, p))
        finally:
            for _, sock in held:
                sock.close()
        with socket.socket() as taken:
            taken.bind(("0.0.0.0", port))
            taken.listen(1)
            with self.assertRaises(ValueError) as refused:
                guard.hold_app_ports([f"127.0.0.1:{port}"])
            self.assertIn("in use", str(refused.exception))


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class ClientCapabilitiesTest(unittest.TestCase):
    """A2: the guard's MCP client declares no roots, declares elicitation and declines every elicitation."""

    SERVER = r"""
import json, sys
log = []
def send(m):
    sys.stdout.write(json.dumps(m) + "\n"); sys.stdout.flush()
def read():
    return json.loads(sys.stdin.readline())
init = read(); log.append(init["params"])
send({"jsonrpc": "2.0", "id": init["id"], "result": {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
      "serverInfo": {"name": "fake", "version": "0"}}})
read()  # notifications/initialized
call = read()
send({"jsonrpc": "2.0", "id": "e1", "method": "elicitation/create", "params": {"message": "allow?",
      "requestedSchema": {"type": "object", "properties": {}}}})
log.append(read())
send({"jsonrpc": "2.0", "id": "r1", "method": "roots/list"})
log.append(read())
send({"jsonrpc": "2.0", "id": call["id"], "result": {"content": [{"type": "text", "text": json.dumps(log)}]}})
"""

    def test_initialize_capabilities_and_answers(self):
        process = subprocess.Popen([sys.executable, "-c", self.SERVER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.stdin.close)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        client = mcp_stdio.Client(process.stdin, process.stdout)
        client.initialize(timeout=30)
        error, text = client.tool("list_pages", {}, timeout=30)
        self.assertFalse(error)
        initialize, elicitation, roots = json.loads(text)
        self.assertEqual(initialize["capabilities"], {"elicitation": {}})
        self.assertNotIn("roots", initialize["capabilities"])
        self.assertNotIn("sampling", initialize["capabilities"])
        self.assertEqual(elicitation, {"jsonrpc": "2.0", "id": "e1", "result": {"action": "decline"}})
        self.assertEqual(roots["id"], "r1")
        self.assertEqual(roots["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
