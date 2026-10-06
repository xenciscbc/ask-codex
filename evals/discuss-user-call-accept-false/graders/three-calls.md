---
type: regex
pattern: '^\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Exactly three Codex calls: the round limit is 3 and C3 is maintained to the end, so round 3 happens and its prompt can show a lapsed proposal line.
