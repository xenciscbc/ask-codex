---
type: regex
pattern: '^(?:\d{4}-\d{2}-\d{2}T[^\r\n]*\r?\n?)?$'
target:
  source: file
  path: .stub/exec.sentinel
---

Zero or one Codex call (an `ask` consultation is allowed); a second call would be a hand-made multi-round discussion. It also keeps `.stub/exec-stdin.txt`, which holds only the last prompt, a complete record for `no-discussion-framing-sent`.
