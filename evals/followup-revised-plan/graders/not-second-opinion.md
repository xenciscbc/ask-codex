---
type: regex
pattern: 'Consultation type: second opinion\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.txt
---
