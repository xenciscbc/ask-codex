---
type: tool_used
tool: Bash
input_match: 'scripts/run\.sh.*?-- .*?codex\s+exec\b'
min: 1
---

The consultation is launched through the shipped launcher (`bash '<skill dir>/scripts/run.sh' '<tmp>' -- codex exec …`), which records the child's pid for the stop script.
