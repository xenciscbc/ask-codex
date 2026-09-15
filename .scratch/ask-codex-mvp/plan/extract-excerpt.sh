#!/usr/bin/env bash
# Write the assistant text messages of a kept eval run, in order, to an evidence file.
# Usage: bash extract-excerpt.sh /tmp/ask-codex-eval.XXXXXX /mnt/d/.../evidence/parallel-shared-timer.txt
d="$1"; out="$2"
chmod -R u+rwx "$d" 2>/dev/null
t="$(find "$d" -name trace.jsonl | head -1)"
[ -n "$t" ] || { echo "no trace.jsonl under $d" >&2; exit 1; }
mkdir -p "$(dirname "$out")"
python3 - "$t" "$out" <<'PY'
import json, sys
trace, out = sys.argv[1], sys.argv[2]
lines = ["# Assistant text messages of the parallel-shared-timer green run, in order (tool calls omitted).",
         "# Written from the kept eval trace for the ticket-08 verifier: no claim may appear before the first parallel-check line.", ""]
n = 0
for raw in open(trace, encoding="utf-8"):
    try:
        o = json.loads(raw)
    except Exception:
        continue
    m = o.get("message") or {}
    if m.get("role") != "assistant" or not isinstance(m.get("content"), list):
        continue
    for b in m["content"]:
        if b.get("type") == "text" and b.get("text", "").strip():
            n += 1
            lines.append(f"--- assistant text {n}")
            lines.append(b["text"].rstrip())
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print(f"wrote {n} assistant text messages to {out}")
PY
