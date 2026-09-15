---
type: regex
pattern: 'Consultation type: technical question\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
