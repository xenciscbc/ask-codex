"""The app's processes under the exercise supervisor (plan `.scratch/exercise-skills/plan.md` claim C4, ticket 04:
I2 post-install condition, I3 precondition, I8, I12 bounds and finish precondition, I15, U10; C2 follow-ups 1 and 7).

Offline at Seam 1: the public CLI with the Codex stub and real fake-app processes (long-running listeners started by
the supervisor from the disposable target). Never calls a real Codex service and never starts Chrome. Every test
works in a fresh directory under the test root (`D:\\tmp\\ask-codex-tests`, outside any repository), removed after;
processes are only ever ended through their recorded identity (PID + creation time), never by name or port.

Seams are in-process only (plan I13): the CLI runs through exercise_run_test's bootstrap (`browser.local_app_data`,
the install verification and the guard pass patched in the CLI process); timing is substituted by patching
`supervisor.TIMING` in the app-start call, which writes it into the supervisor's config; one test substitutes
`supervisor.command` to run the supervisor through a bootstrap that fixes its job name.
"""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exercise_run_test as base  # noqa: E402  (helpers only; its tests are not collected here)

SCRIPTS = base.SCRIPTS
TEST_ROOT = base.TEST_ROOT
REPLY = base.UI_REPLY

# The fake app: python fakeapp.py <notes directory> <mode> [arguments]. Every process writes a note
# <notes>/<role>-<pid>.json so the test knows each PID the app started.
FAKE_APP = r'''
import ctypes, json, os, socket, struct, subprocess, sys, threading, time
from ctypes import wintypes

NOTES, MODE, ARGS = sys.argv[1], sys.argv[2], sys.argv[3:]
ME = [sys.executable, os.path.abspath(__file__), NOTES]

def note(role, **extra):
    with open(os.path.join(NOTES, f"{role}-{os.getpid()}.json"), "w") as f:
        json.dump({"pid": os.getpid(), "role": role, **extra}, f)

def accept(sock):
    while True:
        try:
            connection, _ = sock.accept()
        except OSError:
            return
        connection.close()

def listen(specs):
    for spec in specs:
        host, port = spec.rsplit(":", 1)
        sock = socket.socket(socket.AF_INET6 if ":" in host else socket.AF_INET)
        sock.bind((host, int(port)))
        sock.listen(16)
        threading.Thread(target=accept, args=(sock,), daemon=True).start()
    print("listening on " + " ".join(specs), flush=True)

def forever():
    while True:
        time.sleep(3600)

def handles():
    """Job handles and socket ports among this process's own handles (NtQueryInformationProcess class 51)."""
    nt, k = ctypes.WinDLL("ntdll"), ctypes.WinDLL("kernel32")
    k.GetCurrentProcess.restype = wintypes.HANDLE
    nt.NtQueryInformationProcess.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                             ctypes.POINTER(wintypes.ULONG)]
    nt.NtQueryObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.ULONG,
                                 ctypes.POINTER(wintypes.ULONG)]
    size = 1 << 16
    while True:
        buffer, needed = ctypes.create_string_buffer(size), wintypes.ULONG()
        status = nt.NtQueryInformationProcess(k.GetCurrentProcess(), 51, buffer, size, ctypes.byref(needed))
        if status & 0xFFFFFFFF == 0:
            break
        if status & 0xFFFFFFFF != 0xC0000004 or size > 1 << 24:
            raise SystemExit(f"handle query failed {status & 0xFFFFFFFF:x}")
        size *= 4
    count = struct.unpack_from("<Q", buffer.raw, 0)[0]
    jobs, ports, total = 0, [], 0
    for i in range(count):
        value = struct.unpack_from("<Q", buffer.raw, 16 + i * 40)[0]
        info = ctypes.create_string_buffer(4096)
        if nt.NtQueryObject(value, 2, info, 4096, None) & 0xFFFFFFFF:
            continue
        total += 1
        length, pointer = struct.unpack_from("<H", info.raw, 0)[0], struct.unpack_from("<Q", info.raw, 8)[0]
        kind = ctypes.wstring_at(pointer, length // 2) if pointer else ""
        if kind == "Job":
            jobs += 1
        elif kind == "File":
            try:
                sock = socket.socket(fileno=value)
            except OSError:
                continue
            try:
                ports.append(sock.getsockname()[1])
            except OSError:
                pass
            finally:
                sock.detach()
    return {"jobs": jobs, "socket_ports": ports, "handles": total}

if MODE == "listen":                      # listen <host:port> ...
    note("listen")
    listen(ARGS)
    forever()
elif MODE == "first-child":               # spawn a listening child at the first instruction, then wait
    child = subprocess.Popen([*ME, "listen", *ARGS])
    note("first-child", child=child.pid)
    forever()
elif MODE == "middle":                    # spawn a listening grandchild and exit at once
    subprocess.Popen([*ME, "listen", *ARGS], creationflags=0x8)
    note("middle")
elif MODE == "never":                     # print, never listen
    note("never")
    print("starting the server ...", flush=True)
    sys.stderr.write("warning: waiting for a database that never comes\n")
    sys.stderr.flush()
    forever()
elif MODE == "fail":                      # fail at once with output
    note("fail")
    print("booting", flush=True)
    sys.stderr.write("fatal: cannot read config/app.toml\n")
    raise SystemExit(3)
elif MODE == "junction":                  # junction <link> <target>: an install step creating a link
    import _winapi
    _winapi.CreateJunction(ARGS[1], ARGS[0])
    note("junction")
elif MODE == "probe":                     # report inherited handles, then listen
    note("probe", **handles())
    listen(ARGS)
    forever()
elif MODE == "listen-link":               # listen, then create a junction <link> -> <target> in the target
    import _winapi
    note("listen")
    listen(ARGS[2:])
    _winapi.CreateJunction(ARGS[1], ARGS[0])
    forever()
'''

_k32 = ctypes.WinDLL("kernel32", use_last_error=True) if sys.platform == "win32" else None
if _k32:
    _k32.OpenProcess.restype = wintypes.HANDLE
    _k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    _k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(ctypes.c_uint64)] * 4
    _k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    _k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]


def created_at(pid):
    """Creation time of a running process (the test's own record of an identity), or None."""
    handle = _k32.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        return times[0].value if _k32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]) else None
    finally:
        _k32.CloseHandle(handle)


def alive(pid, created):
    handle = _k32.OpenProcess(0x1000 | 0x100000, False, pid)
    if not handle:
        return False
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        if not _k32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]) or times[0].value != created:
            return False
        return _k32.WaitForSingleObject(handle, 0) != 0
    finally:
        _k32.CloseHandle(handle)


def kill(pid, created):
    """End a process this test started or recorded, by its identity (never by name or port)."""
    handle = _k32.OpenProcess(0x1000 | 0x100000 | 0x1, False, pid)
    if not handle:
        return
    try:
        times = [ctypes.c_uint64() for _ in range(4)]
        if _k32.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]) and times[0].value == created:
            _k32.TerminateProcess(handle, 1)
            _k32.WaitForSingleObject(handle, 10000)
    finally:
        _k32.CloseHandle(handle)


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def answers(port, host="127.0.0.1"):
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except OSError:
        return False


def bindable(port):
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_until(condition, timeout, message):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError(message)
        time.sleep(0.2)


def timing(**values):
    return "import supervisor\nsupervisor.TIMING.update(" + json.dumps(values) + ")\n"


def tearDownModule():
    try:
        TEST_ROOT.rmdir()
    except OSError:
        pass


@unittest.skipUnless(sys.platform == "win32", "the exercise platform layer is Windows only (plan I13)")
class AppTestBase(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="a-", dir=TEST_ROOT))
        self.project, self.targets = self.root / "project", self.root / "targets"
        self.base, self.records, self.requests = self.root / "base", self.root / "records", self.root / "requests"
        self.sentinel, self.local, self.home = self.root / "sentinel", self.root / "localappdata", self.root / "home"
        self.notes = self.root / "notes"
        for directory in (self.project, self.targets, self.base, self.requests, self.sentinel, self.home, self.notes):
            directory.mkdir()
        self.identities = []  # (pid, created) of every process this test may leave; ended in cleanup
        self.addCleanup(base.scrub, self.root)
        self.addCleanup(self.end_leftovers)
        base.write(self.sentinel / "keep.txt", "sentinel content")
        base.write(self.project / "index.html", "<h1>app</h1>")
        base.write(self.project / "fakeapp.py", FAKE_APP)
        base.write(self.local.joinpath(*base.ENTRY), "// fake entry script, never run")
        self.node = base.write(self.root / "node" / "node.exe", "fake node, never run")
        self.scenario({"exec": {"reply": REPLY}})
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home),
                    "CODEX_HOME": str(self.home / ".codex"), "ASK_CODEX_STOP_WINDOW_S": "1",
                    "PATH": os.pathsep.join([str(self.node.parent), str(base.STUB), os.environ["PATH"]])}
        self.ports = [free_port(), free_port()]
        self.app = [f"127.0.0.1:{self.ports[0]}", f"localhost:{self.ports[1]}"]
        self.request = {"interaction": "exercise", "kind": "ui", "project": str(self.project),
                        "prompt": "Exercise the app and report what you find.",
                        "models": [{"model": "gpt-6-sol", "effort": "high"}],
                        "target_root": {"path": str(self.targets), "confirmed_by_user": True},
                        "app": self.app, "headed": False, "scope": "", "target_name": "exercise-target",
                        "commands": {"start": [self.fake("listen", f"127.0.0.1:{self.ports[0]}",
                                                         f"127.0.0.1:{self.ports[1]}")]}}

    # --- helpers ---

    def fake(self, mode, *args, cwd=None):
        command = {"argv": [sys.executable, "fakeapp.py", str(self.notes), mode, *map(str, args)]}
        if cwd is not None:
            command["cwd"] = cwd
        return command

    def scenario(self, value):
        base.write(self.project / ".stub/scenario.json", json.dumps({"records": str(self.records), **value}))

    def call(self, *args, code=None, timeout=300):
        seams = json.dumps({"local_app_data": str(self.local), **({"code": code} if code else {})})
        result = subprocess.run([sys.executable, "-c", base.BOOTSTRAP, str(base.CLI), seams, *map(str, args)],
                                env=self.env, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
        if args[0] == "app-start" and (Path(args[1]) / "supervisor-process.json").exists():
            self.track(args[1])  # whatever the outcome, the cleanup knows the supervisor and the app's processes
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def background(self, *args, code=None):
        seams = json.dumps({"local_app_data": str(self.local), **({"code": code} if code else {})})
        process = subprocess.Popen([sys.executable, "-c", base.BOOTSTRAP, str(base.CLI), seams, *map(str, args)],
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.identities.append((process.pid, created_at(process.pid)))
        return process

    def prepare(self, **change):
        path = self.requests / "request.json"
        path.write_text(json.dumps({**self.request, **change}), encoding="utf-8")
        ready = self.call("prepare", path, "--base", self.base)
        self.assertEqual(ready["state"], "prepared", ready)
        directory = Path(ready["directory"])
        return directory, json.loads((directory / "plan.json").read_text("utf-8"))

    def started(self, code=None, **change):
        directory, plan = self.prepare(**change)
        result = self.call("app-start", directory, code=code)
        self.assertEqual(result["state"], "app_started", result)
        return directory, plan, result

    def track(self, directory):
        identity = json.loads((Path(directory) / "supervisor-process.json").read_text("utf-8"))
        if (identity["pid"], identity["created"]) not in self.identities:
            self.identities.append((identity["pid"], identity["created"]))
        self.app_processes()

    def app_processes(self):
        """(pid, created) of every fake-app process that wrote a note and still runs (identities recorded now)."""
        found = []
        for path in self.notes.glob("*.json"):
            pid = json.loads(path.read_text("utf-8"))["pid"]
            created = created_at(pid)
            if created is not None and alive(pid, created):  # an exited process can persist while a handle is open
                found.append((pid, created))
                if (pid, created) not in self.identities:
                    self.identities.append((pid, created))
        return found

    def noted(self, role):
        return [json.loads(p.read_text("utf-8")) for p in self.notes.glob(f"{role}-*.json")]

    def supervisor(self, directory):
        return json.loads((Path(directory) / "supervisor-process.json").read_text("utf-8"))

    def status(self, directory):
        return json.loads((Path(directory) / "supervisor.json").read_text("utf-8"))

    def end_leftovers(self):
        for pid, created in self.identities:
            if created is not None and alive(pid, created):
                kill(pid, created)

    def still_alive(self, identities):
        return [pid for pid, created in identities if alive(pid, created)]

    def exec_calls(self):
        calls = self.records / "exec-calls"
        return sorted(calls.glob("*.json")) if calls.exists() else []

    def runs(self):
        parent = self.base / "ask-codex"
        return sorted(parent.iterdir()) if parent.exists() else []

    def assert_all_gone(self, directory, identities):
        self.assertEqual(self.still_alive(identities), [], "no recorded process alive")
        self.assertEqual(os.listdir(self.targets), [], "the target and its siblings are gone")
        self.assertFalse(os.path.lexists(directory), "the run directory is gone")
        for port in self.ports:
            self.assertFalse(answers(port), f"app port {port} no longer answers")

    def run_completed(self, directory):
        self.assertEqual(self.call("run", directory)["state"], "finished")
        collected = self.call("collect", directory)
        self.assertEqual(collected["runs"][0]["state"], "completed", collected)
        return collected


class AppLifecycleTest(AppTestBase):
    """Ticket 04 acceptance at Seam 1: start, finish, failure, stop."""

    def test_app_survives_separate_cli_calls_and_finish_ends_every_tree_and_removes_the_target(self):
        directory, plan, started = self.started()
        apps = self.app_processes()
        self.assertEqual(len(apps), 1)
        self.assertEqual([a["kind"] for a in started["apps"]], ["start"])
        self.assertEqual(started["apps"][0]["pid"], apps[0][0], "the start command is its own recorded tree")
        # The app runs on after the app-start call returned, across separate CLI calls (I8, N-4).
        self.assertTrue(all(answers(p) for p in self.ports))
        self.run_completed(directory)
        self.assertTrue(all(answers(p) for p in self.ports), "the app outlives run and collect until finish")
        self.assertEqual(self.still_alive(apps), [p for p, _ in apps])
        supervisor = self.supervisor(directory)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        ended = finished["ended"]
        self.assertEqual((ended["codex"]["confirmed"], ended["browser"]["confirmed"], ended["app"]["confirmed"]),
                         (True, True, True), ended)
        self.assertEqual([t["ended"] for t in ended["app"]["trees"]], [True])
        self.assertTrue(ended["app"]["proxy_released"])
        self.assert_all_gone(directory, apps + [(supervisor["pid"], supervisor["created"])])

    def test_working_directory_outside_the_target_is_refused_and_inside_is_used(self):
        for cwd in ("..", "..\\other", "web/../..", "D:\\elsewhere", "\\\\127.0.0.1\\c$\\x", "C:x", "/tmp",
                    "web:stream"):
            with self.subTest(cwd=cwd):
                path = self.requests / "request.json"
                path.write_text(json.dumps({**self.request, "commands": {"start": [self.fake("listen", "x", cwd=cwd)]}}),
                                encoding="utf-8")
                refused = self.call("prepare", path, "--base", self.base)
                self.assertEqual(refused["state"], "failed", refused)
                self.assertIn("working directory", refused["reason"])
                self.assertEqual(self.runs(), [])
                self.assertEqual(os.listdir(self.targets), [])
        base.write(self.project / "web" / "fakeapp.py", FAKE_APP)
        directory, plan, started = self.started(commands={"start": [self.fake("listen", f"127.0.0.1:{self.ports[0]}",
                                                                              f"127.0.0.1:{self.ports[1]}", cwd="web")]})
        self.assertEqual(len(self.noted("listen")), 1)
        apps = self.app_processes()
        self.assertTrue(all(answers(p) for p in self.ports))
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assert_all_gone(directory, apps)

    def test_a_start_that_fails_is_reported_with_its_output_and_nothing_is_left(self):
        directory, plan = self.prepare(commands={"start": [self.fake("listen", f"127.0.0.1:{self.ports[0]}",
                                                                     f"127.0.0.1:{self.ports[1]}"),
                                                           self.fake("fail")]})
        failed = self.call("app-start", directory)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("no Codex call was made", failed["reason"])
        texts = " ".join(o["output"] for o in failed["output"])
        self.assertIn("fatal: cannot read config/app.toml", texts, "the app's output is reported")
        self.assertIn("listening on", texts)
        self.assertTrue(failed["target_removed"], failed)
        self.assertTrue(failed["ended"]["app"]["confirmed"], failed)
        self.assertEqual(self.exec_calls(), [])
        listeners = [(n["pid"], None) for n in self.noted("listen")]
        self.assertEqual(len(listeners), 1, "the first start command had started")
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.runs(), [], "the run directory is removed too")
        for port in self.ports:
            self.assertFalse(answers(port))

    def test_a_port_that_never_answers_is_reported_and_every_started_tree_is_ended(self):
        directory, plan = self.prepare(commands={"start": [self.fake("listen", f"127.0.0.1:{self.ports[0]}"),
                                                           self.fake("never")]})
        failed = self.call("app-start", directory, code=timing(start_timeout=4))
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("never answered", failed["reason"])
        self.assertIn(f"localhost:{self.ports[1]}", failed["reason"])
        texts = " ".join(o["output"] for o in failed["output"])
        self.assertIn("waiting for a database that never comes", texts)
        self.assertEqual(self.exec_calls(), [])
        self.assertTrue(failed["target_removed"])
        self.assertEqual(self.runs(), [])
        self.assertFalse(answers(self.ports[0]), "the started listener was ended")
        for note in self.noted("listen") + self.noted("never"):
            self.assertIsNone(created_at(note["pid"]), f"PID {note['pid']} ended")

    def test_a_listener_on_the_wildcard_address_is_refused(self):
        directory, plan = self.prepare(commands={"start": [self.fake("listen", f"0.0.0.0:{self.ports[0]}",
                                                                     f"127.0.0.1:{self.ports[1]}")]})
        failed = self.call("app-start", directory)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn(f"0.0.0.0:{self.ports[0]}", failed["reason"])
        self.assertIn("not bound to loopback only", failed["reason"])
        self.assertTrue(failed["target_removed"])
        self.assertEqual(self.exec_calls(), [])
        [note] = self.noted("listen")
        self.assertIsNone(created_at(note["pid"]))
        self.assertFalse(answers(self.ports[0]))

    def test_a_port_taken_before_the_start_is_refused_before_any_app_process(self):
        directory, plan = self.prepare()
        with socket.socket() as taken:
            taken.bind(("127.0.0.1", self.ports[1]))
            taken.listen(1)
            failed = self.call("app-start", directory)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("in use before the app start", failed["reason"])
        self.assertIn(f":{self.ports[1]}", failed["reason"])
        self.assertEqual(self.noted("listen"), [], "no app process was started")
        self.assertTrue(failed["target_removed"])
        self.assertEqual(self.runs(), [])

    def test_stop_during_the_app_start_ends_the_partly_started_app(self):
        directory, plan = self.prepare(commands={"start": [self.fake("listen", f"127.0.0.1:{self.ports[0]}"),
                                                           self.fake("never")]})
        starting = self.background("app-start", directory, code=timing(start_timeout=120))
        try:
            wait_until(lambda: self.noted("listen") and self.noted("never"), 60, "the app never started")
            identity = self.supervisor(directory)
            self.identities.append((identity["pid"], identity["created"]))
            apps = self.app_processes()
            self.assertEqual(len(apps), 2)
            stopped = self.call("stop", directory)
            out, err = starting.communicate(timeout=120)
        finally:
            if starting.poll() is None:
                starting.kill()
        self.assertEqual(stopped["state"], "stopped", stopped)
        self.assertEqual(stopped["ended"]["codex"]["state"], "not_started")
        self.assertTrue(stopped["ended"]["app"]["confirmed"], stopped)
        self.assertEqual(sorted(t["ended"] for t in stopped["ended"]["app"]["trees"]), [True, True])
        self.assertTrue(stopped["target_removed"], stopped)
        self.assertEqual(json.loads(out)["state"], "stopped", (out, err))
        self.assertEqual(self.still_alive(apps), [])
        self.assertFalse(alive(identity["pid"], identity["created"]), "the supervisor exited")
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.exec_calls(), [])
        # Never retried automatically: the attempt is recorded; a second app-start and a run are refused.
        again = self.call("app-start", directory)
        self.assertEqual(again["state"], "failed", again)
        self.assertIn("never retried", again["reason"])
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned")

    def test_stop_while_codex_runs_ends_codex_app_and_browser_and_reports_each(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 40, "event_every_s": 0.2}})
        directory, plan, started = self.started()
        apps = self.app_processes()
        running = self.background("run", directory)
        try:
            wait_until(lambda: (self.records / "exec-argv.json").exists(), 60, "Codex never started")
            stopped = self.call("stop", directory)
            running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertIn(stopped["state"], ("stopped", "stop_unconfirmed"), stopped)
        ended = stopped["ended"]
        self.assertIn("codex", ended)
        if stopped["state"] == "stopped":
            for item in ("codex", "browser", "app"):
                self.assertTrue(ended[item]["confirmed"], (item, ended))
            self.assertTrue(stopped["target_removed"])
            self.assertEqual(self.still_alive(apps), [])
            self.assertEqual(self.call("collect", directory)["runs"][0]["state"], "stopped")
            self.assert_all_gone(directory, apps)
        else:  # an unconfirmed Codex stop keeps the app and the target, and says so per item
            self.assertFalse(ended["codex"]["confirmed"])
            self.assertFalse(ended["app"]["confirmed"])
            self.assertTrue(stopped["target_kept"])

    def test_codex_failure_ends_the_app_and_removes_the_target_at_once(self):
        self.scenario({"exec": {"mode": "fail"}})
        directory, plan, started = self.started()
        apps = self.app_processes()
        ran = self.call("run", directory)
        self.assertEqual(ran["state"], "finished", ran)
        self.assertTrue(ran["target_removed"], ran)
        self.assertTrue(ran["ended"]["app"]["confirmed"], ran)
        self.assertEqual(self.still_alive(apps), [])
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.call("run", directory)["state"], "failed", "never replayed")
        self.assertEqual(self.call("collect", directory)["runs"][0]["state"], "failed")
        self.assert_all_gone(directory, apps)

    def test_run_requires_the_started_app_and_cleanup_ends_it(self):
        directory, plan = self.prepare()
        refused = self.call("run", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("app has not been started", refused["reason"])
        self.assertIn("the target was removed", refused["reason"])
        self.assertEqual(self.exec_calls(), [])
        directory, plan = self.prepare(target_name="second")
        self.assertEqual(self.call("app-start", directory)["state"], "app_started")
        self.track(directory)
        apps = self.app_processes()
        cleaned = self.call("cleanup", directory)
        self.assertEqual(cleaned["state"], "cleaned", cleaned)
        self.assertTrue(cleaned["ended"]["app"]["confirmed"])
        self.assert_all_gone(directory, apps)


class SupervisorProcessTest(AppTestBase):
    """I8: the job, suspended creation, inheritance, the supervisor's death, ports."""

    def test_install_link_resolving_outside_the_target_stops_the_exercise_and_is_not_followed(self):
        sentinel = base.tree(self.sentinel)
        directory, plan = self.prepare(commands={"install": [self.fake("junction", "linked", str(self.sentinel))],
                                                 "start": self.request["commands"]["start"]})
        failed = self.call("app-start", directory)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("resolve outside it", failed["reason"])
        self.assertIn("linked", failed["reason"])
        self.assertEqual(self.noted("listen"), [], "no start command ran")
        self.assertTrue(failed["target_removed"], failed)
        self.assertEqual(base.tree(self.sentinel), sentinel, "the sentinel is unchanged: removal did not follow")
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.exec_calls(), [])
        # A link the install creates inside the target (as pnpm does) is allowed.
        base.write(self.project / "inside" / "x.txt", "x")
        directory, plan, started = self.started(target_name="second", commands={
            "install": [self.fake("junction", "linked", str(self.targets / "second" / "inside"))],
            "start": self.request["commands"]["start"]})
        self.assertEqual(started["apps"][0]["kind"], "install")
        self.assertEqual(started["apps"][0]["exit_code"], 0)
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assertEqual(base.tree(self.sentinel), sentinel)

    def test_a_pre_created_job_with_the_expected_name_is_refused(self):
        sys.path.insert(0, str(SCRIPTS))
        import winjob
        squatter = winjob.Job("ask-codex-app")
        self.addCleanup(squatter.close)
        suffix = squatter.name.rsplit("-", 1)[1]
        wrapper = (
            "import json, runpy, sys\n"
            "script, directory = sys.argv[1], sys.argv[2]\n"
            "sys.path.insert(0, str(__import__('pathlib').Path(script).parent))\n"
            "import winjob\n"
            f"winjob.secrets.token_hex = lambda n: {suffix!r}\n"
            "sys.argv = [script, 'serve', directory]\n"
            "runpy.run_path(script, run_name='__main__')\n")
        code = ("import supervisor, sys\n"
                f"supervisor.command = lambda d: [sys.executable, '-c', {wrapper!r}, "
                "str(supervisor.HERE / 'supervisor.py'), str(d)]\n")
        directory, plan = self.prepare()
        failed = self.call("app-start", directory, code=code)
        self.assertEqual(failed["state"], "failed", failed)
        self.assertIn("already exists", failed["reason"])
        self.assertEqual(self.noted("listen"), [], "no app process was started")
        self.assertTrue(failed["target_removed"])
        self.assertEqual(self.exec_calls(), [])

    def test_a_child_spawned_at_the_first_instruction_is_inside_the_job(self):
        sys.path.insert(0, str(SCRIPTS))
        import winjob
        directory, plan, started = self.started(commands={"start": [
            self.fake("first-child", f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{self.ports[1]}")]})
        [parent] = self.noted("first-child")
        job = winjob.open_job(self.status(directory)["job"])
        self.assertIsNotNone(job)
        try:
            members = winjob.job_pids(job)
        finally:
            winjob.close_handle(job)
        self.assertIn(parent["pid"], members)
        self.assertIn(parent["child"], members, "the child started at once is in the app job")
        supervisor = self.supervisor(directory)
        self.assertNotIn(supervisor["pid"], members, "the supervisor is not a member of the app job")
        apps = self.app_processes()
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assert_all_gone(directory, apps)

    def test_app_processes_inherit_neither_the_job_handle_nor_the_proxy_socket(self):
        sys.path.insert(0, str(SCRIPTS))
        import winjob
        # Positive control: the probe sees a job handle and a listening socket when they are inherited.
        job = winjob.Job("ask-codex-test")
        self.addCleanup(job.close)
        _k32.SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
        self.assertTrue(_k32.SetHandleInformation(job.handle, 1, 1))
        listener = socket.socket()
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.set_inheritable(True)
        port = free_port()
        control = subprocess.Popen([sys.executable, str(self.project / "fakeapp.py"), str(self.notes), "probe",
                                    f"127.0.0.1:{port}"], close_fds=False)
        self.identities.append((control.pid, created_at(control.pid)))
        wait_until(lambda: self.noted("probe"), 30, "the control probe never reported")
        [report] = self.noted("probe")
        self.assertGreaterEqual(report["jobs"], 1, report)
        self.assertIn(listener.getsockname()[1], report["socket_ports"], report)
        control.kill()
        control.wait()
        (self.notes / f"probe-{report['pid']}.json").unlink()
        # The supervised app: no job handle, no socket at all (in particular not the owned proxy port).
        directory, plan, started = self.started(commands={"start": [
            self.fake("probe", f"127.0.0.1:{self.ports[0]}", f"127.0.0.1:{self.ports[1]}")]})
        [report] = self.noted("probe")
        self.assertEqual(report["jobs"], 0, report)
        self.assertNotIn(plan["browser"]["proxy_port"], report["socket_ports"], report)
        self.assertEqual(report["socket_ports"], [], report)
        self.assertGreater(report["handles"], 0)
        self.assertEqual(self.call("finish", directory)["state"], "finished")

    def test_a_grandchild_whose_parent_exits_at_once_and_a_cmd_start_child_are_ended(self):
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        self.assertTrue(pythonw.is_file())
        shell = (f'start "" "{pythonw}" fakeapp.py "{self.notes}" listen 127.0.0.1:{self.ports[1]}')
        directory, plan, started = self.started(commands={"start": [
            self.fake("middle", f"127.0.0.1:{self.ports[0]}"), {"shell": shell}]})
        [middle] = self.noted("middle")
        listeners = self.noted("listen")
        self.assertEqual(len(listeners), 2, "the grandchild and the `start` child both listen")
        identity = (middle["pid"], created_at(middle["pid"]))
        wait_until(lambda: not alive(*identity), 15, "the middle parent did not exit")
        apps = self.app_processes()
        self.assertEqual(len(apps), 2, "the middle parent and cmd exited; their children run on")
        self.assertTrue(all(answers(p) for p in self.ports))
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assert_all_gone(directory, apps)

    def test_killing_the_supervisor_ends_the_app(self):
        directory, plan, started = self.started()
        apps = self.app_processes()
        identity = self.supervisor(directory)
        kill(identity["pid"], identity["created"])
        wait_until(lambda: not self.still_alive(apps), 15, "kill-on-close did not end the app")
        self.assertFalse(any(answers(p) for p in self.ports))
        self.assertTrue(bindable(plan["browser"]["proxy_port"]), "the dead supervisor's proxy port is unheld")
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(finished["ended"]["app"]["confirmed"])
        self.assertEqual(finished["ended"]["app"]["how"], "supervisor_gone")
        self.assert_all_gone(directory, apps)

    def test_the_supervisor_holds_the_proxy_port_from_app_start_until_finish(self):
        sys.path.insert(0, str(SCRIPTS))
        import winjob
        directory, plan, started = self.started()
        port, supervisor = plan["browser"]["proxy_port"], self.supervisor(directory)
        self.assertNotIn(port, self.ports, "the owned proxy port is never an app port")

        def held():
            owners = {pid for _, p, pid in winjob.tcp_listeners() if p == port}
            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.settimeout(5)
                return owners, client.recv(16)
        self.assertEqual(held(), ({supervisor["pid"]}, b""), "accepts and closes; held by the supervisor")
        self.assertFalse(bindable(port))
        self.run_completed(directory)
        self.assertEqual(held(), ({supervisor["pid"]}, b""), "still held after Codex ended (C2 follow-up 1)")
        self.assertEqual(self.call("finish", directory)["state"], "finished")
        self.assertTrue(bindable(port), "released once everything is confirmed ended")

    def test_the_owned_proxy_port_never_collides_with_an_app_port(self):
        first = self.ports[0]
        code = ("import browser\n_original, _calls = browser.free_loopback_port, []\n"
                "def free():\n    _calls.append(1)\n"
                f"    return {first} if len(_calls) == 1 else _original()\n"
                "browser.free_loopback_port = free\n")
        path = self.requests / "request.json"
        path.write_text(json.dumps(self.request), encoding="utf-8")
        ready = self.call("prepare", path, "--base", self.base, code=code)
        self.assertEqual(ready["state"], "prepared", ready)
        directory = Path(ready["directory"])
        plan = json.loads((directory / "plan.json").read_text("utf-8"))
        self.assertNotEqual(plan["browser"]["proxy_port"], first)
        self.assertNotIn(plan["browser"]["proxy_port"], self.ports)
        # A plan whose proxy port is an app port is refused at app-start, before any app process.
        plan["browser"]["proxy_port"] = first
        (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        refused = self.call("app-start", directory)
        self.assertEqual(refused["state"], "failed", refused)
        self.assertIn("proxy port is one of the app ports", refused["reason"])
        self.assertEqual(self.noted("listen"), [])
        self.assertEqual(os.listdir(self.targets), [])

    def test_breakaway_falls_back_when_the_callers_job_forbids_it(self):
        sys.path.insert(0, str(SCRIPTS))
        import supervisor
        calls = []
        original = subprocess.Popen

        def popen(argv, **kwargs):
            calls.append(kwargs["creationflags"])
            if kwargs["creationflags"] & supervisor.BREAKAWAY:
                error = OSError("access denied")
                error.winerror = 5
                raise error
            return original([sys.executable, "-c", "pass"], **{**kwargs, "cwd": None})
        directory = self.root / "base" / "ask-codex" / "run.x"
        directory.mkdir(parents=True)
        supervisor.subprocess.Popen = popen
        try:
            identity, process = supervisor.launch(directory)
        finally:
            supervisor.subprocess.Popen = original
        process.wait(30)
        self.assertEqual([bool(f & supervisor.BREAKAWAY) for f in calls], [True, False])
        self.assertFalse(identity["breakaway"])
        self.assertTrue(identity["created"])


class CodexProcessesTest(AppTestBase):
    """I15 and U10 through the CLI; N-d (the proxy is released only after I15's processes ended)."""

    def left_processes(self):
        path = self.records / "left-processes.jsonl"
        return [json.loads(line) for line in path.read_text("utf-8").splitlines()] if path.exists() else []

    def test_a_process_holding_the_nonce_keeps_proxy_job_and_directories_until_it_ends(self):
        self.scenario({"exec": {"reply": REPLY, "leave_process": {"seconds": 300, "outside_tree": True}}})
        directory, plan, started = self.started()
        apps = self.app_processes()
        self.run_completed(directory)
        [left] = self.left_processes()
        self.assertEqual(left["nonce"], plan["summary"]["browser_server"])
        created = created_at(left["pid"])
        self.assertIsNotNone(created, "the stand-in outlived the stub Codex")
        self.identities.append((left["pid"], created))
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "stop_unconfirmed", finished)
        browser_state = finished["ended"]["browser"]
        self.assertFalse(browser_state["confirmed"])
        [reported] = browser_state["alive"]
        self.assertEqual(reported["pid"], left["pid"])
        self.assertTrue(Path(reported["image"]).name.lower().startswith("python"), reported)
        self.assertEqual(reported["source"], "recognised")
        self.assertIn(str(left["pid"]), finished["reason"])
        self.assertTrue(alive(left["pid"], created), "a recognised process is reported, never terminated")
        # Everything is kept: the proxy listener (N-d), the app and its job, the target, the run directory.
        self.assertEqual(finished["retained_location"], str(directory))
        self.assertTrue(finished["target_kept"])
        self.assertFalse(bindable(plan["browser"]["proxy_port"]), "the proxy port is still held")
        self.assertTrue(all(answers(p) for p in self.ports))
        self.assertEqual(self.still_alive(apps), [p for p, _ in apps])
        self.assertTrue(Path(plan["summary"]["target"]).exists() and directory.exists())
        # Once it has ended, finish ends the app, releases the proxy and removes everything.
        kill(left["pid"], created)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(bindable(plan["browser"]["proxy_port"]))
        self.assert_all_gone(directory, apps)

    def test_codex_descendants_are_recorded_while_it_runs_and_none_is_left_after_finish(self):
        self.scenario({"exec": {"reply": REPLY, "mode": "slow-active", "duration_s": 6, "event_every_s": 0.5,
                                "leave_process": {"seconds": 300}}})
        directory, plan, started = self.started()
        apps = self.app_processes()
        running = self.background("run", directory)
        try:
            wait_until(lambda: self.left_processes(), 60, "the stub left no process")
            [left] = self.left_processes()
            created = created_at(left["pid"])
            self.identities.append((left["pid"], created))
            wait_until(lambda: (directory / "codex-processes.json").exists() and any(
                r["pid"] == left["pid"] for r in json.loads((directory / "codex-processes.json").read_text("utf-8"))),
                30, "the supervisor never recorded Codex's descendant")
            running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        [record] = [r for r in json.loads((directory / "codex-processes.json").read_text("utf-8"))
                    if r["pid"] == left["pid"]]
        self.assertEqual(record["created"], created, "recorded by PID and creation time")
        self.assertEqual(self.call("collect", directory)["runs"][0]["state"], "completed")
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertTrue(finished["ended"]["browser"]["confirmed"])
        self.assertFalse(alive(left["pid"], created), "Codex's descendant is ended")
        self.assert_all_gone(directory, apps)

    def test_codex_is_stopped_when_the_supervisor_dies(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 60, "event_every_s": 0.2}})
        directory, plan, started = self.started()
        apps = self.app_processes()
        identity = self.supervisor(directory)
        running = self.background("run", directory)
        try:
            wait_until(lambda: (directory / "0" / "pid").exists() and (self.records / "exec-argv.json").exists(),
                       60, "Codex never started")
            time.sleep(1)
            kill(identity["pid"], identity["created"])
            died = time.monotonic()
            wait_until(lambda: (directory / "0" / "stop-request").exists(), 5, "no stop requested")
            self.assertLess(time.monotonic() - died, 2.5, "the Codex stop starts within 2 s of the death (U10)")
            out, err = running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        ran = json.loads(out)
        self.assertIn("supervisor_died", ran, (out, err))
        self.assertFalse((self.records / "exec-finished").exists(), "the stub Codex did not run to its end")
        root = dict(line.split("=", 1) for line in (directory / "0" / "pid").read_text().splitlines() if "=" in line)
        self.assertIsNone(created_at(int(root["pid"])), "the Codex root has ended")
        self.assertEqual(self.still_alive(apps), [], "kill-on-close ended the app")
        collected = self.call("collect", directory)
        self.assertIn(collected["runs"][0]["state"], ("stopped", "stop_unconfirmed"), collected)
        if collected["runs"][0]["state"] == "stopped":
            self.assert_all_gone(directory, apps)

    def test_a_run_killed_during_its_launch_checks_no_longer_blocks_finish(self):
        directory, plan, started = self.started()
        apps = self.app_processes()
        stall = ("import exercise, time\n_original = exercise.before_launch\n"
                 "def before_launch(*args, **kwargs):\n    time.sleep(300)\n"
                 "exercise.before_launch = before_launch\n")
        running = self.background("run", directory, code=stall)
        try:
            wait_until(lambda: (directory / "started").exists(), 60, "run never claimed its attempt")
            for action in ("finish", "cleanup", "stop"):
                refused = self.call(action, directory)
                self.assertEqual(refused["state"], "failed", (action, refused))
                self.assertIn("run is starting", refused["reason"])
            self.assertTrue(all(answers(p) for p in self.ports))
        finally:
            running.kill()
            running.communicate(timeout=60)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        self.assertEqual(self.exec_calls(), [])
        self.assert_all_gone(directory, apps)


class BoundsTest(AppTestBase):
    """I12: lifetime bounds held by the supervisor; registered repro jobs end before the app job."""

    def repro_job(self, directory):
        """A fake registered repro job (C6 registers real ones) with a sleeper inside; the test holds a handle."""
        sys.path.insert(0, str(SCRIPTS))
        import winjob
        job = winjob.Job("ask-codex-repro")
        self.addCleanup(job.close)
        sleeper = winjob.start_suspended(job, [sys.executable, "-c", "import time; time.sleep(300)"], str(self.root),
                                         {"SYSTEMROOT": os.environ["SYSTEMROOT"]})
        self.addCleanup(sleeper.close)
        self.identities.append((sleeper.pid, created_at(sleeper.pid)))
        (Path(directory) / "repro-jobs").mkdir()
        (Path(directory) / "repro-jobs" / job.name).touch()
        return job, (sleeper.pid, created_at(sleeper.pid))

    def wait_state(self, directory, states, timeout=120):
        wait_until(lambda: (Path(directory) / "supervisor.json").exists() and
                   self.status(directory)["state"] in states, timeout,
                   f"the supervisor never reached {states}")
        return self.status(directory)

    def test_the_lifetime_bound_ends_a_registered_repro_job_then_the_app_job_and_removes_the_target(self):
        directory, plan, started = self.started(code=timing(bound_after_start=8), commands={"start": [
            self.fake("listen-link", "linked", str(self.sentinel), f"127.0.0.1:{self.ports[0]}",
                      f"127.0.0.1:{self.ports[1]}")]})
        sentinel = base.tree(self.sentinel)
        apps = self.app_processes()
        job, sleeper = self.repro_job(directory)
        identity = self.supervisor(directory)
        status = self.wait_state(directory, ("bound_ended", "stop_unconfirmed", "end_unconfirmed"))
        self.assertEqual(status["state"], "bound_ended", status)
        self.assertEqual(status["bound"]["bound"], "6 h after the app start")
        self.assertEqual([o["kind"] for o in status["order"]], ["repro", "app"], "the repro job ends first")
        self.assertEqual(status["order"][0]["job"], job.name)
        self.assertEqual(job.active_processes(), 0)
        self.assertFalse(alive(*sleeper))
        self.assertEqual(self.still_alive(apps), [])
        self.assertEqual(status["listeners"], [], "no listener on the app ports")
        self.assertEqual(status["bound"]["removal"]["state"], "removed")
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(base.tree(self.sentinel), sentinel, "the app's junction was not followed")
        wait_until(lambda: not alive(identity["pid"], identity["created"]), 15, "the supervisor did not exit")
        self.assertTrue(bindable(plan["browser"]["proxy_port"]))
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned", "the run directory is left for cleanup")
        self.assert_all_gone(directory, apps)

    def test_finish_ends_a_registered_repro_job_before_the_app_job(self):
        directory, plan, started = self.started()
        apps = self.app_processes()
        self.run_completed(directory)
        job, sleeper = self.repro_job(directory)
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "finished", finished)
        order = finished["ended"]["app"]["order"]
        self.assertEqual([o["kind"] for o in order], ["repro", "app"], order)
        self.assertLessEqual(order[0]["at"], order[1]["at"])
        self.assertFalse(alive(*sleeper))
        self.assert_all_gone(directory, apps)

    def test_the_bound_after_collect_and_the_bound_with_codex_running_stop_codex_and_end_the_app(self):
        # 2 h after collect (shortened).
        directory, plan, started = self.started(code=timing(bound_after_collect=3))
        apps = self.app_processes()
        self.run_completed(directory)
        status = self.wait_state(directory, ("bound_ended", "stop_unconfirmed", "end_unconfirmed"))
        self.assertEqual((status["state"], status["bound"]["bound"]), ("bound_ended", "2 h after collect"), status)
        self.assertEqual(status["bound"]["codex"]["state"], "finished")
        self.assertEqual(self.still_alive(apps), [])
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.call("cleanup", directory)["state"], "cleaned")
        # 6 h after the app start (shortened) while Codex runs: the ADR 0004 stop path ends the Codex tree first.
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 120, "event_every_s": 0.2}})
        directory, plan, started = self.started(code=timing(bound_after_start=10), target_name="second")
        apps = self.app_processes()
        running = self.background("run", directory)
        try:
            status = self.wait_state(directory, ("bound_ended", "stop_unconfirmed", "end_unconfirmed"), 180)
            running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertEqual(status["state"], "bound_ended", status)
        self.assertEqual(status["bound"]["codex"]["state"], "stopped", status)
        self.assertTrue(status["bound"]["browser"]["confirmed"])
        self.assertFalse((self.records / "exec-finished").exists(), "Codex was stopped by the bound")
        self.assertEqual(self.still_alive(apps), [])
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.call("collect", directory)["runs"][0]["state"], "stopped")
        self.assertFalse(directory.exists())

    def test_a_bound_whose_codex_stop_is_unconfirmed_keeps_proxy_job_and_target(self):
        self.scenario({"exec": {"mode": "slow-active", "duration_s": 120, "event_every_s": 0.2}})
        directory, plan, started = self.started(code=timing(bound_after_start=12))
        apps = self.app_processes()
        identity = self.supervisor(directory)
        running = self.background("run", directory)
        try:
            wait_until(lambda: (directory / "0" / "pid").exists() and (directory / "0" / "process-identities").exists(),
                       60, "Codex never started")
            # The ADR 0004 stop path cannot verify the tree without a usable recorded identity.
            (directory / "0" / "pid").write_text("pid=unknown\nplatform=windows\n", encoding="utf-8")
            status = self.wait_state(directory, ("bound_ended", "stop_unconfirmed", "end_unconfirmed"), 120)
            running.communicate(timeout=120)
        finally:
            if running.poll() is None:
                running.kill()
        self.assertEqual(status["state"], "stop_unconfirmed", status)
        self.assertFalse(status["bound"]["codex"]["confirmed"])
        self.assertTrue(alive(identity["pid"], identity["created"]), "the supervisor keeps holding")
        self.assertFalse(bindable(plan["browser"]["proxy_port"]), "the proxy listener is kept")
        self.assertTrue(all(answers(p) for p in self.ports), "the app job is kept")
        self.assertEqual(self.still_alive(apps), [p for p, _ in apps])
        self.assertTrue(Path(plan["summary"]["target"]).exists(), "the target is kept")
        finished = self.call("finish", directory)
        self.assertEqual(finished["state"], "stop_unconfirmed", finished)
        self.assertTrue(Path(plan["summary"]["target"]).exists())
        # Test cleanup: end the supervisor by its identity; kill-on-close ends the app.
        kill(identity["pid"], identity["created"])
        wait_until(lambda: not self.still_alive(apps), 15, "the app outlived its supervisor")


@unittest.skipUnless(sys.platform == "win32", "Windows only")
class SupervisorUnitTest(unittest.TestCase):
    """In-process: I15 identity rules (terminate by verified handle, never a reused PID; descendants by identity)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        import supervisor
        import winjob
        cls.supervisor, cls.winjob = supervisor, winjob

    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="u-", dir=TEST_ROOT))
        self.addCleanup(base.scrub, self.root)
        self.started = []
        self.addCleanup(lambda: [kill(p, c) for p, c in self.started if c and alive(p, c)])

    def sleeper(self, code="import time; time.sleep(120)"):
        process = subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE)
        identity = (process.pid, created_at(process.pid))
        self.started.append(identity)
        # Cleanups run last-in first-out: end it by its identity, then reap it, then close its pipe.
        self.addCleanup(process.stdout.close)
        self.addCleanup(process.wait, 30)
        self.addCleanup(lambda: alive(*identity) and kill(*identity))
        return process, identity

    def plan(self):
        return {"summary": {"browser_server": "cdt_" + "f" * 16},
                "browser": {"cwd": str(self.root / "c"), "temp": str(self.root / "t"), "profile": str(self.root / "p")}}

    def test_recorded_processes_are_terminated_only_with_their_recorded_creation_time(self):
        _, (pid, created) = self.sleeper()
        _, (other, other_created) = self.sleeper()
        (self.root / "codex-processes.json").write_text(json.dumps([
            {"pid": pid, "created": created, "image": "python.exe"},
            {"pid": other, "created": other_created + 1, "image": "python.exe"}]), encoding="utf-8")
        result = self.supervisor.codex_processes_ended(self.root, self.plan(), {os.getpid()}, patience=1)
        self.assertTrue(result["confirmed"], result)
        self.assertEqual([t["pid"] for t in result["terminated"]], [pid])
        self.assertFalse(alive(pid, created))
        self.assertTrue(alive(other, other_created), "another creation time is another process: untouched")

    def test_descendants_are_recorded_from_the_identified_root_only(self):
        code = ("import subprocess, sys, time; c = subprocess.Popen([sys.executable, '-c', 'import time; "
                "time.sleep(120)']); print(c.pid, flush=True); time.sleep(120)")
        process, (root, created) = self.sleeper(code)
        child = int(process.stdout.readline())
        self.started.append((child, created_at(child)))
        (self.root / "0").mkdir()
        (self.root / "0" / "pid").write_text(f"pid={root}\nplatform=windows\nidentity={created + 1}\n")
        self.assertEqual(self.supervisor.snapshot_codex(self.root), [], "a root of another identity is ignored")
        self.assertFalse((self.root / "codex-processes.json").exists())
        ticks = self.winjob.dotnet_ticks(created)
        (self.root / "0" / "pid").write_text(f"pid={root}\nplatform=windows\nidentity={ticks}\n")
        found = self.supervisor.snapshot_codex(self.root)
        self.assertEqual([(r["pid"], r["created"]) for r in found], [(child, created_at(child))])
        recorded = json.loads((self.root / "codex-processes.json").read_text("utf-8"))
        self.assertEqual([r["pid"] for r in recorded], [child])

    def test_recognition_by_nonce_and_user_data_dir_never_counts_excluded_processes(self):
        plan = self.plan()
        _, nonce = self.sleeper("import time; time.sleep(120)  # cdt_" + "f" * 16)
        profile = plan["browser"]["profile"]
        _, chrome = self.sleeper(f"import time; time.sleep(120)  # --user-data-dir={profile}\\Default")
        _, unrelated = self.sleeper("import time; time.sleep(120)  # cdt_" + "e" * 16)
        found = {r["pid"]: r for r in self.supervisor.recognise(self.root, plan, {os.getpid()})}
        self.assertIn(nonce[0], found)
        self.assertIn(chrome[0], found)
        self.assertNotIn(unrelated[0], found)
        excluded = {r["pid"] for r in self.supervisor.recognise(self.root, plan, {os.getpid(), nonce[0]})}
        self.assertNotIn(nonce[0], excluded, "the script's own processes are never counted")
        result = self.supervisor.codex_processes_ended(self.root, plan, {os.getpid()}, patience=0.5)
        self.assertFalse(result["confirmed"])
        self.assertTrue(alive(*nonce) and alive(*chrome), "recognised processes are not terminated")

    def test_commands_are_validated_and_programs_resolved_verbatim(self):
        s = self.supervisor
        ok = s.validate_commands({"install": [{"shell": "npm ci"}],
                                  "start": [{"argv": ["node", "server.js"], "cwd": "api", "env": {"PORT": "8000"}}]})
        self.assertEqual(ok["start"][0]["cwd"], "api")
        for bad in ({"start": []}, {"start": [{"argv": []}]}, {"start": [{"shell": "a\nb"}]},
                    {"start": [{"argv": ["x"], "shell": "y"}]}, {"start": [{"argv": ["x"], "env": {"A=B": "1"}}]},
                    {"start": [{"argv": ["x"], "user": "admin"}]}, {"other": []}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                s.validate_commands(bad)
        program, line = s.program_for({"shell": 'npm run dev -- --host 127.0.0.1'}, {})
        self.assertEqual(Path(program).name.lower(), "cmd.exe")
        self.assertEqual(line, f'"{program}" /d /s /c "npm run dev -- --host 127.0.0.1"')
        program, line = s.program_for({"argv": ["python", "-c", "print('a b')"]},
                                      {"PATH": str(Path(sys.executable).parent)})
        self.assertEqual(Path(program), Path(sys.executable))
        self.assertTrue(line.endswith("-c \"print('a b')\""), line)
        for name in ("..\\x.exe", "bin/x.exe", "npm.cmd"):
            with self.subTest(program=name), self.assertRaises(ValueError):
                s.program_for({"argv": [name]}, {"PATH": str(Path(sys.executable).parent)})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--test-root", help="parent of the per-test directories (outside any repository)")
    known, rest = parser.parse_known_args()
    if known.test_root:
        TEST_ROOT = base.TEST_ROOT = Path(known.test_root)
    unittest.main(argv=[sys.argv[0], *rest])
