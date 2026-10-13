"""Run one exercise probe: the consultation command line (same preflight MCP overrides, child agents off),
with a chosen sandbox and optional extra args.

Usage: python probe-run.py <name> <read-only|workspace-write> <prompt-file> [extra codex args...]
Evidence goes to .scratch/exercise-skills/evidence/<name>-*.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "D:/work_data/project/skill/ask-codex/skills/ask/scripts")
import consult  # noqa: E402

name, sandbox, prompt_file, *extra = sys.argv[1:]
if extra and extra[0].startswith("@"):  # extra args from a JSON list file, avoiding shell quoting
    extra = json.loads(Path(extra[0][1:]).read_text(encoding="utf-8"))
PROJECT = "D:/tmp/exercise-probe/ws"
OUT = Path("D:/work_data/project/skill/ask-codex/.scratch/exercise-skills/evidence")
prompt = Path(prompt_file).read_text(encoding="utf-8")
request = {"project": PROJECT, "prompt": prompt,
           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}], "confirmations": {}}
with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
    summary, overrides = consult.preflight(request, neutral)
# "profile": no -s, the extra args select a permissions profile (docs: don't combine with sandbox_mode)
args = ["codex", "exec", *([] if sandbox == "profile" else ["-s", sandbox]), "--ephemeral", "--skip-git-repo-check", "--json",
        "-C", PROJECT, "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"', *overrides,
        "--disable", "apps", "-c", "agents.enabled=false", "-c", "features.multi_agent_v2.enabled=false",
        *extra, "-o", str(OUT / f"{name}-last.txt"), "-"]
(OUT / f"{name}-argv.json").write_text(json.dumps(args, indent=1), encoding="utf-8")
with open(OUT / f"{name}-events.jsonl", "wb") as events:
    proc = subprocess.run(consult.invocation_for(args, OUT / f"{name}-argv.bin"), input=prompt.encode("utf-8"),
                          stdout=events, stderr=subprocess.PIPE, env=consult.shell_environment(), timeout=900)
(OUT / f"{name}-stderr.log").write_bytes(proc.stderr)
print("exit", proc.returncode)
print("policy", summary.get("policy"), "allowed", summary.get("allowed_servers"))
