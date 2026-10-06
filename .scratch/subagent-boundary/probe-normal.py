"""Probe: an ordinary ask consultation (template + technical-question framing) with -c agents.enabled=false.

Same command line as consult.py builds (preflight MCP overrides), plus only -c agents.enabled=false.
Nothing in the prompt mentions child agents.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "D:/work_data/project/skill/ask-codex/skills/ask/scripts")
import consult  # noqa: E402

ASK = Path("D:/work_data/project/skill/ask-codex/skills/ask")
template = (ASK / "prompts" / "consultation.md").read_text(encoding="utf-8")
framing = (ASK / "prompts" / "framing" / "technical-question.md").read_text(encoding="utf-8").strip()
prompt = (template.replace("{{framing}}", framing)
          .replace("{{question}}", "How should login() in src/login.js stop leaking which usernames exist, and what is the smallest safe change?")
          .replace("{{context}}", "- The code is in src/login.js and src/users.js.\n- No callers exist yet; the return shape may change.")
          .replace("{{extra_paths_or_none}}", "none"))
request = {"project": "D:/tmp/agents-off-probe", "prompt": prompt,
           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}], "confirmations": {}}
with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
    summary, overrides = consult.preflight(request, neutral)
out = Path("D:/tmp/agents-off-guard")
args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
        "-C", "D:/tmp/agents-off-probe", "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"', *overrides,
        "--disable", "apps", "-c", "agents.enabled=false",
        "--output-schema", str(ASK / "consultation.schema.json"), "-o", str(out / "last.json"), "-"]
(out / "prompt.md").write_text(prompt, encoding="utf-8")
with open(out / "events.jsonl", "wb") as events:
    proc = subprocess.run(consult.invocation_for(args, out / "argv.bin"), input=prompt.encode("utf-8"),
                          stdout=events, stderr=subprocess.PIPE, env=consult.shell_environment(), timeout=900)
(out / "stderr.log").write_bytes(proc.stderr)
print("exit", proc.returncode, "| policy", summary.get("policy"), summary.get("allowed_servers"))
