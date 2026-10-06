---
type: regex
pattern: 'User call proposed by (?:Claude|Codex): [^<\s]'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.3.txt
---

Round 2's reply set `user_call: false` on the proposed point, so the proposal lapsed and its line is never carried into round 3's block. The framing and the template name the line only as `User call proposed by Claude: <reason>` and `User call proposed by …`; a real line has a reason that does not start with `<`.
