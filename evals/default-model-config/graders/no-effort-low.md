---
type: regex
pattern: 'model_reasoning_effort=\\"low\\"'
match: not_contains
target:
  source: file
  path: .stub/exec-argv.json
---
