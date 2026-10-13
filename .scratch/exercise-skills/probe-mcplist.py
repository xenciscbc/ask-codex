"""Show what `codex mcp list --json` reports for the cdt server under the probe's extra args."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "D:/work_data/project/skill/ask-codex/skills/ask/scripts")
import consult  # noqa: E402

extra = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
proc = subprocess.run(consult.invocation_for(["codex", "mcp", "list", "--json", *extra], Path("D:/tmp/exercise-probe/mcplist-argv.bin")),
                      capture_output=True, env=consult.shell_environment(), cwd="D:/tmp/exercise-probe/ws")
out = proc.stdout.decode("utf-8", "replace")
try:
    servers = json.loads(out)
    print("names", [s.get("name") for s in servers])
    for server in servers:
        if server.get("name") == "cdt":
            print(json.dumps(server, indent=1))
except ValueError:
    print("RAW", out[:2000], proc.stderr.decode("utf-8", "replace")[:2000])
