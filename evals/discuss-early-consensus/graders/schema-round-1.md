---
type: regex
pattern: '"--output-schema",\s*"[^"]*discussion\.schema\.json"'
target:
  source: file
  path: .stub/exec-argv.1.json
---

Round 1's command line passes `discussion.schema.json` as `--output-schema` (the stub's per-call record `.stub/exec-argv.1.json`).
