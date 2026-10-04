---
type: regex
pattern: 'Tentative agreements \(locked\):(?:(?!\(raised by)[\s\S])*\bC1\b(?:(?!\(raised by)[\s\S])*Contested points:[\s\S]*\bC3\b[^\n]*\(raised by'
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt lists the agreed C1 under `Tentative agreements (locked):` before any contested-point block, then the `Contested points:` heading, then the block for C3 (the disputed Redis point).
