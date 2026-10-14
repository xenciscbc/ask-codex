"""Reproduction of bug claims and the exercise's evidence (plan `.scratch/exercise-skills/plan.md` claim C6; I9 evidence
resolution and move, I10, I11 repro side, I12: reproduction and evidence handling come between collect and finish).

    consult.py repro <run directory> <steps file> [--result <file>]
    consult.py evidence-keep <run directory> <keep file>

Both run after `collect` of a completed run (the run directory holds `collected`) and before `finish`, while the
target, its evidence directory and the app are kept (I12). Windows only (I13): the browser session (`open_session`)
and the evidence move (`move_files`) are the platform layer's; the eval fake replaces exactly those two names.

Reproduction (I10). One call runs one step list in one browser session: the exercise's own browser server definition
(browser.template with the exercise's app host:ports and headed flag, i.e. the template whose fingerprint the guard
passed; `run` and this call both require that pass), instantiated with this call's own nonce, its own recorded
sibling directories `repro-temp`, `repro-cwd` and `repro-profile` (I5's placement rule; the profile seeded to block
downloads, U16), its own owned proxy port (a listener held here for the whole session) and its own kill-on-close job.
The job's name is registered in `<run directory>/repro-jobs/<job name>` before node starts, so a bound or `finish`
ends it before the app job (I8, supervisor.end_repro_jobs); node is created suspended, assigned and resumed. The
MCP client declares Codex 0.159.3's capabilities (mcp_stdio, A2). At the end the job is ended and confirmed (no
active process); only then is the registration removed.

Steps file (unknown keys are refused):

    {"claim": "C1", "steps": [<step>, ...]}   (1 to MAX_STEPS steps; "claim" optional, C<n>)
    <step> = {"action": "<action>", <its fields>}
    <element> = {"role": "<role>", "name": "<accessible name>"} or {"text": "<visible text>"}

    navigate        url (http://<app host:port>/..., the origin exactly one of the exercise's app host:ports)
    take_snapshot
    click           element, double (optional, bool)
    fill            element, value
    hover           element
    press_key       key
    drag            from (element), to (element)
    handle_dialog   response ("accept" | "dismiss"), prompt_text (optional)
    wait_for        text (a string or 1 to 5 strings), timeout_ms (optional, 1 to 30000; default 10000)
    resize_page     width, height (200 to 4000)
    take_screenshot full_page (optional, bool)
    list_console_messages, get_console_message (msgid), list_network_requests, get_network_request (reqid)

The step list is checked whole before anything starts. Any step outside that closed set (another action, an unknown
or ill-typed field, a URL whose origin is not an app host:port) refuses the whole list: no browser starts, no step
runs, and each such step is reported "not confirmed: outside the exercise boundary" (state `refused`). Then the steps
run in order. An element is resolved from a snapshot taken just before its step (the latest snapshot): exactly one
node whose role (case-insensitive) and accessible name (exact) match, or, for `text`, exactly one node other than the
document (whose name is the page title) whose name is that text; no match or several matches fail the step. The first failing step ends the run; the steps after it are
`not run` (state `step_failed`); all steps passing gives state `completed`. After each step that ran a screenshot is
saved as `<target>/evidence/repro-<token>-<nn>.png` (`take_screenshot` steps save theirs there too); the result is
also written as `<target>/evidence/repro-<token>.json`. Every string of the result is redacted (I11, redact.py)
before it is written or returned; each tool output is redacted, then cut to a bound.

Evidence (I9). `evidence-keep` moves chosen evidence files out of the target before `finish` removes it:

    {"destination": "<absolute local directory the user named>", "files": ["<reference>", ...]}

A reference names a file relative to `<target>/evidence` (`shot.png`, `sub/shot.png`); refused: empty, absolute,
UNC or device forms, drive-relative (`D:x`), `.`/`..` or empty components, a stream (`:`), reserved or invalid
names. It resolves through handles opened relative to the recorded target, never following a link: every directory
on the way must be a plain directory, the file a regular file (no reparse point) with one link only. The destination
must be an existing plain directory on a local drive, outside the target, its recorded siblings and the run
directory. Each file is copied into a new file the script names itself
(`ask-codex-evidence-<time>-<nn>-<safe name>`, created exclusively: nothing is ever overwritten), then deleted from
the evidence directory. Nothing here reads an environment variable (I13).
"""
import contextlib
import json
import ntpath
import os
from pathlib import Path
import re
import secrets
import threading
import time
from urllib.parse import urlsplit

import browser
from redact import redact, redact_value

BOUNDARY = "not confirmed: outside the exercise boundary"
MAX_STEPS = 40
MAX_SECONDS = 420            # one call's bound for its steps, counted from its start (a foreground call ends < 600 s)
TOOL_TIMEOUT = 60
WAIT_DEFAULT_MS, WAIT_MAX_MS = 10000, 30000
OUTPUT_LIMIT, SNAPSHOT_LIMIT = 6000, 20000
MAX_KEEP_FILES, MAX_KEEP_BYTES = 50, 64 * 1024 ** 2
ROLE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,39}$")
CLAIM = re.compile(r"^C[1-9][0-9]{0,2}$")
NODE = re.compile(r"^\s*uid=(\S+)(?: (.*))?$")
REGISTRY = "repro-jobs"
SAFE = re.compile(r"[^A-Za-z0-9._-]")

# The closed action set (I10): action -> {field: (kind, required)}.
ACTIONS = {
    "navigate": {"url": ("url", True)},
    "take_snapshot": {},
    "click": {"element": ("element", True), "double": ("bool", False)},
    "fill": {"element": ("element", True), "value": ("value", True)},
    "hover": {"element": ("element", True)},
    "press_key": {"key": ("key", True)},
    "drag": {"from": ("element", True), "to": ("element", True)},
    "handle_dialog": {"response": ("dialog", True), "prompt_text": ("value", False)},
    "wait_for": {"text": ("texts", True), "timeout_ms": ("timeout", False)},
    "resize_page": {"width": ("dimension", True), "height": ("dimension", True)},
    "take_screenshot": {"full_page": ("bool", False)},
    "list_console_messages": {},
    "get_console_message": {"msgid": ("id", True)},
    "list_network_requests": {},
    "get_network_request": {"reqid": ("id", True)},
}
# The MCP tools a reproduction calls (all inside the exercise's enabled_tools).
TOOLS = ("list_pages", "navigate_page", "take_snapshot", "click", "fill", "hover", "press_key", "drag",
         "handle_dialog", "wait_for", "resize_page", "take_screenshot", "list_console_messages",
         "get_console_message", "list_network_requests", "get_network_request")


# --- the steps file (pure; production code also under the eval fake) ---

def _line(value, limit):
    return isinstance(value, str) and 0 < len(value) <= limit and not any(c in value for c in "\0\r\n")


def element_problem(value):
    if isinstance(value, dict) and set(value) == {"role", "name"}:
        if isinstance(value["role"], str) and ROLE.fullmatch(value["role"]) and _line(value["name"], 300):
            return None
    elif isinstance(value, dict) and set(value) == {"text"}:
        if _line(value["text"], 300):
            return None
    return 'an element is {"role": "<role>", "name": "<accessible name>"} or {"text": "<visible text>"}'


def app_origin(url, app):
    """The URL's origin when it is exactly one of the app host:ports over http, else None."""
    if not isinstance(url, str) or not 0 < len(url) <= 2000 or \
            any(ord(c) <= 32 or ord(c) >= 127 or c == "\\" for c in url):
        return None
    parts = urlsplit(url)
    if parts.scheme != "http" or "@" in parts.netloc:
        return None
    try:
        if parts.port is None:
            return None
    except ValueError:
        return None
    netloc = parts.netloc.lower()
    return netloc if netloc in {origin.lower() for origin in app} else None


def _field_problem(kind, value, app):
    if kind == "element":
        return element_problem(value)
    if kind == "url":
        return None if app_origin(value, app) else \
            "the URL's origin is not one of the app's host:ports (http://<host:port> as confirmed)"
    if kind == "bool":
        return None if isinstance(value, bool) else "must be true or false"
    if kind == "value":
        return None if isinstance(value, str) and len(value) <= 2000 and "\0" not in value else \
            "must be text of at most 2000 characters"
    if kind == "key":
        return None if _line(value, 64) else "must be one key or key combination"
    if kind == "dialog":
        return None if value in ("accept", "dismiss") else 'must be "accept" or "dismiss"'
    if kind == "texts":
        texts = [value] if isinstance(value, str) else value
        return None if isinstance(texts, list) and 1 <= len(texts) <= 5 and all(_line(t, 500) for t in texts) else \
            "must be a text or 1 to 5 texts"
    if kind == "timeout":
        return None if type(value) is int and 1 <= value <= WAIT_MAX_MS else f"must be 1 to {WAIT_MAX_MS} ms"
    if kind == "dimension":
        return None if type(value) is int and 200 <= value <= 4000 else "must be 200 to 4000"
    if kind == "id":
        return None if type(value) is int and 0 <= value <= 10 ** 9 else "must be a number from the listing"
    return "unknown field"


def validate_steps(data, app):
    """(claim, steps, refusals): refusals list each step outside the closed set; a malformed file raises."""
    if not isinstance(data, dict) or set(data) - {"claim", "steps"}:
        raise ValueError('The steps file must be {"claim": "C<n>", "steps": [...]}')
    claim = data.get("claim")
    if claim is not None and (not isinstance(claim, str) or not CLAIM.fullmatch(claim)):
        raise ValueError("claim must be C<n>")
    steps = data.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError(f"steps must be a list of 1 to {MAX_STEPS} steps")
    refusals = []
    for index, step in enumerate(steps, 1):
        action = step.get("action") if isinstance(step, dict) else None
        if not isinstance(action, str) or action not in ACTIONS:
            why = "not one of the reproduction's actions"
        else:
            fields = ACTIONS[action]
            unknown = sorted(set(step) - {"action", *fields})
            missing = sorted(name for name, (_, required) in fields.items() if required and name not in step)
            why = None
            if unknown:
                why = f"fields outside the action: {', '.join(unknown)}"
            elif missing:
                why = f"missing: {', '.join(missing)}"
            else:
                for name, (kind, _) in fields.items():
                    if name in step:
                        problem = _field_problem(kind, step[name], app)
                        if problem:
                            why = f"{name}: {problem}"
                            break
        if why:
            refusals.append({"index": index, "action": action if isinstance(action, str) else None,
                             "status": "refused", "detail": f"{BOUNDARY} ({why})"})
    return claim, steps, refusals


# --- element resolution from a snapshot (pure) ---

def snapshot_nodes(text):
    """(uid, role, rest after the role, the line) of every node of a chrome-devtools-mcp text snapshot."""
    nodes = []
    for line in (text or "").splitlines():
        match = NODE.match(line)
        if not match:
            continue
        rest = match.group(2) or ""
        if rest.startswith('"'):
            role, after = "", rest
        else:
            role, _, after = rest.partition(" ")
        nodes.append((match.group(1), role, after, line.strip()))
    return nodes


def _named(after, name):
    quoted = f'"{name}"'
    return after == quoted or after.startswith(quoted + " ")


def resolve(text, element):
    """(uid, line, None) for exactly one matching node, else (None, None, reason)."""
    nodes = snapshot_nodes(text)
    if "role" in element:
        found = [n for n in nodes if n[1].casefold() == element["role"].casefold() and _named(n[2], element["name"])]
        shown = f'{element["role"]} "{element["name"]}"'
    else:  # visible text: any node so named except the document itself (its name is the page title)
        found = [n for n in nodes if n[1].casefold() != "rootwebarea" and _named(n[2], element["text"])]
        shown = f'text "{element["text"]}"'
    if len(found) == 1:
        return found[0][0], found[0][3], None
    if not found:
        return None, None, f"no element {shown} in the latest snapshot"
    return None, None, f"{len(found)} elements match {shown} in the latest snapshot (ambiguous)"


# --- running the steps (production code; `tool` is the browser session's, or the eval fake's) ---

def _shown(text, limit):
    shown = redact(text or "")
    return shown if len(shown) <= limit else shown[:limit] + f" ... [{len(shown) - limit} more characters]"


def _posix(path):
    return str(path).replace("\\", "/")


def _call(step, tool, uids, evidence, shot):
    """(ok, text) of one step's tool call; uids maps element fields to resolved uids."""
    action = step["action"]
    if action == "navigate":
        return tool("navigate_page", timeout=TOOL_TIMEOUT, type="url", url=step["url"])
    if action == "take_snapshot":
        return tool("take_snapshot")
    if action == "click":
        return tool("click", uid=uids["element"], **({"dblClick": True} if step.get("double") else {}))
    if action == "fill":
        return tool("fill", uid=uids["element"], value=step["value"])
    if action == "hover":
        return tool("hover", uid=uids["element"])
    if action == "press_key":
        return tool("press_key", key=step["key"])
    if action == "drag":
        return tool("drag", from_uid=uids["from"], to_uid=uids["to"])
    if action == "handle_dialog":
        extra = {"promptText": step["prompt_text"]} if "prompt_text" in step else {}
        return tool("handle_dialog", action=step["response"], **extra)
    if action == "wait_for":
        texts = [step["text"]] if isinstance(step["text"], str) else list(step["text"])
        ms = step.get("timeout_ms", WAIT_DEFAULT_MS)
        return tool("wait_for", timeout=ms / 1000 + 30, text=texts, timeout_ms=ms)
    if action == "resize_page":
        return tool("resize_page", width=step["width"], height=step["height"])
    if action == "take_screenshot":
        return tool("take_screenshot", filePath=_posix(evidence / shot), format="png",
                    **({"fullPage": True} if step.get("full_page") else {}))
    if action == "list_console_messages":
        return tool("list_console_messages")
    if action == "get_console_message":
        return tool("get_console_message", msgid=step["msgid"])
    if action == "list_network_requests":
        return tool("list_network_requests")
    if action == "get_network_request":
        return tool("get_network_request", reqid=step["reqid"])
    raise ValueError(f"unhandled action {action}")  # unreachable after validate_steps


def run_steps(steps, tool, evidence, token, deadline):
    """Run validated steps in order; the first failure ends the run. Returns the per-step results (not redacted:
    the caller redacts the whole result)."""
    results, stopped = [], None
    for index, step in enumerate(steps, 1):
        result = {"index": index, "action": step["action"], "step": step}
        if stopped:
            results.append({**result, "status": "not run", "detail": stopped})
            continue
        if time.monotonic() > deadline:
            stopped = f"the reproduction's time bound ({MAX_SECONDS} s) was reached"
            results.append({**result, "status": "not run", "detail": stopped})
            continue
        uids, problem = {}, None
        fields = [name for name in ("element", "from", "to") if name in step]
        if fields:
            error, snapshot = tool("take_snapshot")
            if error is not False:
                problem = "the snapshot before this step failed: " + (snapshot or "no answer")[:300]
            else:
                for name in fields:
                    uid, line, reason = resolve(snapshot, step[name])
                    if reason:
                        problem = f"{name}: {reason}"
                        break
                    uids[name] = uid
                    result.setdefault("resolved", {})[name] = line
        shot = f"repro-{token}-{index:02d}.png"
        if problem:
            ok, text = False, problem
        else:
            error, text = _call(step, tool, uids, evidence, shot)
            ok = error is False
            if error is None:
                text = "the browser server did not answer: " + (text or "")
        limit = SNAPSHOT_LIMIT if step["action"] == "take_snapshot" else OUTPUT_LIMIT
        result.update(status="passed" if ok else "failed", output=_shown(text, limit))
        if step["action"] == "take_screenshot" and not problem:
            result["screenshot"] = shot if ok else None
        else:  # the page as this step left it (also when it failed)
            error, _ = tool("take_screenshot", filePath=_posix(evidence / shot), format="png")
            result["screenshot"] = shot if error is False else None
        if not ok:
            stopped = f"step {index} failed"
        results.append(result)
    return results


# --- the browser session (platform layer; the eval fake replaces `open_session`) ---

class Session:
    """A reproduction's browser session: `tool(name, timeout=60, **arguments) -> (is_error, text)`, with is_error
    None when the server did not answer; `started` once a browser process exists, `ended` once the session's job is
    confirmed ended. The caller creates it, so it sees `started` and `ended` also when the session fails to open."""

    def __init__(self):
        self.client, self.page, self.stuck = None, None, None
        self.started, self.ended = False, False
        self.server_requests = []

    def tool(self, name, timeout=TOOL_TIMEOUT, **arguments):
        import mcp_stdio
        if self.stuck:
            return None, f"skipped: the browser server stopped answering ({self.stuck})"
        if name != "list_pages" and self.page is not None:
            arguments = {"pageId": self.page, **arguments}
        if name == "wait_for" and "timeout_ms" in arguments:
            arguments["timeout"] = arguments.pop("timeout_ms")
        try:
            return self.client.tool(name, arguments, timeout=timeout)
        except mcp_stdio.McpTimeout as error:
            self.stuck = f"{name}: {error}"
            return None, str(error)


def _register(directory, name):
    import target as disposable_target
    folder = Path(directory) / REGISTRY
    try:
        os.mkdir(folder)
    except FileExistsError:
        pass
    attributes = os.lstat(folder).st_file_attributes
    if attributes & disposable_target.ATTR_REPARSE or not attributes & disposable_target.ATTR_DIRECTORY:
        raise ValueError("The repro registration directory is not a plain directory; nothing is started")
    path = folder / name
    with open(path, "x", encoding="utf-8") as written:
        written.write(json.dumps({"pid": os.getpid(), "registered_at": time.time()}))
    return path


@contextlib.contextmanager
def open_session(cli, directory, plan, session):
    """I10's browser session: own siblings, nonce, proxy port and kill-on-close job (registered before node starts),
    the exercise's definition template. Yields `session` (a Session) ready for its tool calls; ends the job and
    confirms it on the way out (session.ended)."""
    import exercise
    import guard
    import mcp_stdio
    import supervisor
    import target as disposable_target
    import winjob
    b, summary = plan["browser"], plan["summary"]
    temp = disposable_target.create_sibling(directory, "repro-temp")
    cwd = disposable_target.create_sibling(directory, "repro-cwd")
    profile = disposable_target.create_sibling(directory, "repro-profile")
    problems = exercise.placement_problems(Path(directory), Path(summary["target"]), Path(b["evidence"]), temp, cwd,
                                           profile)
    if problems:
        raise ValueError("Repro directory placement refused: " + "; ".join(problems))
    browser.seed_profile(profile)  # U16: downloads blocked before the launch
    problems = browser.profile_problems(profile)
    if problems:
        raise ValueError("Repro profile refused: " + "; ".join(problems))
    node, entry = browser.node_executable(cli.which), browser.entry_script()
    template = exercise._template({"app": summary["app"], "headed": plan["request"]["headed"]}, node, entry)
    holder = browser.ProxyHolder(exercise.owned_proxy_port(summary["app"]))
    registration = None
    try:
        definition = browser.instantiate(template, browser.NAME_PREFIX + secrets.token_hex(8), summary["target"], cwd,
                                         temp, holder.port, profile)
        if browser.never_listed(definition, profile):
            raise ValueError("The repro's browser server definition carries a forbidden argument")
        env = guard.mcp_environment(cli.shell_environment(), definition["env"])
        job = winjob.Job(supervisor.REPRO_JOB_PREFIX)
        try:
            registration = _register(directory, job.name)
            process = winjob.start_suspended(job, [definition["command"], *definition["args"]], definition["cwd"], env)
            session.started = True
            try:
                stderr = []
                threading.Thread(target=lambda: [stderr.append(line) for line in process.stderr], daemon=True).start()
                session.client = mcp_stdio.Client(process.stdin, process.stdout)
                try:
                    info = session.client.initialize()
                except mcp_stdio.McpError as error:
                    raise ValueError(f"The browser server did not start ({error}); "
                                     f"stderr: {redact(b''.join(stderr)[-400:].decode('utf-8', 'replace'))}") from None
                version = (info or {}).get("serverInfo", {}).get("version") if isinstance(info, dict) else None
                if version != browser.VERSION:
                    raise ValueError(f"The browser server reports version {str(version)[:40]!r}, not {browser.VERSION}")
                listed = {t.get("name") for t in (session.client.request("tools/list", timeout=30) or {}).get("tools", [])}
                missing = [name for name in TOOLS if name not in listed]
                if missing:
                    raise ValueError(f"The browser server lacks the reproduction's tools: {', '.join(missing)}")
                _, pages = session.tool("list_pages")
                found = re.search(r"^(\d+):", pages or "", re.M)
                if not found:
                    raise ValueError("The browser server lists no page")
                session.page = int(found.group(1))
                yield session
            finally:
                session.server_requests = list(session.client.server_requests) if session.client else []
                try:
                    process.stdin.close()
                except OSError:
                    pass
                process.wait(5)
                session.ended = job.terminate(supervisor.TIMING["end_patience"])
                process.close()
        finally:
            if not session.started:
                session.ended = job.terminate(supervisor.TIMING["end_patience"])
            job.close()
            if session.ended and registration is not None:
                registration.unlink(missing_ok=True)
    finally:
        holder.close()


# --- the CLI action: repro ---

def _require_kept(directory, plan):
    import exercise
    if not exercise.is_plan(plan):
        raise ValueError("This applies to exercises only")
    exercise.require_platform()
    if not (Path(directory) / "collected").exists():
        raise ValueError("Reproduction and evidence handling come after collect of a completed exercise run and "
                         "before finish (the target and the app are kept only then)")


def read_steps(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ValueError("The steps file cannot be read as JSON") from None


def repro(cli, directory, steps_path):
    """consult.py repro: validate the whole step list, then run it in one browser session (I10)."""
    import exercise
    import guard
    import supervisor
    directory, plan = cli.plan_at(directory)
    _require_kept(directory, plan)
    claim, steps, refusals = validate_steps(read_steps(steps_path), plan["summary"]["app"])
    base = {"directory": str(directory), "claim": claim}
    if refusals:
        refused = {r["index"] for r in refusals}
        results = [next(r for r in refusals if r["index"] == i) if i in refused else
                   {"index": i, "action": s.get("action") if isinstance(s, dict) else None, "status": "not run",
                    "detail": "the step list is refused: no step ran"} for i, s in enumerate(steps, 1)]
        return redact_value({"state": "refused", **base, "reason": f"{BOUNDARY}: {len(refusals)} step(s) are not "
                             "reproduction actions on the app; nothing was started and no step ran", "steps": results})
    exercise.verify_entries(directory, plan)
    guard.require_current_pass(cli, directory, plan)   # the exercise's fingerprint (I10, I7)
    supervisor.require_started(directory, plan)       # the app runs under its supervisor
    evidence = Path(plan["browser"]["evidence"])
    token = secrets.token_hex(4)
    deadline = time.monotonic() + MAX_SECONDS
    results, failure = [], None
    session = Session()
    try:
        with open_session(cli, directory, plan, session) as opened:
            results = run_steps(steps, opened.tool, evidence, token, deadline)
    except Exception as error:
        failure = str(error) if isinstance(error, ValueError) else f"{type(error).__name__}: the reproduction failed"
    if failure is not None and not results:
        state = "failed"
    else:
        state = "completed" if results and all(r["status"] == "passed" for r in results) else "step_failed"
    result = {"state": state, **base, "steps": results,
              "screenshots": [r["screenshot"] for r in results if r.get("screenshot")],
              "browser_ended": session.ended or not session.started}
    if failure:
        result["reason"] = failure
    if not session.started:
        result["browser_note"] = "no browser process was started"
    elif not session.ended:
        result["browser_note"] = ("the reproduction's browser job was not confirmed ended; finish ends its registered "
                                  "job before the app")
    result = redact_value(result)
    name = f"repro-{token}.json"
    try:
        with open(evidence / name, "x", encoding="utf-8") as written:
            written.write(json.dumps(result, ensure_ascii=False, indent=1))
        result["result_file"] = name
    except OSError:
        result["result_file"] = None
    return result


# --- the CLI action: evidence-keep ---

def reference_parts(reference):
    """The components of an evidence reference relative to <target>/evidence, or (None, reason)."""
    import target as disposable_target
    if not isinstance(reference, str) or not 0 < len(reference) <= 400 or any(ord(c) < 32 for c in reference):
        return None, "not a file name"
    if reference.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", reference):
        return None, "absolute, UNC, device and drive-relative paths are refused"
    if ":" in reference:
        return None, "a data stream (':') is refused"
    parts = re.split(r"[\\/]", reference)
    for part in parts:
        if part in ("", ".", ".."):
            return None, "'.', '..' and empty components are refused"
        if not disposable_target._valid_component(part):
            return None, f"invalid name {part!r}"
    return parts, None


def kept_name(stamp, index, parts):
    safe = SAFE.sub("_", parts[-1]).lstrip(".")[:80] or "file"
    return f"ask-codex-evidence-{stamp}-{index:02d}-{safe}"


def keep(cli, directory, request_path):
    """consult.py evidence-keep: move chosen evidence files to the user-named destination (I9)."""
    import exercise
    directory, plan = cli.plan_at(directory)
    _require_kept(directory, plan)
    try:
        request = json.loads(Path(request_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise ValueError("The keep file cannot be read as JSON") from None
    if not isinstance(request, dict) or set(request) != {"destination", "files"}:
        raise ValueError('The keep file must be {"destination": "<directory>", "files": ["<reference>", ...]}')
    destination, files = request["destination"], request["files"]
    if not isinstance(destination, str) or not 0 < len(destination) <= 1000 or any(ord(c) < 32 for c in destination):
        raise ValueError("The destination must be the absolute path of an existing directory")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_KEEP_FILES:
        raise ValueError(f"files must list 1 to {MAX_KEEP_FILES} evidence references")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    items, outcomes = [], []
    for index, reference in enumerate(files, 1):
        parts, reason = reference_parts(reference)
        if reason:
            outcomes.append({"reference": reference, "kept": False, "reason": reason})
        else:
            items.append((reference, parts, kept_name(stamp, index, parts)))
            outcomes.append(None)
    exercise.verify_entries(directory, plan)
    moved = iter(move_files(directory, plan, items, destination) if items else [])
    outcomes = [o if o is not None else next(moved) for o in outcomes]
    kept = sum(1 for o in outcomes if o["kept"])
    return {"state": "kept" if kept == len(outcomes) else "partly_kept" if kept else "nothing_kept",
            "directory": str(directory), "destination": destination, "files": outcomes}


def move_files(directory, plan, items, destination):
    """(platform layer) Each (reference, parts, new name): resolve under <target>/evidence through handles without
    following a link, copy into a new file in the destination, delete the source. One outcome per item."""
    import msvcrt
    import target as t
    t._absolute_drive_path(destination, "destination")  # a local drive path: no UNC, device, '.' or '..' form
    if ":" in destination[2:]:
        raise ValueError("The destination must not name a data stream")
    with t._placeholders_exposed():
        destination_handle = _open_destination(t, destination, directory)
        try:
            _, record = t.record_at(directory)
            [entry] = [e for e in record["entries"] if e.get("kind") == "target" and e.get("state") == "created"]
            root = t._verified_root(record)
            try:
                target_handle = t._nt_open(root, ntpath.basename(entry["path"]), t.TRAVERSE | t.READ_ATTRIBUTES,
                                           t.DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
            finally:
                t._close(root)
            try:
                attributes, _ = t._attribute_tag(target_handle)
                if attributes & t.ATTR_REPARSE or t._identity(target_handle) != {
                        "volume_serial": entry.get("volume_serial"), "file_id": entry.get("file_id")}:
                    raise ValueError("The target no longer matches its record; nothing is moved")
                evidence = _open_plain_directory(t, target_handle, "evidence")
            finally:
                t._close(target_handle)
            try:
                return [_move_one(t, msvcrt, evidence, destination_handle, destination, *item) for item in items]
            finally:
                t._close(evidence)
        finally:
            t._close(destination_handle)


def _open_plain_directory(t, parent, name):
    handle = t._nt_open(parent, name, t.LIST_DIRECTORY | t.TRAVERSE | t.READ_ATTRIBUTES,
                        t.DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
    if t._attribute_tag(handle)[0] & t.ATTR_REPARSE:
        t._close(handle)
        raise ValueError(f"{name} is a link (reparse point); refused")
    return handle


def _open_destination(t, destination, directory):
    try:
        handle = t._win_open(destination, t.LIST_DIRECTORY | t.ADD_FILE | t.TRAVERSE | t.READ_ATTRIBUTES,
                             t.FLAG_BACKUP_SEMANTICS | t.FLAG_OPEN_REPARSE_POINT)
    except OSError:
        raise ValueError("The destination does not exist or cannot be opened; name an existing directory") from None
    try:
        attributes, _ = t._attribute_tag(handle)
        if attributes & t.ATTR_REPARSE or not attributes & t.ATTR_DIRECTORY:
            raise ValueError("The destination is a link or not a directory; refused")
        final = t._strip_final(t._final_path(handle), "destination")
        _, record = t.record_at(directory)
        for owned in [str(Path(directory).resolve()), *[e.get("path") for e in record.get("entries", [])
                                                       if isinstance(e.get("path"), str)]]:
            if t._inside(final, owned):
                raise ValueError("The destination lies in the target, its sibling directories or the run directory, "
                                 "which finish removes; name a directory outside them")
        return handle
    except BaseException:
        t._close(handle)
        raise


def _move_one(t, msvcrt, evidence, destination_handle, destination, reference, parts, name):
    try:
        return _move_checked(t, msvcrt, evidence, destination_handle, destination, reference, parts, name)
    except OSError as error:
        return {"reference": reference, "kept": False, "reason": f"{type(error).__name__}: {error}"}


def _move_checked(t, msvcrt, evidence, destination_handle, destination, reference, parts, name):
    outcome = {"reference": reference, "kept": False}
    opened = []
    try:
        parent = evidence
        for part in parts[:-1]:
            try:
                parent = _open_plain_directory(t, parent, part)
            except t.NtError as error:
                return {**outcome, "reason": f"{part}: not a directory under evidence ({error})"}
            except ValueError as error:
                return {**outcome, "reason": str(error)}
            opened.append(parent)
        try:
            source = t._nt_open(parent, parts[-1], t.READ_DATA | t.READ_ATTRIBUTES | t.DELETE,
                                t.NON_DIRECTORY_FILE | t.OPEN_REPARSE_POINT)
        except t.NtError as error:
            missing = error.status in (t.STATUS_NAME_NOT_FOUND, t.STATUS_PATH_NOT_FOUND)
            return {**outcome, "reason": "not found under the evidence directory" if missing else
                    f"not a regular file under the evidence directory ({error})"}
        source_fd = t._adopt(source, os.O_RDONLY)
        try:
            attributes, _ = t._attribute_tag(source)
            information = _file_information(t, source)
            if attributes & (t.ATTR_REPARSE | t.ATTR_DIRECTORY) or attributes & t.RECALL_ATTRIBUTES:
                return {**outcome, "reason": "a link (reparse point) or not a regular file; refused"}
            if information["links"] != 1:
                return {**outcome, "reason": "a file with more than one link (a hard link) is refused"}
            if information["size"] > MAX_KEEP_BYTES:
                return {**outcome, "reason": f"larger than {MAX_KEEP_BYTES} bytes; refused"}
            try:
                created = t._nt_open(destination_handle, name, t.WRITE_DATA | t.READ_ATTRIBUTES | t.DELETE,
                                     t.NON_DIRECTORY_FILE, t.FILE_CREATE, t.ATTR_NORMAL)
            except t.NtError as error:
                return {**outcome, "reason": f"the destination file {name} could not be created (nothing is "
                                             f"overwritten): {error}"}
            target_fd = t._adopt(created, os.O_WRONLY)
            try:
                try:
                    while True:
                        chunk = os.read(source_fd, 1 << 20)
                        if not chunk:
                            break
                        os.write(target_fd, chunk)
                except OSError as error:
                    t._dispose(msvcrt.get_osfhandle(target_fd))
                    return {**outcome, "reason": f"copy failed ({error}); the partial copy was deleted"}
            finally:
                os.close(target_fd)
            kept = {**outcome, "kept": True, "path": ntpath.join(destination.replace("/", "\\"), name)}
            try:
                t._dispose(msvcrt.get_osfhandle(source_fd))
            except OSError as error:
                kept["note"] = f"copied; the original stays in the evidence directory and goes with the target ({error})"
            return kept
        finally:
            os.close(source_fd)
    finally:
        for handle in opened:
            t._close(handle)


def _file_information(t, handle):
    import ctypes
    import struct
    info = ctypes.create_string_buffer(52)  # BY_HANDLE_FILE_INFORMATION
    if not t._api()[0].GetFileInformationByHandle(handle, info):
        raise t._win_error("Reading file information")
    high, low, links = struct.unpack_from("<III", info.raw, 32)
    return {"size": (high << 32) | low, "links": links}
