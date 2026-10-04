---
type: regex
pattern: '"--output-schema",\s*"[^"]*discussion\.schema\.json"'
target:
  source: file
  path: .stub/exec-argv.2.json
---
