#!/usr/bin/env python3
"""Stub `codex` CLI for the ask-codex eval suite. Never contacts OpenAI.

Behaviour is driven by `.stub/scenario.json` in the directory the call targets
(the working directory for `mcp list`, the `-C` directory for `exec`). Without a
scenario file the call is treated as coming from a neutral directory.

Records written next to the scenario file:
  .stub/mcp-list.log     one JSON line per `mcp list` call made from a scenario dir
  .stub/exec.sentinel    written by every `exec` call
  .stub/exec-argv.json   argv of the last `exec` call
  .stub/exec-stdin.txt   stdin (the prompt) of the last `exec` call
  .stub/violations.log   created on every call; one line per argv that breaks the invocation allowlist
  .stub/missing-calls.log  one line per call while EVAL_CODEX_STUB_MODE=missing (scenario dirs only)

`exec.mode` in the scenario: valid (default), not-logged-in, fail, schema-violation,
unstructured, os-error (prints the observed "os error 1" line on stdout, exit 1),
unreadable (exit 0, no agent message, empty -o file). `exec.reply` replaces the default reply.

Environment: EVAL_CODEX_STUB_MODE=missing makes every invocation behave like a missing
CLI (`codex: command not found` on stderr, exit 127) — set per case through case.yaml
`execution.env`, because the first call runs from a neutral dir without a scenario.
"""
import copy
import datetime
import json
import os
import re
import sys


def server(name, command, args, env):
    return {
        "name": name,
        "enabled": True,
        "disabled_reason": None,
        "transport": {"type": "stdio", "command": command, "args": args, "env": env, "env_vars": [], "cwd": None},
        "startup_timeout_sec": None,
        "tool_timeout_sec": None,
        "auth_status": "unsupported",
    }


GLOBAL_SERVERS = [
    server("blender", "uvx.exe", ["--python", "3.11", "blender-mcp"], {"DISABLE_TELEMETRY": "true"}),
    server("comfyui", "comfy-mcp.exe", [], {"COMFYUI_URL": "http://127.0.0.1:8188"}),
    server("node_repl", "node_repl.exe", [], {}),
    server("pencil", "mcp-server-windows-x64.exe", ["--app", "visual_studio_code"], None),
    server("cua_repl", "node.exe", ["cua-repl.mjs"], {"CUA_REPL_ENABLED_SURFACES": "browser"}),
]

DEFAULT_REPLY = {
    "summary": "The retry loop in fetchUser swallows the timeout error, so callers see an empty result instead of a failure.",
    "claims": [
        {
            "id": "C1",
            "statement": "fetchUser catches TimeoutError and returns an empty object instead of rethrowing.",
            "kind": "fact",
            "confidence": "high",
            "evidence": ["src/user.js:7"],
            "followup_status": None,
        },
        {
            "id": "C2",
            "statement": "renderProfile treats an empty object as 'user not found', which explains the misleading page.",
            "kind": "inference",
            "confidence": "medium",
            "evidence": ["src/pages/profile.js:4"],
            "followup_status": None,
        },
        {
            "id": "C3",
            "statement": "Raising the timeout from 2s to 10s would hide the symptom without fixing the error handling.",
            "kind": "inference",
            "confidence": "low",
            "evidence": [],
            "followup_status": None,
        },
    ],
    "open_questions": ["Is the empty-object return relied on by any other caller?"],
}

# -c mcp_servers.<name>={command="ask-codex-disabled",enabled=false}
DISABLE_RE = re.compile(r'^mcp_servers\.([A-Za-z0-9_.-]+)=\{\s*command\s*=\s*"ask-codex-disabled"\s*,\s*enabled\s*=\s*false\s*\}$')
# Consultation effort is never below medium; `ultra` only when the user asks for it.
EFFORT_RE = re.compile(r'^model_reasoning_effort="(medium|high|xhigh|max|ultra)"$')
SLUG_RE = re.compile(r'^[A-Za-z0-9._-]+$')


def load_scenario(directory):
    path = os.path.join(directory, ".stub", "scenario.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return {"dir": directory, "data": json.load(f)}


def stub_dir(scenario):
    d = os.path.join(scenario["dir"], ".stub")
    os.makedirs(d, exist_ok=True)
    # Always present once the stub has run, so graders can assert it is empty.
    open(os.path.join(d, "violations.log"), "a", encoding="utf-8").close()
    return d


def append(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def violation(scenario, reason):
    if scenario is not None:
        append(os.path.join(stub_dir(scenario), "violations.log"), reason + "\n")


def deep_merge(target, patch):
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            deep_merge(target[k], v)
        else:
            target[k] = v
    return target


def config_overrides(args):
    return [args[i + 1] if i + 1 < len(args) else "" for i, a in enumerate(args) if a == "-c"]


def mcp_list(args):
    scenario = load_scenario(os.getcwd())
    data = scenario["data"] if scenario else {}
    servers = copy.deepcopy(GLOBAL_SERVERS)
    if scenario:
        for extra in data.get("project_extra", []):
            servers.append(server(extra["name"], extra.get("command", "extra.exe"), extra.get("args", []), extra.get("env", {})))
        for name, patch in data.get("project_overrides", {}).items():
            for s in servers:
                if s["name"] == name:
                    deep_merge(s, patch)
    overrides = config_overrides(args)
    for kv in overrides:
        m = DISABLE_RE.match(kv)
        if not m:
            violation(scenario, f"mcp list: unexpected -c {kv}")
            continue
        if data.get("guard_fails"):
            continue
        match = [s for s in servers if s["name"] == m.group(1)]
        if match:
            match[0]["enabled"] = False
        else:
            disabled = server(m.group(1), "ask-codex-disabled", [], None)
            disabled["enabled"] = False
            servers.append(disabled)
    if scenario:
        append(os.path.join(stub_dir(scenario), "mcp-list.log"),
               json.dumps({"argv": args, "cwd": os.getcwd(), "overrides": len(overrides)}) + "\n")
    sys.stdout.write(json.dumps(servers, indent=2) + "\n")


def parse_exec(args):
    opts = {"flags": [], "c": [], "unknown": [], "stdin": False, "repeated": []}
    i = 0
    while i < len(args):
        a = args[i]
        value = args[i + 1] if i + 1 < len(args) else None
        if a in ("-s", "-o", "--output-schema", "-C", "-m", "--disable"):
            key = {"-s": "sandbox", "-o": "out", "--output-schema": "schema", "-C": "cwd", "-m": "model", "--disable": "disable"}[a]
            if key in opts:
                opts["repeated"].append(a)
            opts[key] = value
            i += 2
            continue
        if a == "-c":
            opts["c"].append(value if value is not None else "")
            i += 2
            continue
        if a in ("--ephemeral", "--skip-git-repo-check", "--json"):
            opts["flags"].append(a)
        elif a == "-":
            opts["stdin"] = True
        else:
            opts["unknown"].append(a)
        i += 1
    return opts


def emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def exec_(args):
    opts = parse_exec(args)
    directory = opts.get("cwd") or os.getcwd()
    scenario = load_scenario(directory) or {"dir": directory, "data": {}}
    data = scenario["data"]
    records = stub_dir(scenario)

    problems = []
    if opts.get("sandbox") != "read-only":
        problems.append(f"sandbox={opts.get('sandbox')}")
    for flag in ("--ephemeral", "--skip-git-repo-check", "--json"):
        if flag not in opts["flags"]:
            problems.append(f"missing {flag}")
    for key, flag in (("out", "-o"), ("schema", "--output-schema"), ("cwd", "-C")):
        if not opts.get(key):
            problems.append(f"missing {flag}")
    if not opts["stdin"]:
        problems.append("prompt not read from stdin (-)")
    if opts.get("model") is not None and not SLUG_RE.match(opts["model"]):
        problems.append(f"bad model {opts['model']}")
    if opts.get("disable") != "apps":
        problems.append(f"missing --disable apps (got {opts.get('disable')})")
    for flag in opts["repeated"]:
        problems.append(f"repeated {flag}")
    effort_seen = False
    for kv in opts["c"]:
        if EFFORT_RE.match(kv):
            effort_seen = True
        elif not DISABLE_RE.match(kv):
            problems.append(f"unexpected -c {kv}")
    if not effort_seen:
        problems.append("missing effort override")
    for u in opts["unknown"]:
        problems.append(f"unknown arg {u}")
    for p in problems:
        violation(scenario, f"exec: {p}")

    # Read raw bytes: the platform's default stdin encoding (e.g. a Windows code page)
    # can turn UTF-8 prompts into surrogates that cannot be written back out.
    prompt = sys.stdin.buffer.read().decode("utf-8", "replace") if opts["stdin"] else ""
    with open(os.path.join(records, "exec.sentinel"), "w", encoding="utf-8") as f:
        f.write(datetime.datetime.now(datetime.timezone.utc).isoformat() + "\n")
    with open(os.path.join(records, "exec-argv.json"), "w", encoding="utf-8") as f:
        json.dump(args, f, indent=2)
    with open(os.path.join(records, "exec-stdin.txt"), "w", encoding="utf-8") as f:
        f.write(prompt)

    mode = (data.get("exec") or {}).get("mode", "valid")
    emit({"type": "thread.started", "thread_id": "stub-thread"})
    emit({"type": "turn.started"})

    if mode == "not-logged-in":
        sys.stderr.write("Error: Not logged in. Run `codex login` to authenticate.\n")
        sys.exit(1)
    if mode == "fail":
        sys.stderr.write("Error: stub failure requested by scenario\n")
        sys.exit(1)
    if mode == "os-error":
        # The real failure observed on a drive where the Windows sandbox cannot run (stdout, exit 1).
        sys.stdout.flush()
        sys.stdout.buffer.write("Error: 功能錯誤。 (os error 1)\n".encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(1)
    if mode == "unreadable":
        emit({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 0}})
        if opts.get("out"):
            open(opts["out"], "w", encoding="utf-8").close()
        return

    if mode == "schema-violation":
        reply = json.dumps({"verdict": "looks fine", "notes": "no claims array"})
    elif mode == "unstructured":
        reply = "I looked at the code and I think the timeout handling is the problem."
    else:
        reply = json.dumps((data.get("exec") or {}).get("reply", DEFAULT_REPLY), indent=2)

    emit({"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": reply}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}})
    if opts.get("out"):
        with open(opts["out"], "w", encoding="utf-8") as f:
            f.write(reply)


def main():
    argv = sys.argv[1:]
    if os.environ.get("EVAL_CODEX_STUB_MODE") == "missing":
        scenario = load_scenario(os.getcwd())
        if scenario:
            append(os.path.join(stub_dir(scenario), "missing-calls.log"), " ".join(argv) + "\n")
        sys.stderr.write("codex: command not found\n")
        sys.exit(127)
    cmd = argv[0] if argv else ""
    sub = argv[1] if len(argv) > 1 else ""
    if cmd == "--version":
        sys.stdout.write("codex-cli 0.0.0-stub\n")
    elif cmd == "mcp" and sub == "list":
        mcp_list([a for a in argv[2:] if a != "--json"])
    elif cmd == "exec":
        exec_(argv[1:])
    else:
        violation(load_scenario(os.getcwd()), "unsupported command: " + " ".join(argv))
        sys.stderr.write("codex stub: unsupported command: " + " ".join(argv) + "\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
