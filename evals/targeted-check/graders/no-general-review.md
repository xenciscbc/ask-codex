---
type: regex
pattern: '[Rr]eview (the )?(whole|entire|full)'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
