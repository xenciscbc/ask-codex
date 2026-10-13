"""Disposable target of an exercise through the public CLI (plan C1); offline, Windows only, never calls Codex.

Every test works in a fresh directory under the test root (`--test-root`, default D:\\tmp\\ask-codex-tests,
outside any repository), created and removed by the test and passed to the code only through request
fields and `--base`, never through the environment.
"""
import ast
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "skills/ask/scripts/consult.py"
SCRIPTS = REPO / "skills/ask/scripts"
TEST_ROOT = Path(r"D:\tmp\ask-codex-tests")
REPARSE, DIRECTORY, READONLY = 0x400, 0x10, 0x1


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


def snapshot(path):
    """Relative path -> (kind, content hash or link target, attributes, mtime) for the tree and its top."""
    top = os.lstat(extended(path))
    found = {".": ("top", None, top.st_file_attributes, top.st_mtime_ns)}

    def walk(current, parts):
        for entry in os.scandir(current):
            status = entry.stat(follow_symlinks=False)
            key = "/".join(parts + (entry.name,))
            if status.st_file_attributes & REPARSE:
                found[key] = ("link", os.readlink(entry.path), status.st_file_attributes, None)
            elif status.st_file_attributes & DIRECTORY:
                found[key] = ("dir", None, status.st_file_attributes, None)
                walk(entry.path, parts + (entry.name,))
            else:
                with open(entry.path, "rb") as source:
                    digest = hashlib.sha256(source.read()).hexdigest()
                found[key] = ("file", digest, status.st_file_attributes, status.st_mtime_ns)

    if top.st_file_attributes & DIRECTORY:
        walk(extended(path), ())
    else:
        with open(extended(path), "rb") as source:
            found["."] = ("top", hashlib.sha256(source.read()).hexdigest(), top.st_file_attributes, top.st_mtime_ns)
    return found


def named_streams(path):
    """Every stream of a file or directory other than the unnamed data stream (FindFirstStreamW)."""
    class FindStreamData(ctypes.Structure):
        _fields_ = [("StreamSize", ctypes.c_longlong), ("cStreamName", ctypes.c_wchar * 296)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.FindFirstStreamW.restype = ctypes.c_void_p
    kernel32.FindFirstStreamW.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
    kernel32.FindNextStreamW.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    kernel32.FindClose.argtypes = [ctypes.c_void_p]
    data = FindStreamData()
    handle = kernel32.FindFirstStreamW(extended(path), 0, ctypes.byref(data), 0)
    if handle in (None, ctypes.c_void_p(-1).value):
        if ctypes.get_last_error() == 38:  # ERROR_HANDLE_EOF: no stream at all
            return []
        raise ctypes.WinError(ctypes.get_last_error())
    names = []
    try:
        while True:
            if data.cStreamName.upper() != "::$DATA":
                names.append(data.cStreamName)
            if not kernel32.FindNextStreamW(handle, ctypes.byref(data)):
                return names
    finally:
        kernel32.FindClose(handle)


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


def tearDownModule():
    try:
        TEST_ROOT.rmdir()  # only when every test removed its own directory
    except OSError:
        pass


@unittest.skipUnless(sys.platform == "win32", "the exercise platform layer is Windows only (plan I13)")
class DisposableTargetTest(unittest.TestCase):
    def setUp(self):
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="t-", dir=TEST_ROOT))
        self.addCleanup(scrub, self.root)
        self.project, self.targets = self.root / "project", self.root / "targets"
        self.sentinel, self.base, self.requests = self.root / "sentinel", self.root / "base", self.root / "requests"
        for directory in (self.project, self.targets, self.sentinel, self.base, self.requests):
            directory.mkdir()
        write(self.sentinel / "keep.txt", "sentinel content")
        self.sentinel_file = write(self.sentinel / "readonly.txt", "read-only sentinel")
        os.chmod(self.sentinel_file, stat.S_IREAD)
        write(self.project / "README.md", "project")
        self.env = dict(os.environ)

    # --- helpers ---

    def request(self, **changes):
        request = {"project": str(self.project), "target_root": {"path": str(self.targets), "confirmed_by_user": True}}
        request.update(changes)
        return request

    def call(self, *args, env=None, bootstrap=None):
        prefix = [sys.executable, "-c", bootstrap, str(CLI)] if bootstrap else [sys.executable, str(CLI)]
        result = subprocess.run([*prefix, *map(str, args)], env=env or self.env, capture_output=True,
                                text=True, encoding="utf-8", timeout=120)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def create(self, request=None, **options):
        path = self.requests / "request.json"
        path.write_text(json.dumps(self.request() if request is None else request), encoding="utf-8")
        return self.call("target-create", path, "--base", self.base, **options)

    def remove(self, directory, **options):
        return self.call("target-remove", directory, **options)

    def runs(self):
        parent = self.base / "ask-codex"
        return sorted(parent.iterdir()) if parent.exists() else []

    def created(self, request=None):
        result = self.create(request)
        self.assertEqual(result["state"], "created", result)
        return result, Path(result["target"])

    def assert_unchanged(self, before, path):
        self.assertEqual(snapshot(path), before, f"{path} changed")

    def assert_refused_without_writes(self, request, expected, env=None):
        targets, base = snapshot(self.targets), snapshot(self.base)
        result = self.create(request, env=env)
        self.assertEqual(result["state"], "failed", result)
        self.assertIn(expected.lower(), result["reason"].lower())
        self.assertNotIn("target", result)
        self.assert_unchanged(targets, self.targets)
        self.assert_unchanged(base, self.base)
        return result

    # --- create, copy and remove ---

    def test_copy_leaves_out_metadata_dependencies_secrets_and_links_then_removal_deletes_only_the_target(self):
        p = self.project
        write(p / "src/app.py", "print('app')")
        write(p / ".git/config", "[core]")
        write(p / "src/.git/HEAD", "ref: refs/heads/main")       # .git directory at depth
        write(p / "lib/deep/.GIT", "gitdir: elsewhere")          # .git file at depth, other case
        for name in (".hg/store", ".svn/entries", ".jj/repo", ".codex/config.toml", "pkg/.codex/hooks.json",
                     ".claude/settings.json", "node_modules/a/index.js", "web/Node_Modules/b.js", ".venv/pyvenv.cfg",
                     "venv/x", "src/__pycache__/app.pyc", ".pnpm-store/v3", "dist/bundle.js", ".env", ".env.local",
                     "config/.env.test", "keys/server.pem", "deploy.KEY", "cert.pfx", "store.p12", "id_rsa",
                     "credentials.json"):
            write(p / name, "never copied")
        write(p / ".env.test", "TEST_ONLY=1")
        write(p / "\u8cc7\u6599.txt", "unicode name")
        os.chmod(write(p / "readonly.txt", "read-only"), stat.S_IREAD)
        os.link(self.sentinel_file, p / "hard.txt")              # hard link to a sentinel file
        junction(p / "link-out", self.sentinel)                  # junction to a sentinel outside
        junction(p / "link-in", p / "src")                       # absolute junction into the project
        project, sentinel = snapshot(p), snapshot(self.sentinel)

        result, target = self.created(self.request(env_files=[".env.test"], exclude_names=["dist"]))

        self.assertEqual(str(target.parent).casefold(), str(self.targets).casefold())
        copied = {key for key in snapshot(target) if key != "."}
        self.assertEqual(copied, {"README.md", "src", "src/app.py", "lib", "lib/deep", "pkg", "web", "config", "keys",
                                  ".env.test", "\u8cc7\u6599.txt", "readonly.txt", "hard.txt"})
        self.assertFalse(any(kind == "link" for kind, *_ in snapshot(target).values()))
        self.assertEqual({s["path"] for s in result["skipped_links"]}, {"link-out", "link-in"})
        for name in (".git", "src/.git", "lib/deep/.GIT", ".codex", "pkg/.codex", ".claude", "node_modules",
                     "web/Node_Modules", ".venv", "venv", "src/__pycache__", ".pnpm-store", "dist", ".env",
                     ".env.local", "config/.env.test", "keys/server.pem", "deploy.KEY", "cert.pfx", "store.p12",
                     "id_rsa", "credentials.json"):
            self.assertIn(name, result["excluded"])
        self.assertEqual(result["env_files"], [".env.test"])
        self.assertEqual((target / ".env.test").read_text(encoding="utf-8"), "TEST_ONLY=1")
        self.assertTrue(os.stat(target / "readonly.txt").st_file_attributes & READONLY)
        self.assertEqual(os.stat(target / "hard.txt").st_nlink, 1, "a hard link is copied as an independent file")
        run = Path(result["directory"])
        self.assertEqual(run.parent, self.base / "ask-codex")
        self.assertTrue(run.name.startswith("run."))
        record = json.loads((run / "target.json").read_text(encoding="utf-8"))
        self.assertEqual(record["copy"], "done")
        self.assertEqual(record["root"]["path"].casefold(), str(self.targets).casefold())
        self.assertTrue(record["root"]["volume_serial"] and record["root"]["file_id"])
        [entry] = record["entries"]
        self.assertEqual((entry["kind"], entry["path"], entry["state"]), ("target", result["target"], "created"))
        self.assertTrue(entry["volume_serial"] and entry["file_id"])
        self.assert_unchanged(project, p)                         # nothing written into the project
        self.assert_unchanged(sentinel, self.sentinel)

        removed = self.remove(run)
        self.assertEqual(removed["state"], "removed", removed)
        self.assertEqual(removed["removed"], [result["target"]])
        self.assertFalse(os.path.lexists(target))
        self.assertEqual(self.runs(), [])
        self.assertEqual(os.listdir(self.targets), [])
        self.assert_unchanged(project, p)
        self.assert_unchanged(sentinel, self.sentinel)

    def test_removal_deletes_links_inside_the_target_without_following_them(self):
        result, target = self.created()
        junction(target / "j-sentinel", self.sentinel)
        junction(target / "j-project", self.project)
        junction(write(target / "deep/inner/file.txt").parent / "j-again", self.sentinel)
        os.link(self.sentinel_file, target / "deep/hard.txt")    # read-only, link count 2
        os.chmod(write(target / "deep/readonly.txt"), stat.S_IREAD)
        os.chmod(target / "deep/inner", stat.S_IREAD)            # read-only directory
        with open(extended(target / "deep" / "CON"), "w") as device_name:  # reserved name made after the copy
            device_name.write("x")
        project, sentinel = snapshot(self.project), snapshot(self.sentinel)

        removed = self.remove(result["directory"])

        self.assertEqual(removed["state"], "removed", removed)
        self.assertFalse(os.path.lexists(target))
        self.assert_unchanged(sentinel, self.sentinel)
        self.assertTrue(os.stat(self.sentinel_file).st_file_attributes & READONLY, "attributes never changed")
        self.assertEqual(os.stat(self.sentinel_file).st_nlink, 1)
        self.assert_unchanged(project, self.project)

    def test_symbolic_links_are_skipped_on_copy_and_not_followed_on_removal(self):
        try:
            os.symlink(self.sentinel, self.project / "dir-link", target_is_directory=True)
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                self.skipTest("symlink creation needs SeCreateSymbolicLinkPrivilege or Developer Mode, "
                              "which this account does not have")
            raise
        os.symlink(self.sentinel_file, self.project / "file-link")
        os.symlink("..", self.project / "up", target_is_directory=True)
        project, sentinel = snapshot(self.project), snapshot(self.sentinel)
        result, target = self.created()
        self.assertEqual({s["path"] for s in result["skipped_links"]}, {"dir-link", "file-link", "up"})
        self.assertEqual({k for k in snapshot(target) if k != "."}, {"README.md"})
        os.symlink(self.sentinel, target / "dir-link", target_is_directory=True)
        os.symlink(self.sentinel_file, target / "file-link")
        os.symlink("..", target / "up", target_is_directory=True)
        self.assertEqual(self.remove(result["directory"])["state"], "removed")
        self.assertFalse(os.path.lexists(target))
        self.assert_unchanged(sentinel, self.sentinel)
        self.assert_unchanged(project, self.project)

    # --- removal guards ---

    def test_target_swapped_for_a_junction_after_create_is_refused(self):
        result, target = self.created()
        os.rename(target, str(target) + ".moved")
        junction(target, self.sentinel)
        sentinel = snapshot(self.sentinel)
        removed = self.remove(result["directory"])
        self.assertEqual(removed["state"], "failed", removed)
        self.assertIn("link or junction", removed["reason"])
        self.assertEqual(removed["retained_location"], result["target"])
        self.assertTrue(os.path.lexists(target))
        self.assert_unchanged(sentinel, self.sentinel)
        self.assertTrue((Path(result["directory"]) / "target.json").exists(), "the record is kept")

    def test_target_replaced_after_create_is_refused(self):
        result, target = self.created()
        os.rename(target, str(target) + ".moved")
        write(target / "user-file.txt", "someone else's directory")
        removed = self.remove(result["directory"])
        self.assertEqual(removed["state"], "failed", removed)
        self.assertIn("identity", removed["reason"])
        self.assertEqual(removed["retained_location"], result["target"])
        self.assertEqual((target / "user-file.txt").read_text(encoding="utf-8"), "someone else's directory")

    def test_recorded_path_outside_the_root_is_refused(self):
        result, target = self.created()
        record_path = Path(result["directory"]) / "target.json"
        sentinel = snapshot(self.sentinel)
        original = json.loads(record_path.read_text(encoding="utf-8"))
        moved = json.loads(json.dumps(original))
        moved["entries"][0]["path"] = str(self.sentinel)
        record_path.write_text(json.dumps(moved), encoding="utf-8")
        removed = self.remove(result["directory"])
        self.assertEqual(removed["state"], "failed", removed)
        self.assertIn("outside the recorded root", removed["reason"])
        self.assertEqual(removed["retained_location"], str(self.sentinel))
        # A root moved up to the sentinel's parent no longer matches its recorded identity.
        moved["root"]["path"] = str(self.root)
        record_path.write_text(json.dumps(moved), encoding="utf-8")
        removed = self.remove(result["directory"])
        self.assertEqual(removed["state"], "failed", removed)
        self.assertIn("root no longer matches", removed["reason"])
        self.assert_unchanged(sentinel, self.sentinel)
        self.assertTrue(target.exists())

    def test_removal_without_an_owned_record_is_refused(self):
        result, target = self.created()
        (Path(result["directory"]) / "target.json").unlink()
        sentinel = snapshot(self.sentinel)
        for directory, expected in ((result["directory"], "No target record"), (self.sentinel, "Not an owned run directory"),
                                    (self.base / "ask-codex", "Not an owned run directory")):
            removed = self.remove(directory)
            self.assertEqual(removed["state"], "failed", removed)
            self.assertIn(expected, removed["reason"])
            self.assertEqual(removed["retained_location"], str(directory))
        self.assertTrue(target.exists())
        self.assert_unchanged(sentinel, self.sentinel)

    # --- I1 refusals: nothing is written ---

    def test_create_refusals_write_nothing(self):
        targets = str(self.targets)
        write(self.root / "a-file.txt")
        junction(self.root / "root-junction", self.targets)
        write(self.root / "repo/.git/HEAD")
        (self.root / "repo/targets").mkdir()
        write(self.root / "codexed/.codex")
        (self.root / "codexed/targets").mkdir()
        (self.project / "inner").mkdir()
        write(self.targets / "taken-file")
        (self.targets / "taken-dir").mkdir()
        junction(self.targets / "taken-junction", self.sentinel)
        root = lambda path, **extra: {"target_root": {"path": str(path), "confirmed_by_user": True, **extra}}
        cases = [
            ({"target_root": {"path": targets}}, "confirmed by the user"),
            ({"target_root": {"path": targets, "confirmed_by_user": False}}, "confirmed by the user"),
            ({"target_root": {"path": targets, "confirmed_by_user": "true"}}, "confirmed by the user"),
            (root("targets"), "absolute path"),
            (root("D:targets"), "absolute path"),
            (root("\\\\127.0.0.1\\D$\\tmp"), "absolute path"),
            (root("\\\\?\\" + targets), "absolute path"),
            (root(str(self.targets) + "\\..\\targets"), "'..'"),
            (root(self.root / "missing"), "does not exist"),
            (root(self.root / "a-file.txt"), "not a directory"),
            (root(self.root / "root-junction"), "link or junction"),
            (root(self.project / "inner"), "neither inside the project nor contain it"),
            (root(self.project), "neither inside the project nor contain it"),
            (root(self.root), "neither inside the project nor contain it"),
            (root(self.root / "repo/targets"), "holds .git"),
            (root(self.root / "codexed/targets"), "holds .codex"),
            ({"target_name": "taken-file"}, "already exists"),
            ({"target_name": "taken-dir"}, "already exists"),
            ({"target_name": "taken-junction"}, "already exists"),
            ({"target_name": "a\\b"}, "one plain directory name"),
            ({"target_name": "CON"}, "one plain directory name"),
            ({"surprise": True}, "Unknown target request fields"),
            ({"env_files": ["..\\outside\\.env"]}, "Invalid env file path"),
            ({"env_files": [str(self.project / ".env")]}, "Invalid env file path"),
            ({"env_files": ["node_modules/pkg/.env"]}, "never copied"),
            ({"env_files": ["credentials/.env"]}, "never copied"),
            ({"env_files": ["notes.txt:hidden"]}, "Invalid env file path"),       # a name designating a stream
            ({"env_files": [".env.test::$DATA"]}, "Invalid env file path"),
            ({"exclude_names": ["a/b"]}, "plain file or directory name"),
            ({"exclude_names": ["dist:s"]}, "plain file or directory name"),
            ({"limits": {"max_entries": 0}}, "limits.max_entries"),
            ({"limits": {"max_bytes": True}}, "limits.max_bytes"),
            ({"limits": {"max_entries": 10 ** 9}}, "limits.max_entries"),
        ]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assert_refused_without_writes(self.request(**changes), expected)

    def test_root_inside_a_cloud_sync_folder_is_refused(self):
        for variable in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            with self.subTest(variable=variable):
                env = {k: v for k, v in self.env.items() if not k.lower().startswith("onedrive")}
                env[variable] = str(self.root)
                self.assert_refused_without_writes(self.request(), "cloud-sync", env=env)

    def test_root_off_a_local_fixed_drive_is_refused(self):
        sys.path.insert(0, str(SCRIPTS))
        import target
        original = target._drive_type
        self.addCleanup(setattr, target, "_drive_type", original)
        for kind in (2, 4, 5, 6):  # removable, remote, CD-ROM, RAM disk as reported by GetDriveTypeW
            target._drive_type = lambda path, kind=kind: kind
            with self.subTest(kind=kind), self.assertRaises(target.TargetError) as refused:
                target.create(self.request(), lambda: self.fail("nothing may be written"))
            self.assertIn("local fixed drive", str(refused.exception))
        self.assertEqual(self.runs(), [])
        self.assertEqual(os.listdir(self.targets), [])

    # --- I2 failures remove the partial target ---

    def assert_failed_and_cleaned(self, request, expected):
        result = self.create(request)
        self.assertEqual(result["state"], "failed", result)
        self.assertIn(expected.lower(), result["reason"].lower())
        self.assertIn("partial target was removed", result["reason"])
        self.assertTrue(result["target_removed"])
        self.assertNotIn("target", result, "never a fallback to the working tree")
        self.assertEqual(os.listdir(self.targets), [])
        self.assertEqual(self.runs(), [])
        return result

    def partial_project(self):
        for name in ("a-first.txt", "b-dir/one.txt", "b-dir/two.txt"):
            write(self.project / name, "copied before the failure")

    def test_copy_error_removes_the_partial_target(self):
        self.partial_project()
        locked = write(self.project / "z-locked.txt", "held without sharing")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.restype = ctypes.c_void_p
        kernel32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
                                         ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.CreateFileW(str(locked), 0x80000000, 0, None, 3, 0x80, None)
        self.assertNotIn(handle, (None, ctypes.c_void_p(-1).value), ctypes.get_last_error())
        try:
            project = snapshot(self.project / "b-dir")
            self.assert_failed_and_cleaned(self.request(), "copy failed")
            self.assert_unchanged(project, self.project / "b-dir")
        finally:
            kernel32.CloseHandle(handle)

    def test_reserved_name_fails_cleanly(self):
        self.partial_project()
        with open(extended(self.project / "b-dir" / "CON"), "w") as device_name:
            device_name.write("x")
        self.assert_failed_and_cleaned(self.request(), "reserved or invalid file name: b-dir/CON")

    def test_alternate_data_streams_are_never_copied_and_their_files_are_listed(self):
        downloaded = write(self.project / "downloaded.zip.txt", "main stream")
        with open(str(downloaded) + ":Zone.Identifier", "w") as stream:
            stream.write("[ZoneTransfer]\nZoneId=3\n")
        tagged = write(self.project / "docs/notes.txt", "notes")
        with open(str(tagged) + ":hidden", "w") as stream:
            stream.write("alternate stream content")
        os.mkdir(self.project / "tagged-dir")
        with open(str(self.project / "tagged-dir") + ":dirstream", "w") as stream:
            stream.write("directory stream")
        result, target = self.created()
        self.assertEqual(sorted(result["streams_not_copied"]), ["docs/notes.txt", "downloaded.zip.txt", "tagged-dir"])
        self.assertEqual((target / "downloaded.zip.txt").read_text(encoding="utf-8"), "main stream")
        self.assertEqual((target / "docs/notes.txt").read_text(encoding="utf-8"), "notes")
        for key, (kind, *_rest) in snapshot(target).items():
            if key != ".":
                self.assertEqual(named_streams(target / key), [], f"{key} carries a stream in the target")
        self.assertEqual(named_streams(downloaded), [":Zone.Identifier:$DATA"], "the source keeps its stream")
        self.assertEqual(self.remove(result["directory"])["state"], "removed")
        self.assertFalse(os.path.lexists(target))

    def test_overlong_path_fails_cleanly(self):
        self.partial_project()
        deep = Path(extended(self.project)).joinpath(*["d" * 60] * 4)
        os.makedirs(deep)
        with open(str(deep) + "\\leaf.txt", "w") as leaf:
            leaf.write("deep")
        self.assert_failed_and_cleaned(self.request(), "path too long")

    def test_limits_fail_cleanly(self):
        self.partial_project()
        self.assert_failed_and_cleaned(self.request(limits={"max_entries": 3}), "more than 3 entries")
        self.assert_failed_and_cleaned(self.request(limits={"max_bytes": 30}), "more than 30 bytes")

    def test_named_file_that_is_missing_fails_cleanly(self):
        self.partial_project()
        self.assert_failed_and_cleaned(self.request(env_files=["config/.env.test"]), "named file not found")

    # --- record discipline and the sibling MCP TEMP directories (I5 shape) ---

    def test_entries_are_recorded_before_creation_and_siblings_are_removed_under_the_same_rules(self):
        sys.path.insert(0, str(SCRIPTS))
        import target
        original = target._create_directory
        self.addCleanup(setattr, target, "_create_directory", original)
        seen = []

        def spy(parent, name):
            [record_file] = (self.base / "ask-codex").glob("run.*/target.json")
            record = json.loads(record_file.read_text(encoding="utf-8"))
            pending = [e for e in record["entries"] if e["path"].endswith("\\" + name) and e["state"] == "pending"]
            seen.append((name, len(pending)))
            return original(parent, name)

        target._create_directory = spy

        def make_run_directory():
            (self.base / "ask-codex").mkdir()
            return Path(tempfile.mkdtemp(prefix="run.", dir=self.base / "ask-codex")), True

        result = target.create(self.request(target_name="exercise-target"), make_run_directory)
        self.assertEqual(result["state"], "created", result)
        sibling = Path(target.create_sibling(result["directory"], "mcp-temp"))
        swapped = Path(target.create_sibling(result["directory"], "guard-temp"))
        self.assertEqual([n for n, count in seen if count != 1], [], "every directory was recorded before creation")
        self.assertEqual(len(seen), 3)
        self.assertEqual(sibling.parent, Path(result["target"]).parent)
        record = json.loads((Path(result["directory"]) / "target.json").read_text(encoding="utf-8"))
        self.assertEqual([(e["kind"], e["state"]) for e in record["entries"]],
                         [("target", "created"), ("temp", "created"), ("temp", "created")])
        self.assertTrue(all(e["volume_serial"] and e["file_id"] for e in record["entries"]))
        junction(sibling / "j-sentinel", self.sentinel)
        os.rename(swapped, str(swapped) + ".moved")
        junction(swapped, self.sentinel)
        sentinel = snapshot(self.sentinel)

        removed = self.remove(result["directory"])
        self.assertEqual(removed["state"], "failed", removed)
        self.assertEqual(removed["retained_location"], str(swapped))
        self.assertIn("link or junction", removed["reason"])
        self.assertFalse(os.path.lexists(sibling))
        self.assertFalse(os.path.lexists(result["target"]))
        self.assert_unchanged(sentinel, self.sentinel)
        record = json.loads((Path(result["directory"]) / "target.json").read_text(encoding="utf-8"))
        self.assertEqual([e["path"] for e in record["entries"]], [str(swapped)], "only the refused entry stays")

    # --- I13 ---

    def test_other_platforms_are_refused(self):
        result, target = self.created()
        bootstrap = ("import runpy, sys; script = sys.argv.pop(1); sys.path.insert(0, script.rsplit('\\\\', 1)[0]); "
                     "import consult, target; sys.platform = 'linux'; sys.argv[0] = script; "
                     "runpy.run_path(script, run_name='__main__')")
        runs, targets = self.runs(), snapshot(self.targets)
        path = self.requests / "request.json"
        path.write_text(json.dumps(self.request()), encoding="utf-8")
        for args in (("target-create", path, "--base", self.base), ("target-remove", result["directory"])):
            refused = self.call(*args, bootstrap=bootstrap)
            self.assertEqual(refused["state"], "failed", refused)
            self.assertIn("Windows only", refused["reason"])
        self.assertEqual(self.runs(), runs)
        self.assert_unchanged(targets, self.targets)
        self.assertTrue(target.exists())

    def test_no_environment_variable_reaches_a_check_other_than_sync_root_detection(self):
        tree = ast.parse((SCRIPTS / "target.py").read_text(encoding="utf-8"))
        reads = []
        for function in (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)):
            for node in ast.walk(function):
                if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv", "environb"):
                    reads.append(function.name)
        top_level = [n for n in tree.body if not isinstance(n, (ast.FunctionDef, ast.ClassDef))]
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv")
                             for stmt in top_level for n in ast.walk(stmt)))
        self.assertEqual(reads, ["_sync_roots"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--test-root", help="parent of the per-test directories (outside any repository)")
    known, rest = parser.parse_known_args()
    if known.test_root:
        TEST_ROOT = Path(known.test_root)
    unittest.main(argv=[sys.argv[0], *rest])
