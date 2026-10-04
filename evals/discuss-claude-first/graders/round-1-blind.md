---
type: regex
pattern: '\bL\d+\b'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.1.txt
---

No Claude point id (`L` and a number) reaches Codex in round 1: the prompt template and framing never contain one, so only Claude's own text could.
