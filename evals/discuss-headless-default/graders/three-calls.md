---
type: regex
pattern: '^\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Exactly three Codex calls: no round count was given, so the limit is the default 3 (also when a question tool was tried and failed).
