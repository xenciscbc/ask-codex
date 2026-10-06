"""Probe: an ordinary second-opinion consultation that requires reading several documents and analysing contradictions.

  python probe-docs.py <project> <outdir> <off|on>
"off" adds -c agents.enabled=false; "on" is the current ask-codex command line. Nothing in the prompt mentions child agents.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "D:/work_data/project/skill/ask-codex/skills/ask/scripts")
import consult  # noqa: E402

project, outdir, mode = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
outdir.mkdir(parents=True, exist_ok=True)
ASK = Path("D:/work_data/project/skill/ask-codex/skills/ask")
template = (ASK / "prompts" / "consultation.md").read_text(encoding="utf-8")
framing = (ASK / "prompts" / "framing" / "second-opinion.md").read_text(encoding="utf-8").strip()
prompt = (template.replace("{{framing}}", framing)
          .replace("{{question}}", "Read every document under docs/ and the code in src/. Find every contradiction between the requirements, the design, the API description and the code, assess the impact of each, and say which source should win and why.")
          .replace("{{context}}", "- Claude's stance: the requirements document is the source of truth and the design should be rewritten to match it.\n- The documents are docs/requirements.md, docs/design.md and docs/api.md; the code is src/orders.js.")
          .replace("{{extra_paths_or_none}}", "none"))
request = {"project": project, "prompt": prompt,
           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}], "confirmations": {}}
with tempfile.TemporaryDirectory(prefix="ask-codex-preflight-") as neutral:
    summary, overrides = consult.preflight(request, neutral)
extra = ["-c", "agents.enabled=false"] if mode == "off" else []
args = ["codex", "exec", "-s", "read-only", "--ephemeral", "--skip-git-repo-check", "--json",
        "-C", project, "-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"', *overrides,
        "--disable", "apps", *extra,
        "--output-schema", str(ASK / "consultation.schema.json"), "-o", str(outdir / "last.json"), "-"]
with open(outdir / "events.jsonl", "wb") as events:
    proc = subprocess.run(consult.invocation_for(args, outdir / "argv.bin"), input=prompt.encode("utf-8"),
                          stdout=events, stderr=subprocess.PIPE, env=consult.shell_environment(), timeout=1500)
(outdir / "stderr.log").write_bytes(proc.stderr)
print(mode, "exit", proc.returncode)
