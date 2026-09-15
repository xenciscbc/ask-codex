---
type: regex
pattern: 'C3 \[reject\]'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
