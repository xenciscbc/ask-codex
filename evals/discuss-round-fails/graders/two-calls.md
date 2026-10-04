---
type: regex
pattern: '^\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Exactly two Codex calls: the round limit is 2.
