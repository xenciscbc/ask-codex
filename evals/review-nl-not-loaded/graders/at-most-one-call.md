---
type: regex
pattern: '^(?:\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?)?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Zero or one Codex call (an `ask` consultation of an existing type is allowed): the scaffold creates the sentinel empty and the stub appends one timestamp line per call. This keeps `.stub/exec-stdin.txt`, which holds only the last prompt, a complete record for `no-review-framing-sent`.
