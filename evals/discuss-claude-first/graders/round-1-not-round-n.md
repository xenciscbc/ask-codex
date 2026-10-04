---
type: regex
pattern: 'Discussion round: follow-up\.'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.1.txt
---
