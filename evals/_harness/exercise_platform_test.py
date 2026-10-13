"""The exercise's platform layer selection and the eval fake (plan `.scratch/exercise-skills/plan.md` C5: I13, N10;
C4 review item 30: background operations with a result file). Offline; never calls a real Codex service.

Each test copies the `ask` skill into a fresh plugin tree under the test root (`D:\\tmp\\ask-codex-tests`, outside
any repository), so `<plugin root>/.eval-stub/` is created there and never in this checkout. The CLI runs as a
subprocess; the only in-process seam is `sys.platform` (to show the gate is replaced on a non-Windows host, I13). The
stub records outside the target (`records` in its scenario).

I13's three tests:
- a non-Windows host without the fake: every exercise operation refuses;
- the fake present and the stub check passing: validation and the whole lifecycle run through the CLI
  (exercise-deps, prepare, guard, app-start, run, wait, collect, finish), with the MCP guard against the stub;
- `.eval-stub/` present with a non-stub `codex` (or a stub reporting another version, or a fake that does not
  replace exactly the layer): every exercise operation refuses, also on Windows, and nothing is created.
"""
import ast
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]
STUB = REPO / "evals/_harness/stub"
TEST_ROOT = Path(r"D:\tmp\ask-codex-tests")

BOOTSTRAP = r"""
import runpy, sys
from pathlib import Path
script = sys.argv.pop(1)
platform = sys.argv.pop(1)
sys.path.insert(0, str(Path(script).parent))
if platform:
    sys.platform = platform
sys.argv[0] = script
runpy.run_path(script, run_name="__main__")
"""

UI_REPLY = {
    "claims": [
        {"category": "bug", "statement": "Saving an empty name shows a success message.",
         "steps": ["Open http://127.0.0.1:15173/", "Click the button named Save"], "expected": "A validation error",
         "actual": "Saved with Authorization: Bearer abcdefghijklmnop1234567890", "viewport": "1280x720",
         "evidence": ["save-empty.png"], "confidence": "high", "in_scope": True},
    ],
    "out_of_scope": ["The footer links point to an external site."],
    "coverage": {"pages": ["/"], "flows": ["save a name"], "viewports": ["1280x720", "390x844"]},
}

OTHER_CODEX = "#!/usr/bin/env bash\necho 'codex-cli 0.159.3'\n"


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def scrub(path):
    if not os.path.lexists(path):
        return

    def writable(function, target, _):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        function(target)
    shutil.rmtree(path, onerror=writable)


def tearDownModule():
    try:
        TEST_ROOT.rmdir()
    except OSError:
        pass


@unittest.skipUnless(sys.platform == "win32", "offline suite of the Windows checkout (the fake itself is portable)")
class PlatformLayerTest(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="p-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.plugin = self.root / "plugin"
        shutil.copytree(REPO / "skills/ask", self.plugin / "skills/ask",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.cli = self.plugin / "skills/ask/scripts/consult.py"
        self.project, self.base = self.root / "project", self.root / "base"
        self.records, self.requests, self.home = self.root / "records", self.root / "requests", self.root / "home"
        for directory in (self.project, self.base, self.requests, self.home):
            directory.mkdir()
        write(self.project / "index.html", "<h1>app</h1>")
        write(self.project / "server.py", "print('never run by the fake')\n")
        write(self.project / ".env", "SECRET=never-copied\n")
        write(self.project / ".stub/scenario.json", json.dumps({"records": str(self.records),
                                                                 "exec": {"reply": UI_REPLY}}))
        self.other = self.root / "other-codex"
        write(self.other / "codex", OTHER_CODEX)
        self.path_tail = os.environ["PATH"]
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CODEX_HOME": str(self.home / ".codex")}
        self.request = {"interaction": "exercise", "kind": "ui", "project": str(self.project),
                        "prompt": "Exercise type: UI exercise.\nExercise the app.",
                        "models": [{"model": "gpt-6-sol", "effort": "high"}],
                        "target_root": {"path": str(self.root / "targets"), "confirmed_by_user": True},
                        "app": ["127.0.0.1:15173", "127.0.0.1:18080"], "headed": False, "scope": "the save form",
                        "commands": {"start": [{"argv": ["python", "-I", "server.py"]}]}}

    # --- helpers ---

    def stage(self, fake_text=None, version=None):
        """`<plugin>/.eval-stub/` as run-evals.sh stages it (optionally a changed fake or stub version)."""
        stub = self.plugin / ".eval-stub"
        stub.mkdir()
        shutil.copy(STUB / "codex", stub / "codex")
        stub_py = (STUB / "codex-stub.py").read_text(encoding="utf-8")
        if version:
            stub_py = stub_py.replace('"codex-cli 0.0.0-stub\\n"', f'"{version}\\n"')
        write(stub / "codex-stub.py", stub_py)
        write(stub / "exercise_platform_fake.py",
              fake_text if fake_text is not None else (STUB / "exercise_platform_fake.py").read_text(encoding="utf-8"))
        return stub

    def path_with(self, *first):
        self.env["PATH"] = os.pathsep.join([*map(str, first), self.path_tail])

    def call(self, *args, platform="", timeout=120, expect_json=True):
        result = subprocess.run([sys.executable, "-c", BOOTSTRAP, str(self.cli), platform, *map(str, args)],
                                env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if not expect_json:
            return result
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def background(self, *args, platform=""):
        return subprocess.Popen([sys.executable, "-c", BOOTSTRAP, str(self.cli), platform, *map(str, args)],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def prepare(self, request=None, platform=""):
        path = self.requests / f"request-{time.monotonic_ns()}.json"
        path.write_text(json.dumps(self.request if request is None else request), encoding="utf-8")
        return self.call("prepare", path, "--base", self.base, platform=platform)

    def runs(self):
        parent = self.base / "ask-codex"
        return sorted(p.name for p in parent.iterdir()) if parent.exists() else []

    def violations(self):
        path = self.records / "violations.log"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def exec_count(self):
        sentinel = self.records / "exec.sentinel"
        return len(sentinel.read_text(encoding="utf-8").splitlines()) if sentinel.exists() else 0

    # --- I13: a non-Windows host without the fake ---

    def test_non_windows_host_without_the_fake_refuses_every_exercise_operation(self):
        self.path_with(STUB)
        refused = self.prepare(platform="linux")
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("Windows only", refused["reason"])
        self.assertEqual(self.runs(), [])
        for args in (("exercise-deps",), ("guard", self.base), ("app-start", self.base), ("finish", self.base)):
            with self.subTest(action=args[0]):
                result = self.call(*args, platform="linux")
                self.assertEqual(result["state"], "failed", result)
                self.assertIn("Windows only", result["reason"])
        self.assertEqual(self.exec_count(), 0)

    # --- I13: the fake present and the stub check passing ---

    def test_with_the_fake_validation_and_the_whole_lifecycle_run_through_the_cli(self):
        stub = self.stage()
        self.path_with(stub)
        deps = self.call("exercise-deps", platform="linux")
        self.assertEqual(deps["state"], "ready", deps)
        self.assertEqual(deps["codex_version"], "codex-cli 0.0.0-stub")
        self.assertEqual(deps["codex_tested_version"], "codex-cli 0.159.3")
        self.assertIs(deps["codex_untested"], True)
        # Validation is production code: two models and a non-loopback port are refused before anything exists.
        for change in ({"models": [{"model": "a", "effort": "high"}, {"model": "b", "effort": "high"}]},
                       {"app": ["192.168.1.5:8080"]},
                       {"target_root": {"path": str(self.root / "targets"), "confirmed_by_user": False}},
                       {"target_root": {"path": str(self.project / "inside"), "confirmed_by_user": True}}):
            with self.subTest(refused=sorted(change)):
                refused = self.prepare({**self.request, **change}, platform="linux")
                self.assertEqual(refused["state"], "failed", refused)
                self.assertEqual([r for r in self.runs() if r.startswith("run.")], [])
        ready = self.prepare(platform="linux")
        self.assertEqual(ready["state"], "prepared", ready)
        directory = Path(ready["directory"])
        plan = json.loads((directory / "plan.json").read_text(encoding="utf-8"))
        target = Path(plan["summary"]["target"])
        self.assertEqual(plan["summary"]["target_root"], str(self.root / "targets"), "the requested root is reported")
        self.assertFalse((self.root / "targets").exists(), "the fake never writes under the requested root")
        self.assertTrue((target / "index.html").is_file() and (target / ".stub/scenario.json").is_file())
        self.assertFalse((target / ".env").exists(), "the real copy's secret patterns apply")
        self.assertTrue((target / "evidence").is_dir())
        # The MCP guard (I6) ran against the stub with the target as cwd: mcp list and mcp get were called.
        listing = [json.loads(line) for line in (self.records / "mcp-list.log").read_text("utf-8").splitlines()]
        self.assertTrue(listing and all(Path(item["cwd"]) == target for item in listing))
        self.assertTrue((self.records / "mcp-get.log").exists())
        # A run before the guard and the app start is refused (production lifecycle checks).
        early = self.call("run", directory, platform="linux")
        self.assertEqual(early["state"], "failed", early)
        self.assertEqual(self.exec_count(), 0)
        self.assertFalse(target.exists(), "a launch check failure removes the target at once")
        settled = self.call("collect", directory, platform="linux")
        self.assertEqual(settled["state"], "failed", settled)
        self.assertFalse(directory.exists(), "collect of the failed run removes its run directory")

        ready = self.prepare(platform="linux")
        directory = Path(ready["directory"])
        target = Path(json.loads((directory / "plan.json").read_text(encoding="utf-8"))["summary"]["target"])
        guarded = self.call("guard", directory, "--result", self.requests / "guard.json", platform="linux")
        self.assertEqual(guarded["state"], "guard_passed", guarded)
        self.assertEqual(guarded["guard"]["source"], "ran")
        self.assertEqual(self.call("wait-result", self.requests / "guard.json", "--seconds", "0",
                                   platform="linux"), guarded)
        started = self.call("app-start", directory, "--result", self.requests / "app-start.json", platform="linux")
        self.assertEqual(started["state"], "app_started", started)
        self.assertEqual(self.call("app-start", directory, platform="linux")["state"], "failed", "never retried")
        self.assertEqual(self.call("run", directory, platform="linux")["state"], "finished")
        self.assertEqual(self.call("wait", directory, "--seconds", "5", platform="linux")["state"], "finished")
        collected = self.call("collect", directory, platform="linux")
        self.assertEqual(collected["state"], "collected", collected)
        self.assertEqual(collected["guard"]["source"], "ran")
        reply = collected["runs"][0]["reply"]
        self.assertEqual(reply["format"], "structured")
        self.assertNotIn("abcdefghijklmnop1234567890", json.dumps(reply), "I11: the collect side redacts")
        self.assertTrue(target.exists(), "collect keeps the target until finish (I12)")
        self.assertEqual(self.call("run", directory, platform="linux")["state"], "failed", "never replayed")
        argv = json.loads((self.records / "exec-argv.json").read_text(encoding="utf-8"))
        self.assertIn("--ignore-rules", argv)
        self.assertIn(Path(target).as_posix(), argv)
        self.assertTrue(any(a.startswith("mcp_servers.cdt_") and a.endswith('.default_tools_approval_mode="prompt"')
                            for a in argv))
        self.assertTrue(any(a.startswith("mcp_servers.cdt_") and "--headless" in a for a in argv))
        self.assertEqual(self.violations(), "")
        self.assertEqual(self.exec_count(), 1)
        finished = self.call("finish", directory, platform="linux")
        self.assertEqual(finished["state"], "finished", finished)
        self.assertFalse(target.exists())
        self.assertFalse(directory.exists())
        self.assertEqual(self.runs(), [], "the stand-in root went with the target")

    def test_the_fake_guard_and_app_start_follow_the_scenario(self):
        stub = self.stage()
        self.path_with(stub)
        scenario = json.loads((self.project / ".stub/scenario.json").read_text(encoding="utf-8"))
        for fake, expected in (({"guard": "cache"}, ("guard_passed", "cache")), ({"guard": "fail"}, ("failed", None))):
            with self.subTest(fake=fake):
                write(self.project / ".stub/scenario.json", json.dumps({**scenario, "exercise_fake": fake}))
                directory = Path(self.prepare(platform="linux")["directory"])
                guarded = self.call("guard", directory, platform="linux")
                self.assertEqual(guarded["state"], expected[0], guarded)
                if expected[1]:
                    self.assertEqual(guarded["guard"]["source"], expected[1])
                    self.assertEqual(self.call("finish", directory, platform="linux")["state"], "finished")
                else:
                    self.assertTrue(guarded["target_removed"])
        write(self.project / ".stub/scenario.json", json.dumps({**scenario, "exercise_fake": {"app_start": "fail"}}))
        directory = Path(self.prepare(platform="linux")["directory"])
        self.assertEqual(self.call("guard", directory, platform="linux")["state"], "guard_passed")
        failed = self.call("app-start", directory, platform="linux")
        self.assertEqual(failed["state"], "failed", failed)
        self.assertTrue(failed["target_removed"])
        self.assertIn("no Codex call was made", failed["reason"])
        self.assertEqual(self.runs(), [])
        self.assertEqual(self.exec_count(), 0)

    # --- I13: `.eval-stub/` present but the stub check fails ---

    def assert_refused_everywhere(self, platform):
        directory = None
        refused = self.prepare(platform=platform)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn(".eval-stub", refused["reason"])
        self.assertEqual(self.runs(), [])
        for args in (("exercise-deps",), ("guard", self.base), ("app-start", self.base), ("finish", self.base),
                     ("target-create", self.requests / "none.json")):
            with self.subTest(action=args[0], platform=platform):
                result = self.call(*args, platform=platform)
                self.assertEqual(result["state"], "failed", result)
                self.assertIn(".eval-stub", result["reason"])
        self.assertEqual(self.exec_count(), 0)
        return directory

    def test_eval_stub_with_a_non_stub_codex_refuses_every_exercise_operation(self):
        stub = self.stage()
        self.path_with(self.other, stub)
        for platform in ("", "linux"):
            self.assert_refused_everywhere(platform)
        # A consultation is not an exercise operation: model resolution still works.
        resolve = self.requests / "resolve.json"
        resolve.write_text(json.dumps({"models": [], "effort": None, "session": {}}), encoding="utf-8")
        self.assertEqual(self.call("resolve", resolve)["state"], "resolved")

    def test_eval_stub_codex_reporting_another_version_refuses(self):
        stub = self.stage(version="codex-cli 0.159.3")
        self.path_with(stub)
        self.assert_refused_everywhere("linux")

    def test_eval_stub_codex_absent_from_path_refuses(self):
        self.stage()
        self.path_with(STUB)  # a stub codex, but not the one in <plugin root>/.eval-stub
        self.assert_refused_everywhere("")

    def test_a_fake_that_does_not_replace_exactly_the_layer_refuses(self):
        text = (STUB / "exercise_platform_fake.py").read_text(encoding="utf-8")
        cut = text.replace('"run_alive": run_alive}', '}')
        self.assertNotEqual(cut, text)
        stub = self.stage(fake_text=cut)
        self.path_with(stub)
        refused = self.prepare(platform="linux")
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("does not replace exactly", refused["reason"])
        self.assertEqual(self.runs(), [])

    def test_selection_reads_no_environment_variable(self):
        for path in (REPO / "skills/ask/scripts/platform_layer.py", REPO / "skills/ask/scripts/exercise.py"):
            with self.subTest(module=path.name):
                source = path.read_text(encoding="utf-8")
                reads = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Attribute) and
                         n.attr in ("environ", "getenv", "environb", "putenv")]
                self.assertEqual(reads, [])
                self.assertNotIn("getenv", source)

    # --- C4 review item 30: a background operation leaves its result in a file ---

    def test_result_file_and_wait_result(self):
        stub = self.stage()
        self.path_with(stub)
        directory = Path(self.prepare(platform="linux")["directory"])
        result_file = self.requests / "guard-result.json"
        process = self.background("guard", directory, "--result", result_file, platform="linux")
        waited = self.call("wait-result", result_file, "--seconds", "30", platform="linux")
        process.communicate(timeout=60)
        self.assertEqual(waited["state"], "guard_passed", waited)
        # An existing result file is never overwritten, and the operation does not run.
        again = self.call("app-start", directory, "--result", result_file, platform="linux")
        self.assertEqual(again["state"], "failed", again)
        self.assertIn("already exists", again["reason"])
        self.assertFalse((directory / "supervisor-config.json").exists(), "app-start did not run")
        relative = self.call("app-start", directory, "--result", "relative.json", platform="linux")
        self.assertEqual(relative["state"], "failed")
        self.assertFalse((directory / "supervisor-config.json").exists())
        missing = self.call("wait-result", self.requests / "never.json", "--seconds", "0", platform="linux")
        self.assertEqual(missing["state"], "missing")
        lost = write(self.requests / "lost.json", json.dumps({"state": "pending", "action": "app-start",
                                                              "started_at": time.time() - 100, "bound_seconds": 50}))
        self.assertEqual(self.call("wait-result", lost, "--seconds", "0")["state"], "lost")
        pending = write(self.requests / "pending.json", json.dumps({"state": "pending", "action": "guard",
                                                                    "started_at": time.time(), "bound_seconds": 3600}))
        waited = self.call("wait-result", pending, "--seconds", "1")
        self.assertEqual(waited["state"], "pending")
        self.assertEqual(self.call("wait-result", pending, "--seconds", "61")["state"], "failed")
        usage = self.call("run", directory, "--result", self.requests / "run.json", expect_json=False)
        self.assertEqual(usage.returncode, 2, "--result applies to the long operations only")
        self.assertFalse((self.requests / "run.json").exists())
        self.assertEqual(self.call("finish", directory, platform="linux")["state"], "finished")

    def test_app_start_result_bound_covers_its_install_commands(self):
        stub = self.stage()
        self.path_with(stub)
        request = {**self.request, "commands": {"install": [{"argv": ["python", "-c", "0"]}] * 2,
                                                "start": [{"argv": ["python", "server.py"]}]}}
        directory = Path(self.prepare(request, platform="linux")["directory"])
        sys.path.insert(0, str(self.plugin / "skills/ask/scripts"))
        try:
            import consult
            import supervisor
            bound = consult.result_bound("app-start", directory)
            timing = supervisor.TIMING
        finally:
            sys.path.pop(0)
            for name in [n for n, m in sys.modules.items()
                         if str(getattr(m, "__file__", "") or "").startswith(str(self.plugin))]:
                del sys.modules[name]
        # app-start's own wait (supervisor.wait_started) is install_timeout per install + start_timeout + 60 s.
        self.assertGreater(bound, timing["install_timeout"] * 2 + timing["start_timeout"] + 60)
        self.assertEqual(consult.RESULT_BOUNDS["guard"], 3600)
        self.assertEqual(self.call("finish", directory, platform="linux")["state"], "finished")


class CodexNoticeTest(unittest.TestCase):
    """N10: the tested codex-cli version and the comparison the skill acts on."""

    def test_notice(self):
        sys.path.insert(0, str(REPO / "skills/ask/scripts"))
        try:
            import guard
        finally:
            sys.path.pop(0)
        self.assertEqual(guard.TESTED_CODEX_CLI, "codex-cli 0.159.3")
        self.assertEqual(guard.codex_notice("codex-cli 0.159.3\n"),
                         {"codex_tested_version": "codex-cli 0.159.3", "codex_untested": False})
        for other in ("codex-cli 0.160.0", "codex-cli 0.0.0-stub", ""):
            self.assertIs(guard.codex_notice(other)["codex_untested"], True)


if __name__ == "__main__":
    unittest.main()
