"""The browser MCP server definition of an exercise (plan I5) and its owned proxy port.

One function, `instantiate(template(...), ...)`, produces the definition for the exercise, the guard (C3) and
the reproduction (C6). The template keeps the app host:ports and the headed flag and holds placeholders for
the per-run values (`<nonce>`, `<target>`, `<cwd>`, `<temp>`, `<profile>`, `<proxy port>`), so the guard
fingerprint (I7) can be taken over it.

Chrome profile (U16): chrome-devtools-mcp 1.10.1 sets no download behaviour, so with `--isolated` a download landed
in the user's Downloads folder. The definition therefore names a run-owned profile directory with
`--userDataDir=<profile>` (never `--isolated`, and never any other `--userDataDir`); the directory follows the
run-owned `TEMP` rule (a recorded sibling of the target) and is seeded before launch with `Default/Preferences` =
PREFERENCES, which blocks every download (`download_restrictions` = 3). `seed_profile` writes it into the fresh,
empty directory; `profile_problems` checks, before every launch, that the directory holds exactly that seed.

The definition reaches Codex as `-c mcp_servers.<nonce>.<field>=<TOML value>` (`config_overrides`). The
approval keys are not part of the definition: `approval_constants(name)` generates them from the literal TOOLS
list at command-line build time only, so they never appear in overrides, the prepared summary or plan.json
(A5). `codex mcp get` does not print them (codex-cli 0.159.3, also not `default_tools_approval_mode`).

The node entry script is the one chrome-devtools-mcp 1.10.1 package the script installs under the user-level
ask-codex state directory (install.py installs it with `npm install --ignore-scripts`; `entry_script()` verifies
the whole install against the committed hash manifest before every use). The state directory is the Local
AppData known folder (SHGetKnownFolderPath), never an environment variable (I13).
"""
import ctypes
import json
import ntpath
import os
from pathlib import Path
import re
import socket
import threading

PACKAGE = "chrome-devtools-mcp"
VERSION = "1.10.1"
ENTRY = ("node_modules", PACKAGE, "build", "src", "bin", "chrome-devtools-mcp.js")
STARTUP_TIMEOUT_SEC = 90
VIEWPORT = "1280x720"
NAME_PREFIX = "cdt_"
NAME = re.compile(r"^cdt_[0-9a-f]{16}$")

# The spec's tool allowlist (spec "Tool allowlist"); never generated. Not exposed: upload_file,
# take_heapsnapshot, performance_*, evaluate_script and anything a later release adds.
TOOLS = ("navigate_page", "new_page", "list_pages", "select_page", "close_page", "take_screenshot", "take_snapshot",
         "click", "hover", "fill", "fill_form", "type_text", "press_key", "drag", "handle_dialog", "wait_for",
         "resize_page", "emulate", "list_console_messages", "get_console_message", "list_network_requests",
         "get_network_request", "get_css_styles", "lighthouse_audit")

# Placeholders of the template; per-run values replace them in instantiate().
NONCE, TARGET, CWD, TEMP, PROFILE, PROXY_PORT = "<nonce>", "<target>", "<cwd>", "<temp>", "<profile>", "<proxy port>"

# Never in the argument list (I5); `--userDataDir` only as the one run-owned profile (never_listed).
NEVER = ("--config", "--browserUrl", "--browser-url", "--wsEndpoint", "--ws-endpoint", "--autoConnect",
         "--auto-connect", "--isolated", "--userDataDir", "--user-data-dir", "--acceptInsecureCerts",
         "--accept-insecure-certs", "--allowUnrestrictedPaths", "--allow-unrestricted-paths", "--slim", "--category",
         "--experimental")
# The seeded profile preferences (U16): every download is blocked.
PREFERENCES = {"download_restrictions": 3}
PREFERENCES_BYTES = json.dumps(PREFERENCES).encode("utf-8")


def _posix(path):
    # Every path of the definition is in forward-slash form, as consult.py passes every path to Codex: Git's
    # bin/bash.exe launcher (the run.sh hop) turns `\\` into `\` inside an argument holding `"`, while the guard's
    # `codex mcp` calls do not cross it, so a backslash would make the guard check another value than Codex gets.
    return str(path).replace("\\", "/")


def template(app, headed, node, entry):
    """The definition with per-run placeholders; `app` is the list of `host:port` strings (validated)."""
    args = [_posix(entry), f"--userDataDir={PROFILE}"]
    if not headed:
        args.append("--headless")
    args += ["--no-javascript-evaluation", "--no-usage-statistics", "--no-performance-crux", "--redactNetworkHeaders",
             f"--filesystemRoot={TARGET}/evidence", f"--viewport={VIEWPORT}"]
    args += [f"--allowedUrlPattern=http://{origin}/*" for origin in app]
    args += [f"--proxyServer=http://127.0.0.1:{PROXY_PORT}",
             "--chromeArg=--proxy-bypass-list=" + ";".join(["<-loopback>", *app]),
             "--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp"]
    return {"name": NONCE, "command": _posix(node), "args": args, "cwd": CWD,
            "env": {"CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY": "1", "CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS": "1",
                    # Documented by 1.10.1's README ("Update checks"): no npm registry call, no ~/.cache write (F10).
                    "CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS": "1",
                    "NODE_OPTIONS": "", "TEMP": TEMP, "TMP": TEMP},
            "startup_timeout_sec": STARTUP_TIMEOUT_SEC, "enabled_tools": list(TOOLS)}


def instantiate(definition, nonce, target, cwd, temp, proxy_port, profile):
    """The template with every placeholder replaced; refuses values that could alter the structure."""
    if not NAME.fullmatch(nonce):
        raise ValueError("Invalid browser server name")
    if type(proxy_port) is not int or not 1024 <= proxy_port <= 65535:
        raise ValueError("Invalid owned proxy port")
    values = {NONCE: nonce, TARGET: _posix(target), CWD: _posix(cwd), TEMP: _posix(temp), PROFILE: _posix(profile),
              PROXY_PORT: str(proxy_port)}
    for value in values.values():
        if any(p in value for p in values) or any(c in value for c in "\0\r\n"):
            raise ValueError("A per-run value of the browser server definition is not allowed")

    def fill(value):
        if isinstance(value, str):
            for placeholder, actual in values.items():
                value = value.replace(placeholder, actual)
            return value
        if isinstance(value, list):
            return [fill(item) for item in value]
        if isinstance(value, dict):
            return {key: fill(item) for key, item in value.items()}
        return value

    return fill(definition)


def _toml(value):
    # JSON strings and arrays of strings are TOML values; raw (not \u-escaped) characters keep non-BMP text valid.
    return json.dumps(value, ensure_ascii=False)


def config_overrides(definition):
    """The definition as `-c mcp_servers.<name>.<field>=<value>` pairs (approval keys excluded, see module doc)."""
    name = definition["name"]
    if not NAME.fullmatch(name):
        raise ValueError("Invalid browser server name")
    env = ",".join(f"{key}={_toml(value)}" for key, value in definition["env"].items())
    pairs = ["-c", f"mcp_servers.{name}.command={_toml(definition['command'])}",
             "-c", f"mcp_servers.{name}.args={_toml(definition['args'])}",
             "-c", f"mcp_servers.{name}.cwd={_toml(definition['cwd'])}",
             "-c", f"mcp_servers.{name}.env={{{env}}}",
             "-c", f"mcp_servers.{name}.startup_timeout_sec={int(definition['startup_timeout_sec'])}",
             "-c", f"mcp_servers.{name}.enabled_tools={_toml(definition['enabled_tools'])}"]
    if any("\\" in value for value in pairs):
        raise ValueError("A browser server value holds a backslash; the guard and Codex would not see the same value")
    return pairs


def approval_constants(name):
    """Per-tool approval for exactly TOOLS and the server default pinned to prompt (B1, A4); exec constants."""
    if not NAME.fullmatch(name):
        raise ValueError("Invalid browser server name")
    pairs = []
    for tool in TOOLS:
        pairs += ["-c", f'mcp_servers.{name}.tools.{tool}.approval_mode="approve"']
    return pairs + ["-c", f'mcp_servers.{name}.default_tools_approval_mode="prompt"']


def never_listed(definition, profile=PROFILE):
    """Arguments of the definition that the never-list forbids (empty when the definition is sound). Exactly one
    `--userDataDir=<profile>` naming the run-owned profile directory (`profile`, the placeholder for a template) is
    required and allowed; `--isolated`, any other user data directory and a second one are forbidden."""
    allowed = f"--userDataDir={_posix(profile)}"
    found = [arg for arg in definition["args"] if any(arg == flag or arg.startswith(flag) for flag in NEVER)]
    if allowed in found:
        found.remove(allowed)  # one occurrence is the required profile; a second one stays forbidden
    else:
        found.append(f"(missing) {allowed}")
    return found


def seed_profile(profile):
    """Write Default/Preferences = PREFERENCES into the fresh, empty run-owned profile directory (exclusive creates,
    nothing followed: the directory itself must be a plain empty directory)."""
    status = os.lstat(profile)
    if getattr(status, "st_file_attributes", 0) & 0x400 or not os.path.isdir(profile) or os.listdir(profile):
        raise ValueError("The browser profile directory is not a fresh, empty, plain directory")
    os.mkdir(os.path.join(profile, "Default"))
    with open(os.path.join(profile, "Default", "Preferences"), "xb") as preferences:
        preferences.write(PREFERENCES_BYTES)


def profile_problems(profile):
    """Before a launch: the profile directory holds exactly the seed (Default/Preferences with PREFERENCES), plain
    directories and a regular file only."""
    def plain(path, directory):
        status = os.lstat(path)
        if getattr(status, "st_file_attributes", 0) & 0x400:
            return False
        return os.path.isdir(path) if directory else os.path.isfile(path)
    try:
        default = os.path.join(profile, "Default")
        preferences = os.path.join(default, "Preferences")
        if not plain(profile, True) or os.listdir(profile) != ["Default"] or not plain(default, True) or \
                os.listdir(default) != ["Preferences"] or not plain(preferences, False):
            return ["the browser profile directory does not hold exactly Default/Preferences"]
        with open(preferences, "rb") as source:
            if source.read() != PREFERENCES_BYTES:
                return ["the browser profile's Default/Preferences is not the seed that blocks downloads"]
    except OSError:
        return ["the browser profile directory cannot be checked"]
    return []


# --- user-level state directory (Windows known folder; no environment variable) ---

class _Guid(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16),
                ("Data4", ctypes.c_ubyte * 8)]


_LOCAL_APP_DATA = (0xF1B32785, 0x6FBA, 0x4FCF, (0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91))


def local_app_data():
    """FOLDERID_LocalAppData through SHGetKnownFolderPath."""
    shell32, ole32 = ctypes.WinDLL("shell32"), ctypes.WinDLL("ole32")
    shell32.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(_Guid), ctypes.c_uint32, ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_wchar_p)]
    shell32.SHGetKnownFolderPath.restype = ctypes.c_long
    ole32.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    d1, d2, d3, d4 = _LOCAL_APP_DATA
    guid, path = _Guid(d1, d2, d3, (ctypes.c_ubyte * 8)(*d4)), ctypes.c_wchar_p()
    if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path)) != 0:
        raise ValueError("The Local AppData folder cannot be determined")
    try:
        return Path(path.value)
    finally:
        ole32.CoTaskMemFree(path)


def state_directory():
    """The user-level ask-codex state directory (package install and guard cache live here, never in a project)."""
    return local_app_data() / "ask-codex"


def install_directory():
    return state_directory() / f"{PACKAGE}-{VERSION}"


def guard_cache_directory():
    return state_directory() / "guard-cache"


def entry_script():
    """The installed entry script, after verifying the whole install against the committed manifest (install.py,
    I5: before every use; any difference refuses)."""
    import install  # install imports this module
    install.verify_installed()
    entry = install_directory().joinpath(*ENTRY)
    try:
        status = os.lstat(entry)
    except OSError:
        raise ValueError(f"The browser server ({PACKAGE} {VERSION}) is not installed; run /ask-codex:setup") from None
    if getattr(status, "st_file_attributes", 0) & 0x400 or not os.path.isfile(entry):
        raise ValueError("The browser server entry script is not a regular file")
    return entry


def node_executable(which):
    """Absolute node.exe found by `which` (the script's own PATH lookup for the run environment)."""
    found = which("node")
    if not found:
        raise ValueError("node is required for exercises and was not found")
    found = Path(found)
    if not found.is_absolute() or found.suffix.lower() != ".exe" or not found.is_file():
        raise ValueError("node must resolve to an absolute node.exe")
    return found


# --- owned proxy port (a closed proxy: every connection accepted and closed at once) ---

def free_loopback_port():
    """A port free on 127.0.0.1 now; the exercise binds it exclusively when a browser may run."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class ProxyHolder:
    """Holds the owned proxy port: an exclusive loopback listener that accepts and closes every connection."""

    def __init__(self, port):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            self.socket.set_inheritable(False)
            self.socket.bind(("127.0.0.1", port))
            self.socket.listen(64)
        except OSError:
            self.socket.close()
            raise ValueError(f"The owned proxy port 127.0.0.1:{port} is not free; the exercise does not start") from None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while True:
            try:
                connection, _ = self.socket.accept()
            except OSError:
                return
            try:
                connection.close()
            except OSError:
                pass

    def close(self):
        try:
            self.socket.close()
        except OSError:
            pass
        self.thread.join(timeout=2)


# --- placement of the run-owned directories (R4-1) ---

def _parts(path):
    return [p for p in ntpath.normpath(str(path)).casefold().split("\\") if p]


def related(a, b):
    """True when a equals b or either contains the other (case-insensitive, Windows paths)."""
    x, y = _parts(a), _parts(b)
    n = min(len(x), len(y))
    return x[:n] == y[:n]
