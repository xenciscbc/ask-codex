---
type: regex
pattern: '^(?=[\s\S]*\bL1\b)(?=[\s\S]*\bC1\b)(?=[\s\S]*\bC2\b)(?=[\s\S]*\bC3\b)'
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt names L1 (Claude always raises at least one point) and C1, C2, C3 (each Codex point is either a locked agreement or a contested point, and both are listed with their ids).
