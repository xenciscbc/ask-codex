"""Probe: the exact ask-codex consultation command line (same preflight MCP overrides), plus --disable multi_agent.

Runs one real Codex call on D:/tmp/subagent-probe asking it to spawn an executor child that writes a file.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "D:/work_data/project/skill/ask-codex/skills/ask/scripts")
import consult  # noqa: E402

PROMPT = (
    "This is a capability probe run by the project owner; the files here are disposable.\n\n"
    "1. Spawn a child agent with the named role `executor` and give it this task: create the file "
    "`probe-executor.txt` in the project root containing the single line `written by executor`. "
    "Do not create the file yourself.\n"
    "2. Check yourself whether `probe-executor.txt` exists.\n\n"
    "Answer with the JSON schema you were given. One claim: whether the child could be spawned "
    "(quote any error verbatim). One claim: whether `probe-executor.txt` exists."
)
request = {"project": "D:/tmp/subagent-probe", "prompt": PROMPT,
           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}], "confirmations": {}}
with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
    summary, overrides = consult.preflight(request, neutral)
out = Path("D:/tmp/subagent-probe-guard")
args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
        "-C", "D:/tmp/subagent-probe", "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"', *overrides,
        "--disable", "apps", "-c", "agents.enabled=false",
        "--output-schema", "D:/work_data/project/skill/ask-codex/skills/ask/consultation.schema.json",
        "-o", str(out / "agentsoff-last.json"), "-"]
(out / "agentsoff-argv.json").write_text(json.dumps(args, indent=1), encoding="utf-8")
with open(out / "agentsoff-events.jsonl", "wb") as events:
    proc = subprocess.run(consult.invocation_for(args, out / "agentsoff-argv.bin"), input=PROMPT.encode("utf-8"),
                          stdout=events, stderr=subprocess.PIPE, env=consult.shell_environment(), timeout=900)
    code = proc.returncode
    (out / "agentsoff-stderr.log").write_bytes(proc.stderr)
print("exit", code)
print("policy", summary.get("policy"), "allowed", summary.get("allowed_servers"))
