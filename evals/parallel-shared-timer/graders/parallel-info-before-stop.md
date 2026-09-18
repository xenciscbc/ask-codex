---
type: regex
pattern: '"role":"assistant"[^\n]*done [—-] [*` ]*gpt-5\.6-sol[*` ]*; still running [—-] [*` ]*gpt-6-astra[\s\S]*"name":"TaskStop"'
target: trace
---

Before the slow run is stopped, the assistant itself has written the parallel state — `done — gpt-5.6-sol; still running — gpt-6-astra` — in one of the places the skill puts it (the still-running notice, the question text, or the stop report copied from `stop.sh`). Anchored to a `"role":"assistant"` line so that neither `stop.sh`'s stdout in a tool result nor the `--done`/`--still-running` arguments of the stop command (which lack the ` — ` separator) can satisfy it; only the real call matches `"name":"TaskStop"`.
