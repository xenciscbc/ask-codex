"""Deterministic MCP policy and definition-bound confirmation decisions."""
import hashlib
import json
import os
from pathlib import Path
import re
import tomllib

NAME = re.compile(r"^[A-Za-z0-9_.-]+$")
PLACEHOLDERS = {"stdio": 'command="ask-codex-disabled"',
                "streamable_http": 'url="http://127.0.0.1:9/ask-codex-disabled"'}


class ConfirmationRequired(Exception):
    def __init__(self, pending):
        self.pending = pending


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def policy_file(path):
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError()
        if "mcp_policy" in value and value["mcp_policy"] not in ("allowlist", "minimal-deny"):
            raise ValueError()
        if "mcp_allow" in value and (not isinstance(value["mcp_allow"], list) or any(
                not isinstance(name, str) or not NAME.fullmatch(name) for name in value["mcp_allow"])):
            raise ValueError()
        return {key: value[key] for key in ("mcp_policy", "mcp_allow") if key in value}
    except (ValueError, OSError):
        raise ValueError(f"Invalid policy configuration: {path}; expected a valid mode and server-name list") from None


def definition_files(project):
    # Discover the enclosing repository without executing any project-configured command.
    root = next((p for p in (project, *project.parents) if (p / ".git").exists()), project)
    current = project
    files = []
    while True:
        path = current / ".codex/config.toml"
        if path.exists():
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
                definitions = data.get("mcp_servers", {})
                if not isinstance(definitions, dict) or any(not NAME.fullmatch(name) or not isinstance(value, dict)
                                                           for name, value in definitions.items()):
                    raise ValueError()
            except (ValueError, OSError):
                raise ValueError(f"Invalid project Codex configuration: {path}") from None
            files.append((str(path), definitions))
        if current == root:
            break
        current = current.parent
    return files


def resolve(request, project, neutral, listing):
    decisions = request.get("confirmations", {})
    if not isinstance(decisions, dict) or any(v not in ("allow", "deny") for v in decisions.values()):
        raise ValueError("Confirmations must map current confirmation IDs to allow or deny")
    pending = []

    def decision(kind, scope, value, **public):
        identifier = digest([kind, str(project), scope, value])
        answer = decisions.get(identifier)
        if answer is None:
            pending.append({"id": identifier, "kind": kind, "scope": scope, **public})
        return answer

    home = Path(os.environ.get("HOME", str(Path.home())))
    own = policy_file(home / ".claude/ask-codex.json")
    local_path = project / ".claude/ask-codex.local.json"
    local = policy_file(local_path)
    effective = {"mcp_policy": "allowlist", "mcp_allow": [], **own, **local}
    if local and (effective["mcp_policy"] == "minimal-deny" or effective["mcp_allow"]):
        answer = decision("project-policy", str(local_path), effective,
                          mode=effective["mcp_policy"], servers=effective["mcp_allow"],
                          on_decline="Use user policy alone or default")
        if answer == "deny":
            effective = {"mcp_policy": "allowlist", "mcp_allow": [], **own}

    definitions = definition_files(project)
    for path, servers in definitions:
        for name, value in servers.items():
            answer = decision("project-definition", path + "#" + name, value, server=name,
                              fields=sorted(value), on_decline="Do not send consultation",
                              grants_use=False)
            if answer == "deny":
                raise ValueError(f"Consultation not sent: project definition declined for {name} in {path}")
    if pending:
        raise ConfirmationRequired(pending)  # No Codex call until project definitions are settled.

    baseline = {s["name"]: s for s in listing(neutral)}
    servers = listing(project)
    disabled = set()
    for server in servers:
        name = server["name"]
        permitted = name in effective["mcp_allow"] if effective["mcp_policy"] == "allowlist" else name not in ("node_repl", "cua_repl")
        changed = baseline.get(name) != server
        if permitted and server["enabled"] and changed:
            answer = decision("project-server-use", name, server, server=name,
                              changed_fields=sorted(k for k in server if server.get(k) != baseline.get(name, {}).get(k)),
                              on_decline="Disable this server and continue", grants_use=True)
            if answer != "allow":
                permitted = False
        # An already-disabled server needs no override; overriding a plugin-provided
        # one creates a config entry without transport, which Codex rejects.
        if not permitted and server["enabled"]:
            disabled.add(name)
    if pending:
        raise ConfirmationRequired(pending)

    overrides = []
    if disabled:
        # A root-table inline value preserves literal dotted names. A plugin-provided
        # server has no config entry to merge into, so each override carries a
        # placeholder of the listed transport type (a different type's key conflicts).
        transports = {s["name"]: s["transport"].get("type") for s in servers}
        entries = []
        for name in sorted(disabled):
            if transports[name] not in PLACEHOLDERS:
                raise ValueError(f"Cannot disable MCP server {name} with transport {transports[name]}; consultation not sent")
            entries.append(f'{json.dumps(name)}={{{PLACEHOLDERS[transports[name]]},enabled=false}}')
        overrides = ["-c", "mcp_servers={" + ",".join(entries) + "}"]
    guarded = listing(project, overrides)
    expected = {s["name"]: False if s["name"] in disabled else s["enabled"] for s in servers}
    expected.update({name: False for name in disabled})
    if {s["name"]: s["enabled"] for s in guarded} != expected:
        raise ValueError("MCP guard mismatch; consultation not sent")
    allowed = sorted(name for name, enabled in expected.items() if enabled)
    # A newly loaded definition for a permitted server must also abort the guard.
    original = {s["name"]: s for s in servers}
    if any(s != original[s["name"]] for s in guarded if s["name"] in allowed):
        raise ValueError("MCP guard definition mismatch; consultation not sent")
    return {"policy": effective["mcp_policy"], "allowed_servers": allowed,
            "fingerprint": digest([effective, definitions, baseline, servers])}, overrides
