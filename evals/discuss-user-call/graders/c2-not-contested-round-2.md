---
type: regex
pattern: '\bC2\b[^\n]*\(raised by'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt has no contested-point block for C2: a point both sides marked as a user call is not sent for debate.
