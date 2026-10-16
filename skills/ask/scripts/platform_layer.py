"""Which platform layer an exercise operation uses (plan `.scratch/exercise-skills/plan.md` I13, R2-1, R2-2, N-1).

The exercise's platform layer is everything that needs Windows: the platform gate, the disposable target and its
sibling directories, the guard, the supervisor and the process checks, the reproduction's browser session and the
evidence move (C6), and attach mode's listener-table inspection (C8). Production uses the real layer and refuses
on every other platform. Claude evals run in WSL, where none of it can run; there the whole layer, gate included,
is replaced by an eval fake. The fake is selected by no environment variable. It is loaded only when all of this
holds, checked on every selection:

- `<plugin root>/.eval-stub/` exists and is a plain directory (no link), and holds the fake as a regular file;
- `codex`, looked up on the PATH of the environment the script runs Codex with (consult.shell_environment(), N-1),
  resolves first to `<plugin root>/.eval-stub/codex`, a regular file (no link);
- `codex --version`, run the way the script runs every Codex command (consult.command), prints exactly
  `codex-cli 0.0.0-stub`;
- the fake replaces exactly the names in REPLACED, no more and no fewer.

When `.eval-stub/` exists and any of that fails, every exercise operation refuses (R2-2): a `.eval-stub/` left
behind by a killed eval runner never swaps the real layer in a development checkout. `run-evals.sh` creates and
removes `.eval-stub/` (same trust as the plugin's own code). Once the fake is installed in a process it stays for
that process (CLI calls are short-lived), so real and fake pieces never mix.

What the fake leaves to production code: request validation, the lifecycle and its state checks, the browser server
definition (I5) and the MCP guard against the stub Codex (I6), the Codex launch, wait, stop, collect with
redaction (I11), finish's ordering, and the reproduction's step validation, origin check, element resolution, step
order and redaction (I10, I11) and the evidence references' checks (I9).
"""
import importlib.util
import os
from pathlib import Path
import stat
import sys

PLUGIN_ROOT = Path(__file__).resolve().parents[3]  # <root>/skills/ask/scripts/platform_layer.py
STUB_DIR = ".eval-stub"
FAKE_FILE = "exercise_platform_fake.py"
STUB_VERSION = "codex-cli 0.0.0-stub"

# module -> the names the fake replaces in it (setattr on the loaded module, so every caller sees the fake).
REPLACED = {
    "target": ("create", "create_sibling", "remove"),
    "exercise": ("_new_run_directory", "make_evidence", "verify_entries", "claim_run"),
    "browser": ("node_executable", "entry_script", "local_app_data", "free_loopback_port"),
    "guard": ("guard_exercise", "require_current_pass", "dependency_report"),
    "supervisor": ("launch", "wait_started", "require_started", "Watcher", "own_processes", "codex_processes_ended",
                   "end_app", "run_alive"),
    "repro": ("open_session", "move_files"),
    "attach": ("examine", "protected_pids"),  # attach mode (C8): the listener table and its owners
}

_installed = None  # the fake module once installed in this process


def _plain(path, directory):
    try:
        status = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(status.st_mode) or getattr(status, "st_file_attributes", 0) & 0x400:
        return False
    return stat.S_ISDIR(status.st_mode) if directory else stat.S_ISREG(status.st_mode)


def _same(a, b):
    a, b = os.path.normcase(os.path.abspath(a)), os.path.normcase(os.path.abspath(b))
    if a == b:
        return True
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def resolve_codex(env):
    """The first `codex` on the absolute entries of env's PATH (also `codex.exe` on Windows), or None."""
    names = ("codex", "codex.exe") if os.name == "nt" else ("codex",)
    for entry in env.get("PATH", "").split(os.pathsep):
        entry = entry.strip().strip('"')
        if not entry or not os.path.isabs(entry):
            continue
        for name in names:
            candidate = os.path.join(entry, name)
            if os.path.isfile(candidate):
                return candidate
    return None


def stub_check(cli, root=None):
    """None when `<root>/.eval-stub/` is absent; else the fake's path when the stub check passes; else ValueError."""
    root = Path(root or PLUGIN_ROOT)
    stub = root / STUB_DIR
    if not os.path.lexists(stub):
        return None
    refused = (f"{stub} exists but the eval stub check failed ({{}}); every exercise operation is refused. "
               "Remove it if no eval run is in progress")
    fake, codex = stub / FAKE_FILE, stub / "codex"
    if not _plain(stub, True) or not _plain(fake, False) or not _plain(codex, False):
        raise ValueError(refused.format("it is not a plain directory holding the stub codex and the fake"))
    found = resolve_codex(cli.shell_environment())
    if found is None or not _same(found, codex):
        raise ValueError(refused.format(f"codex resolves to {found or 'nothing'}, not {codex}"))
    try:
        version = cli.command(["codex", "--version"], str(stub)).strip()
    except (OSError, ValueError) as error:
        raise ValueError(refused.format(f"codex --version failed: {error}")) from None
    if version != STUB_VERSION:
        raise ValueError(refused.format(f"codex reports {version[:80]!r}, not {STUB_VERSION!r}"))
    return fake


def _cli():
    import consult  # lazily: consult imports exercise, which imports this module
    return consult


def select(cli=None, root=None):
    """True when the eval fake is the platform layer (installed now or earlier in this process), False for the real
    layer; ValueError when `.eval-stub/` exists and the stub check fails."""
    global _installed
    if _installed is not None:
        return True
    if not os.path.lexists(Path(root or PLUGIN_ROOT) / STUB_DIR):
        return False
    fake_path = stub_check(cli or _cli(), root)
    spec = importlib.util.spec_from_file_location("ask_codex_exercise_platform_fake", fake_path)
    fake = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake)
    replacements = getattr(fake, "REPLACEMENTS", None)
    if not isinstance(replacements, dict) or {m: set(v) for m, v in replacements.items()} != \
            {m: set(v) for m, v in REPLACED.items()}:
        raise ValueError("The eval fake does not replace exactly the exercise platform layer; every exercise "
                         "operation is refused")
    for module_name, names in REPLACED.items():
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        for name in names:
            setattr(module, name, replacements[module_name][name])
    _installed = fake
    return True
