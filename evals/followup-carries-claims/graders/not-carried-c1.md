---
type: regex
pattern: 'C1 \[adopt\]'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
