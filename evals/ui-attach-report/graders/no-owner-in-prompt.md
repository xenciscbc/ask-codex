---
type: regex
pattern: '5101|5102|python\.exe|backend/server\.py --api-token'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---

Codex is never told the attached processes (AT-9).
