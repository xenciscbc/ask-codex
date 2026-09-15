---
type: regex
pattern: 'Consultation type: targeted check\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
