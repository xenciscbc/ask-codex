---
type: regex
pattern: '^\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Exactly two Codex calls: the stub appends one timestamp line per `exec`, so the sentinel holds exactly two lines (no multiline flag: `^` and `$` are the ends of the file). Round 2 accepts everything, so the `rounds 5` limit is never reached.
