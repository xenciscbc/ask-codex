"""Public consultation CLI integration tests; never calls a real Codex service."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "skills/ask/scripts/consult.py"


class ConsultationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-codex-test-", dir=REPO / ".scratch")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project's space"
        (self.project / ".stub").mkdir(parents=True)
        self.scenario({})
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CODEX_HOME": str(self.home / ".codex"), "TMP": str(self.root), "TEMP": str(self.root),
                    "PATH": str(REPO / "evals/_harness/stub") + os.pathsep + os.environ["PATH"]}
        self.request = {"project": str(self.project), "prompt": "Consultation question: $(touch never) ' evidence",
                        "models": [{"model": "gpt-6-sol", "effort": "high"}], "confirmations": {}}

    def scenario(self, value):
        (self.project / ".stub/scenario.json").write_text(json.dumps(value), encoding="utf-8")

    def call(self, *args):
        result = subprocess.run([sys.executable, str(CLI), *map(str, args)], env=self.env,
                                capture_output=True, text=True, encoding="utf-8", timeout=75)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def prepare(self):
        request = self.root / "request.json"
        request.write_text(json.dumps(self.request), encoding="utf-8")
        return self.call("prepare", request, "--base", self.root)

    def test_single_consultation_collects_reply_then_cleans(self):
        prepared = self.prepare()
        self.assertEqual(prepared["state"], "prepared", prepared)
        self.assertEqual(prepared["summary"]["allowed_servers"], [])
        self.assertEqual(self.call("run", prepared["directory"])["state"], "finished")
        ended = self.call("stop", prepared["directory"])
        self.assertEqual(ended["state"], "finished", ended)
        self.assertEqual(ended["stops"], [])
        collected = self.call("collect", prepared["directory"])
        self.assertEqual(collected["runs"][0]["state"], "completed")
        self.assertEqual(collected["runs"][0]["reply"]["format"], "structured")
        self.assertFalse(Path(prepared["directory"]).exists())
        sent = (self.project / ".stub/exec-stdin.txt").read_text(encoding="utf-8")
        self.assertEqual(sent, self.request["prompt"])
        self.assertEqual((self.project / ".stub/violations.log").read_text(), "")

    def test_unicode_reply_is_delivered_with_legacy_stdout_encoding(self):
        summary = "Unicode reply: \U0001f680 \u4e2d\u6587"
        self.scenario({"exec": {"reply": {"summary": summary, "claims": [], "open_questions": []}}})
        ready = self.prepare()
        self.call("run", ready["directory"])
        result = subprocess.run([sys.executable, str(CLI), "collect", ready["directory"]],
                                env={**self.env, "PYTHONIOENCODING": "cp950"},
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode("ascii", errors="replace"))
        reply = json.loads(result.stdout)["runs"][0]["reply"]
        self.assertEqual(reply["content"]["summary"], summary)
        self.assertFalse(Path(ready["directory"]).exists())

    def test_failed_reply_delivery_retains_run_for_collection_retry(self):
        summary = "reply still recoverable " * 10000
        self.scenario({"exec": {"reply": {"summary": summary, "claims": [], "open_questions": []}}})
        ready = self.prepare()
        self.call("run", ready["directory"])
        with subprocess.Popen([sys.executable, str(CLI), "collect", ready["directory"]],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            process.stdout.close()  # The caller disappears before receiving the reply.
            error = process.stderr.read()
            self.assertNotEqual(process.wait(timeout=10), 0, error)
        self.assertTrue(Path(ready["directory"]).exists(), "undelivered reply must remain recoverable")
        collected = self.call("collect", ready["directory"])
        self.assertEqual(collected["runs"][0]["reply"]["content"]["summary"], summary)
        self.assertFalse(Path(ready["directory"]).exists())
        self.assertEqual(len(list((self.project / ".stub/exec-calls").glob("*.json"))), 1)

    def test_cleanup_failure_preserves_delivered_reply_and_reports_location(self):
        ready = self.prepare()
        self.call("run", ready["directory"])
        bootstrap = """
import pathlib, runpy, shutil, sys
sys.argv.pop(0)
original = shutil.rmtree
def remove(path, *args, **kwargs):
    if pathlib.Path(path) == pathlib.Path(sys.argv[2]) / '0':
        raise PermissionError('test locked run files')
    return original(path, *args, **kwargs)
shutil.rmtree = remove
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-c", bootstrap, str(CLI), "collect", ready["directory"]],
                                env=self.env, capture_output=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        collected = json.loads(result.stdout)
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        failure = json.loads(result.stderr)
        self.assertEqual(failure["state"], "cleanup_failed", failure)
        self.assertEqual(failure["retained_location"], ready["directory"])
        self.assertEqual(self.call("cleanup", ready["directory"])["state"], "cleaned")

    def test_invalid_project_policy_does_not_fall_back_to_wider_user_policy(self):
        (self.home / ".claude").mkdir()
        (self.home / ".claude/ask-codex.json").write_text('{"mcp_policy":"minimal-deny"}')
        (self.project / ".claude").mkdir()
        (self.project / ".claude/ask-codex.local.json").write_text('{broken')
        result = self.prepare()
        self.assertEqual(result["state"], "failed", result)
        self.assertIn("ask-codex.local.json", result["reason"])
        self.assertFalse((self.project / ".stub/exec.sentinel").exists())

    def test_project_definition_confirmation_does_not_grant_use(self):
        (self.project / ".codex").mkdir()
        (self.project / ".codex/config.toml").write_text('[mcp_servers.comfyui]\ncommand="changed"\n')
        self.scenario({"project_overrides": {"comfyui": {"transport": {"command": "changed"}}}})
        pending = self.prepare()
        self.assertEqual(pending["state"], "confirmation_required", pending)
        self.assertFalse((self.project / ".stub/mcp-list.log").exists())
        self.request["confirmations"] = {item["id"]: "allow" for item in pending["pending"]}
        ready = self.prepare()
        self.assertEqual(ready["state"], "prepared", ready)
        self.assertEqual(ready["summary"]["allowed_servers"], [])

    def test_minimal_deny_and_layered_allowlist_resolve_expected_servers(self):
        (self.home / ".claude").mkdir()
        policy = self.home / ".claude/ask-codex.json"
        policy.write_text('{"mcp_policy":"minimal-deny"}')
        ready = self.prepare()
        self.assertEqual(ready["summary"]["allowed_servers"], ["blender", "comfyui", "pencil"])
        policy.write_text('{"mcp_policy":"allowlist","mcp_allow":["comfyui"]}')
        (self.project / ".claude").mkdir()
        (self.project / ".claude/ask-codex.local.json").write_text('{"mcp_allow":[]}')
        ready = self.prepare()
        self.assertEqual(ready["summary"]["allowed_servers"], [])
        self.assertEqual(ready["summary"]["policy"], "allowlist")

    def test_dotted_server_disabled_and_guard_mismatch_rejected(self):
        self.scenario({"project_extra": [{"name": "foo.bar"}]})
        ready = self.prepare()
        self.assertEqual(ready["state"], "prepared", ready)
        self.assertEqual((self.project / ".stub/violations.log").read_text(), "")
        self.scenario({"guard_fails": True})
        self.assertEqual(self.prepare()["state"], "failed")

    def test_plugin_provided_servers_are_disabled_with_valid_overrides(self):
        self.scenario({"project_extra": [{"name": "codex_app", "enabled": False, "plugin": True},
                                         {"name": "plugin_tool", "plugin": True}]})
        ready = self.prepare()
        self.assertEqual(ready["state"], "prepared", ready)
        self.assertEqual(ready["summary"]["allowed_servers"], [])
        self.assertEqual((self.project / ".stub/violations.log").read_text(), "")
        self.call("run", ready["directory"])
        argv = json.loads((self.project / ".stub/exec-argv.json").read_text(encoding="utf-8"))
        override = next(v for v in argv if v.startswith("mcp_servers={"))
        self.assertIn('"plugin_tool"={command="ask-codex-disabled",enabled=false}', override)
        self.assertNotIn("codex_app", override)

    def test_changed_definition_invalidates_session_use_authorization(self):
        (self.home / ".claude").mkdir()
        (self.home / ".claude/ask-codex.json").write_text('{"mcp_allow":["comfyui"]}')
        self.scenario({"project_overrides": {"comfyui": {"transport": {"command": "changed"}}}})
        pending = self.prepare()
        self.assertEqual(pending["state"], "confirmation_required")
        self.request["confirmations"] = {item["id"]: "allow" for item in pending["pending"]}
        ready = self.prepare()
        self.assertEqual(ready["summary"]["allowed_servers"], ["comfyui"])
        self.assertEqual(self.prepare()["state"], "prepared")
        self.scenario({"project_overrides": {"comfyui": {"transport": {"command": "new-command"}}}})
        self.assertEqual(self.prepare()["state"], "confirmation_required")
        self.assertEqual(self.call("run", ready["directory"])["state"], "confirmation_required")
        self.assertFalse((self.project / ".stub/exec.sentinel").exists())

    def test_readable_invalid_schema_is_unstructured(self):
        self.scenario({"exec": {"reply": {"summary": "x", "claims": "wrong", "open_questions": []}}})
        ready = self.prepare()
        self.call("run", ready["directory"])
        result = self.call("collect", ready["directory"])
        self.assertEqual(result["runs"][0]["reply"]["format"], "unstructured", result)

    def test_wait_reports_unstarted_run_without_sleeping(self):
        self.env["EVAL_ASK_CODEX_TIMEOUT_MINUTES"] = "0"
        ready = self.prepare()
        before = time.monotonic()
        waiting = self.call("wait", ready["directory"], "--seconds", "1")
        self.assertEqual(waiting["state"], "prepared", waiting)
        self.assertLess(time.monotonic() - before, 1)
        self.assertEqual(waiting["timer"]["interval_minutes"], 30)
        self.assertEqual(waiting["timer"]["source"], "ignored_override")

    def test_parallel_mixed_result_keeps_success_and_no_retry(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        self.scenario({"exec": {"by_model": {"gpt-6-astra": {"mode": "fail"}}}})
        ready = self.prepare()
        self.call("run", ready["directory"])
        self.assertEqual(self.call("run", ready["directory"])["state"], "failed")
        result = self.call("collect", ready["directory"])
        self.assertEqual([r["state"] for r in result["runs"]], ["completed", "failed"], result)
        self.assertNotIn("reply", result["runs"][1])
        self.assertEqual(len(list((self.project / ".stub/exec-calls").glob("*.json"))), 2)

    def test_parallel_file_preparation_failure_starts_neither_model(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        ready = self.prepare()
        (Path(ready["directory"]) / "1").write_text("occupied")
        result = self.call("run", ready["directory"])
        self.assertEqual(result["state"], "failed", result)
        self.assertFalse((self.project / ".stub/exec.sentinel").exists())
        self.assertEqual(self.call("cleanup", ready["directory"])["state"], "cleaned")

    def test_wrapper_receipt_survives_loss_of_supervisor_receipt(self):
        ready = self.prepare()
        self.call("run", ready["directory"])
        (Path(ready["directory"]) / "0/result.json").unlink()
        collected = self.call("collect", ready["directory"])
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        self.assertFalse(Path(ready["directory"]).exists())

    def test_partial_parallel_launch_failure_stops_started_consultation(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 20, "event_every_s": 0.2}})
        self.env["ASK_CODEX_STOP_WINDOW_S"] = "1"
        ready = self.prepare()
        # Inject an OS process-spawn failure at the subprocess boundary, after
        # the first real stub consultation emits an event. Preflight is real.
        bootstrap = """
import pathlib, runpy, subprocess, sys, time
sys.argv.pop(0)
original = subprocess.Popen
launches = 0
def spawn(*args, **kwargs):
    global launches
    if kwargs.get('stdin') is not None:
        launches += 1
        if launches == 2:
            deadline = time.monotonic() + 15
            events = pathlib.Path(sys.argv[2]) / '0/events.jsonl'
            while (not events.exists() or not events.stat().st_size) and time.monotonic() < deadline:
                time.sleep(.1)
            raise OSError('injected spawn failure')
    return original(*args, **kwargs)
subprocess.Popen = spawn
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-c", bootstrap, str(CLI), "run", ready["directory"]],
                                env=self.env, capture_output=True, text=True, timeout=75)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["state"], "launch_failed", outcome)
        self.assertEqual(outcome["directory"], ready["directory"])
        collected = self.call("collect", ready["directory"])
        self.assertIn(collected["runs"][0]["state"], ("stopped", "stop_unconfirmed"), collected)
        self.assertEqual(collected["runs"][1]["state"], "failed", collected)
        self.assertNotIn("reply", collected["runs"][0])
        self.assertEqual(len(list((self.project / ".stub/exec-calls").glob("*.json"))), 1)

    def test_missing_stop_receipt_retains_other_success_without_attributing_stopped_reply(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        ready = self.prepare()
        self.call("run", ready["directory"])
        (Path(ready["directory"]) / "1/stop-request").touch()
        collected = self.call("collect", ready["directory"])
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        self.assertEqual(collected["runs"][1]["state"], "stop_unconfirmed", collected)
        self.assertNotIn("reply", collected["runs"][1])
        self.assertTrue(Path(collected["retained_location"]).exists())
        self.assertEqual(self.call("cleanup", ready["directory"])["state"], "failed")

    def test_completion_receipt_failure_stops_other_parallel_worker(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        self.scenario({"exec": {"by_model": {
            "gpt-6-astra": {"mode": "slow-active", "duration_s": 20, "event_every_s": 0.1}}}})
        self.env["ASK_CODEX_STOP_WINDOW_S"] = "1"
        ready = self.prepare()
        bootstrap = """
import pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(sys.argv[1]).parent))
import consult
original = consult.write_json
def write(path, data):
    if pathlib.Path(path).name == 'result.json':
        events = pathlib.Path(sys.argv[2]) / '1/events.jsonl'
        deadline = time.monotonic() + 15
        while (not events.exists() or not events.stat().st_size) and time.monotonic() < deadline:
            time.sleep(.1)
        raise PermissionError('injected completion receipt failure')
    original(path, data)
consult.write_json = write
sys.argv = sys.argv[1:]
consult.main()
"""
        result = subprocess.run([sys.executable, "-c", bootstrap, str(CLI), "run", ready["directory"]],
                                env=self.env, capture_output=True, text=True, timeout=75)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["state"], "launch_failed", outcome)
        self.assertEqual(outcome["stop_requested"], ["1"], outcome)
        self.assertEqual(len(outcome["termination"]["stops"]), 1)
        directory = Path(ready["directory"])
        self.assertTrue((directory / "1/stop-request").exists())
        self.assertTrue((directory / "1/launcher-result.json").exists(), "stop must settle the stub launcher")
        events = directory / "1/events.jsonl"
        size = events.stat().st_size
        time.sleep(.4)
        self.assertEqual(events.stat().st_size, size, "stopped stub must not emit further events")
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        self.assertIn(collected["runs"][1]["state"], ("stopped", "stop_unconfirmed"), collected)
        self.assertNotIn("reply", collected["runs"][1])
        self.assertEqual(len(list((self.project / ".stub/exec-calls").glob("*.json"))), 2)

    def test_late_second_launch_failure_preserves_first_completed_opinion(self):
        self.request["models"].append({"model": "gpt-6-astra", "effort": "medium"})
        ready = self.prepare()
        bootstrap = """
import pathlib, runpy, subprocess, sys, time
sys.argv.pop(0)
original = subprocess.Popen
launches = 0
def spawn(*args, **kwargs):
    global launches
    if kwargs.get('stdin') is not None:
        launches += 1
        if launches == 2:
            receipt = pathlib.Path(sys.argv[2]) / '0/launcher-result.json'
            deadline = time.monotonic() + 20
            while not receipt.exists() and time.monotonic() < deadline:
                time.sleep(.1)
            raise OSError('injected late spawn failure')
    return original(*args, **kwargs)
subprocess.Popen = spawn
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        result = subprocess.run([sys.executable, "-c", bootstrap, str(CLI), "run", ready["directory"]],
                                env=self.env, capture_output=True, text=True, timeout=75)
        self.assertEqual(json.loads(result.stdout)["state"], "launch_failed", result.stdout)
        collected = self.call("collect", ready["directory"])
        self.assertEqual([r["state"] for r in collected["runs"]], ["completed", "failed"], collected)
        self.assertFalse(Path(ready["directory"]).exists())

    def test_wait_rejects_duration_above_tool_limit(self):
        ready = self.prepare()
        result = self.call("wait", ready["directory"], "--seconds", "1800")
        self.assertEqual(result["state"], "failed")

    def test_policy_decline_uses_user_policy_and_definition_decline_stops(self):
        (self.project / ".claude").mkdir()
        (self.project / ".claude/ask-codex.local.json").write_text('{"mcp_policy":"minimal-deny"}')
        pending = self.prepare()
        self.request["confirmations"] = {p["id"]: "deny" for p in pending["pending"]}
        ready = self.prepare()
        self.assertEqual(ready["summary"]["allowed_servers"], [])
        (self.project / ".codex").mkdir()
        (self.project / ".codex/config.toml").write_text('mcp_servers."foo.bar".command="test"')
        pending = self.prepare()
        self.assertEqual(pending["state"], "confirmation_required")
        self.request["confirmations"].update({p["id"]: "deny" for p in pending["pending"]})
        denied = self.prepare()
        self.assertEqual(denied["state"], "failed")
        self.assertIn("foo.bar", denied["reason"])

    def test_invalid_models_and_policy_types_do_not_execute(self):
        for models in ([], [{"model": "sol;echo pwned", "effort": "high"}],
                       [{"model": "gpt-6-sol", "effort": "ultra"}], self.request["models"] * 2):
            self.request["models"] = models
            self.assertEqual(self.prepare()["state"], "failed")
        self.request["models"] = [{"model": "gpt-6-sol", "effort": "high"}]
        (self.project / ".claude").mkdir()
        for value in ('[]', '{"mcp_allow":"comfyui"}', '{"mcp_allow":[2]}', '{"mcp_policy":"unknown"}'):
            (self.project / ".claude/ask-codex.local.json").write_text(value)
            self.assertEqual(self.prepare()["state"], "failed")
        self.assertFalse((self.project / ".stub/exec.sentinel").exists())

    def test_sensitive_definition_values_never_appear_in_confirmation_output(self):
        (self.project / ".codex").mkdir()
        (self.project / ".codex/config.toml").write_text('[mcp_servers.comfyui]\ncommand="server"\n[mcp_servers.comfyui.env]\nAPI_KEY="secret-for-test"\n')
        output = self.prepare()
        self.assertEqual(output["state"], "confirmation_required")
        self.assertNotIn("secret-for-test", json.dumps(output))

    def test_prepared_run_can_be_discarded_but_arbitrary_directory_cannot(self):
        prepared = self.prepare()
        self.assertEqual(self.call("cleanup", self.root)["state"], "failed")
        self.assertEqual(self.call("cleanup", prepared["directory"])["state"], "cleaned")
        self.assertFalse(Path(prepared["directory"]).exists())

    def test_foreground_wait_collects_background_completion(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 2, "event_every_s": 0.2}})
        ready = self.prepare()
        with subprocess.Popen([sys.executable, str(CLI), "run", ready["directory"]],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            deadline = time.monotonic() + 25
            while True:
                status = self.call("wait", ready["directory"], "--seconds", "1")
                if status["state"] == "finished":
                    break
                self.assertLess(time.monotonic(), deadline, status)
            process.communicate(timeout=5)
        result = self.call("collect", ready["directory"])
        self.assertEqual(result["runs"][0]["state"], "completed", result)

    def test_check_intervals_repeat_after_continue_and_keep_history(self):
        self.env["EVAL_ASK_CODEX_TIMEOUT_MINUTES"] = "1"
        self.env["ASK_CODEX_STOP_WINDOW_S"] = "1"
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 20, "event_every_s": 0.2}})
        ready = self.prepare()
        bootstrap = """
import pathlib, runpy, sys, time
sys.argv.pop(0)
wallclock = time.time
time.time = lambda: wallclock() + 65
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
runpy.run_path(sys.argv[0], run_name='__main__')
"""
        with subprocess.Popen([sys.executable, str(CLI), "run", ready["directory"]],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            try:
                for _ in range(15):
                    status = self.call("wait", ready["directory"], "--seconds", "1")
                    if status.get("runs", [{}])[0].get("last_event"):
                        break
                for _ in range(2):
                    result = subprocess.run([sys.executable, "-c", bootstrap, str(CLI), "wait",
                                             ready["directory"], "--seconds", "0"],
                                            env=self.env, capture_output=True, text=True, timeout=5)
                    check = json.loads(result.stdout)
                    self.assertEqual(check["state"], "decision_required", check)
                    self.assertEqual(check["recommendation"], "stop")
                    self.assertEqual(check["timer"]["interval_minutes"], 1)
                    self.call("continue", ready["directory"])
            finally:
                self.call("stop", ready["directory"], "--offered", "wait,stop")
                process.communicate(timeout=35)
        collected = self.call("collect", ready["directory"])
        self.assertEqual(len(collected["checks"]), 2, collected)
        self.assertEqual(collected["runs"][0]["stop"]["options_offered"], ["wait", "stop"])

    def test_stop_collect_never_attributes_stopped_reply(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 20, "event_every_s": 0.2}})
        self.env["ASK_CODEX_STOP_WINDOW_S"] = "1"
        ready = self.prepare()
        with subprocess.Popen([sys.executable, str(CLI), "run", ready["directory"]],
                              env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            for _ in range(15):
                status = self.call("wait", ready["directory"], "--seconds", "1")
                if status.get("runs", [{}])[0].get("last_event"):
                    break
            stopped = self.call("stop", ready["directory"], "--offered", "none")
            self.assertIn(stopped["state"], ("stopped", "stop_unconfirmed"), stopped)
            process.communicate(timeout=35)
        result = self.call("collect", ready["directory"])
        self.assertNotIn("reply", result["runs"][0])
        self.assertEqual(result["runs"][0]["stop"].get("options_offered"), [])
        if stopped["state"] == "stop_unconfirmed":
            self.assertTrue(Path(result["retained_location"]).exists())
            self.assertEqual(self.call("cleanup", ready["directory"])["state"], "failed")


if __name__ == "__main__":
    unittest.main()
