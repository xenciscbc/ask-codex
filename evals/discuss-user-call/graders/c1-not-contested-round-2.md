---
type: regex
pattern: '\bC1\b[^\n]*\(raised by'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt has no contested-point block for C1: the agreement is locked background, not a contested point.
