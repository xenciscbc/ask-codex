---
type: regex
pattern: 'Contested points:|Tentative agreements \(locked\)'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.1.txt
---

The round-1 prompt has neither carried-points heading (`Contested points:`, `Tentative agreements (locked)`).
