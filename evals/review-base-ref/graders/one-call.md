---
type: regex
pattern: '^\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Exactly one Codex call: the stub appends one timestamp line per `exec`, so the sentinel holds exactly one line (the pattern has no multiline flag, so `^` and `$` are the ends of the file).
