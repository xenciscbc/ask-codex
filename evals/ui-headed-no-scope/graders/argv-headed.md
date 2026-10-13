---
type: regex
pattern: '--headless'
match: not_contains
target:
  source: file
  path: .stub/exec-argv.json
---

With --headed the browser server definition has no --headless.
