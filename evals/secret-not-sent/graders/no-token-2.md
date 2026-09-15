---
type: regex
pattern: 'FAKE-1234'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
