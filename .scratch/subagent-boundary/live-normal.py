"""Ordinary ask consultation through the real consult.py prepare/run/wait/collect path (subagent-boundary S2).

  python live-normal.py <project> <outdir>
Prints the argv consult.py used, the reply, and any mention of child agents in the event stream.
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ASK = REPO / "skills" / "ask"
project, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
template = (ASK / "prompts" / "consultation.md").read_text(encoding="utf-8")
framing = (ASK / "prompts" / "framing" / "technical-question.md").read_text(encoding="utf-8").strip()
prompt = (template.replace("{{framing}}", framing)
          .replace("{{question}}", "What does src/a.js export, and is anything in this project unused?")
          .replace("{{context}}", "- The project is tiny: README.md and src/a.js.")
          .replace("{{extra_paths_or_none}}", "none"))
req = out / "request.json"
req.write_text(json.dumps({"project": project, "prompt": prompt, "confirmations": {},
                           "models": [{"model": "gpt-5.6-sol", "effort": "medium", "explicit_ultra": False}]}), encoding="utf-8")
call = lambda *a: json.loads(subprocess.run([sys.executable, str(ASK / "scripts" / "consult.py"), *a], capture_output=True, text=True).stdout)
ready = call("prepare", str(req), "--base", str(out))
req.unlink()
directory = ready["directory"]
subprocess.Popen([sys.executable, str(ASK / "scripts" / "consult.py"), "run", directory])
time.sleep(5)
while call("wait", directory, "--seconds", "30")["state"] in ("running", "prepared"):
    pass
child = Path(directory) / "0"
argv = (child / "argv").read_bytes().split(b"\0")
print("argv has agents.enabled=false:", b"agents.enabled=false" in argv,
      "| has features.multi_agent_v2.enabled=false:", b"features.multi_agent_v2.enabled=false" in argv)
events = (child / "events.jsonl").read_text(encoding="utf-8")
shutil.copy(child / "events.jsonl", out / "events.jsonl")
print("child-agent mentions in events:", sorted(set(m.lower() for m in re.findall(r"spawn\w*|collaboration|delegat\w*|feather", events, re.I))))
time.sleep(2)
collected = call("collect", directory)
run = collected["runs"][0]
print("collect:", collected["state"], run.get("state"), run.get("reply", {}).get("format"))
print(json.dumps(run.get("reply", {}).get("content"), ensure_ascii=False)[:1500])
