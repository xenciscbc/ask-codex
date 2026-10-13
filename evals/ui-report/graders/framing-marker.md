---
type: regex
pattern: '^Exercise type: UI exercise\.'
target:
  source: file
  path: .stub/exec-stdin.txt
---

The prompt sent to Codex starts with the UI framing's marker line.
