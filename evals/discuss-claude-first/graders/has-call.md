---
type: regex
pattern: '\d{4}-\d{2}-\d{2}T'
target:
  source: file
  path: .stub/exec.sentinel
---

At least one Codex call was made (the order check below is not vacuous).
