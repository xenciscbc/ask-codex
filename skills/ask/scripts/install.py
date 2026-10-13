"""The pinned browser MCP server package (plan I5): install and verification. Windows only.

The package is described by three committed files under `skills/ask/browser-server/`: `package.json` (exactly
chrome-devtools-mcp 1.10.1), `package-lock.json` (resolved tarball and its sha512 integrity) and `manifest.json`
(the SHA-256 of every file the install produces, relative paths with forward slashes).

`install()` (consult.py `browser-install`, used by /ask-codex:setup) runs, from a fresh staging directory under
the user-level ask-codex state directory, `node <npm-cli.js> install --ignore-scripts --no-audit --no-fund`
(node launched directly, no shell; no lifecycle script runs), verifies the staging directory against the
manifest and only then renames it to the install directory. An existing install directory is never replaced:
it is verified, and a difference is reported with the directory to remove by hand.

`verify()` runs before every use of the entry script (prepare, guard, run): the install directory, and every
entry inside it, must be a plain directory or a regular file (no reparse point of any kind), the set of files
must equal the manifest's exactly and every file's SHA-256 must match. Any difference refuses. It returns the
SHA-256 of the committed manifest, which is part of the guard fingerprint (I7).

No environment variable selects or skips any of this (I13): the state directory is the Local AppData known
folder (browser.state_directory); tests pass their own directory as an argument.
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess

import browser
import target as disposable_target

HERE = Path(__file__).resolve().parent
PACKAGE_DIR = HERE.parent / "browser-server"
MANIFEST = PACKAGE_DIR / "manifest.json"
PACKAGE_FILES = ("package.json", "package-lock.json")
REPARSE = 0x400
INSTALL_TIMEOUT_S = 300


class InstallError(ValueError):
    pass


def _plain_directory(path, what):
    try:
        status = os.lstat(path)
    except OSError:
        raise InstallError(f"{what} does not exist: {path}") from None
    if getattr(status, "st_file_attributes", 0) & REPARSE or not stat.S_ISDIR(status.st_mode):
        raise InstallError(f"{what} is not a plain directory (a link, junction or file): {path}")


def files_of(directory):
    """{relative posix path: sha256} for every file under `directory`; refuses any reparse point or other kind."""
    found = {}

    def walk(path, prefix):
        with os.scandir(path) as entries:
            listing = sorted(entries, key=lambda e: e.name)
        for entry in listing:
            status = entry.stat(follow_symlinks=False)
            relative = f"{prefix}{entry.name}"
            if getattr(status, "st_file_attributes", 0) & REPARSE:
                raise InstallError(f"The browser server install holds a link or junction: {relative}")
            if stat.S_ISDIR(status.st_mode):
                walk(entry.path, relative + "/")
            elif stat.S_ISREG(status.st_mode):
                digest = hashlib.sha256()
                with open(entry.path, "rb") as source:
                    for block in iter(lambda: source.read(1 << 20), b""):
                        digest.update(block)
                found[relative] = digest.hexdigest()
            else:
                raise InstallError(f"The browser server install holds an entry that is not a regular file: {relative}")

    walk(directory, "")
    return found


def manifest():
    """The committed manifest and the SHA-256 of its bytes."""
    data = MANIFEST.read_bytes()
    parsed = json.loads(data)
    if parsed.get("package") != browser.PACKAGE or parsed.get("version") != browser.VERSION or \
            not isinstance(parsed.get("files"), dict) or not parsed["files"]:
        raise InstallError("The committed browser server manifest is not for the pinned package")
    return parsed, hashlib.sha256(data).hexdigest()


def compare(directory, expected):
    """Differences between the files under `directory` and the manifest's file map (empty when equal)."""
    actual = files_of(directory)
    problems = [f"missing: {name}" for name in sorted(set(expected) - set(actual))]
    problems += [f"not in the manifest: {name}" for name in sorted(set(actual) - set(expected))]
    problems += [f"changed: {name}" for name in sorted(set(expected) & set(actual)) if expected[name] != actual[name]]
    return problems


def verify(state_dir=None):
    """Verify the install directory against the committed manifest; returns the manifest's SHA-256."""
    directory = (Path(state_dir) if state_dir else browser.state_directory()) / f"{browser.PACKAGE}-{browser.VERSION}"
    expected, digest = manifest()
    if not os.path.lexists(directory):
        raise InstallError(f"The browser server ({browser.PACKAGE} {browser.VERSION}) is not installed; "
                           "run /ask-codex:setup")
    _plain_directory(directory.parent, "The ask-codex state directory")
    _plain_directory(directory, "The browser server install directory")
    problems = compare(directory, expected["files"])
    if problems:
        shown = "; ".join(problems[:5]) + (f"; and {len(problems) - 5} more" if len(problems) > 5 else "")
        raise InstallError(f"The installed browser server differs from the committed manifest ({shown}); "
                           f"nothing is started. Remove {directory} and run /ask-codex:setup again")
    return digest


def verify_installed():
    """verify() of the user-level install, as every use calls it (browser.entry_script, the guard fingerprint)."""
    return verify(None)


def _remove_tree(path):
    """Remove a staging directory; reparse points inside are unlinked, never followed."""
    status = os.lstat(path)
    if getattr(status, "st_file_attributes", 0) & REPARSE:
        (os.rmdir if stat.S_ISDIR(status.st_mode) else os.unlink)(path)
    elif stat.S_ISDIR(status.st_mode):
        for entry in os.scandir(path):
            _remove_tree(entry.path)
        os.rmdir(path)
    else:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)  # npm output only (the staging directory is script-owned)
        os.unlink(path)


def npm_cli(node):
    """npm's own entry script beside node.exe (run with node directly; no npm.cmd, no shell)."""
    candidate = Path(node).parent / "node_modules" / "npm" / "bin" / "npm-cli.js"
    if not candidate.is_file():
        raise InstallError("npm was not found beside node.exe; install Node.js with npm")
    return candidate


def install(cli, state_dir=None):
    """Install the pinned package into the user-level state directory (see module doc)."""
    disposable_target.require_windows()
    state = Path(state_dir) if state_dir else browser.state_directory()
    final = state / f"{browser.PACKAGE}-{browser.VERSION}"
    expected, _ = manifest()
    if os.path.lexists(final):
        return {"state": "installed", "directory": str(final), "manifest_sha256": verify(state), "changed": False}
    state.mkdir(parents=True, exist_ok=True)
    _plain_directory(state, "The ask-codex state directory")
    node = browser.node_executable(cli.which)
    staging = state / f"{browser.PACKAGE}-{browser.VERSION}.staging-{secrets.token_hex(8)}"
    staging.mkdir()  # exclusive create
    try:
        for name in PACKAGE_FILES:
            (staging / name).write_bytes((PACKAGE_DIR / name).read_bytes())
        result = subprocess.run([str(node), str(npm_cli(node)), "install", "--ignore-scripts", "--no-audit",
                                 "--no-fund", "--no-update-notifier"],
                                cwd=staging, env=cli.shell_environment(), capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=INSTALL_TIMEOUT_S)
        if result.returncode:
            raise InstallError(f"npm install failed (exit {result.returncode}): {result.stderr.strip()[-600:]}")
        problems = compare(staging, expected["files"])
        if problems:
            raise InstallError("The freshly installed browser server differs from the committed manifest ("
                               + "; ".join(problems[:5]) + "); nothing was installed")
        os.rename(staging, final)
    except BaseException:
        try:
            _remove_tree(staging)
        except OSError:
            pass
        raise
    return {"state": "installed", "directory": str(final), "manifest_sha256": verify(state), "changed": True}


def write_manifest(directory):
    """Maintainer helper (never called by the skill): the manifest of a fresh, reviewed install directory."""
    MANIFEST.write_text(json.dumps({"package": browser.PACKAGE, "version": browser.VERSION,
                                    "installed_with": "npm install --ignore-scripts",
                                    "files": files_of(Path(directory))}, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
