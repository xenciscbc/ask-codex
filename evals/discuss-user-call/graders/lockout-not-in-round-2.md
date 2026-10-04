---
type: regex
pattern: 'CAPTCHA|[Ww]ait message'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt does not mention the lockout-screen choice at all, so it is not debated under another id either (a Claude point on the same question, unmatched, would carry these words).
