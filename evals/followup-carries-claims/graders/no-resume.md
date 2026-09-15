---
type: regex
pattern: 'resume|fork'
match: not_contains
target:
  source: file
  path: .stub/exec-argv.json
---
