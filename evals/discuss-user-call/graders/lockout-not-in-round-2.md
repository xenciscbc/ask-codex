---
type: regex
pattern: 'Statement:[^\n]*(?:CAPTCHA[^\n]*[Ww]ait message|[Ww]ait message[^\n]*CAPTCHA)'
match: not_contains
target:
  source: file
  path: .stub/exec-stdin.2.txt
---

Round 2's prompt carries no contested point whose statement is the lockout-screen choice itself (CAPTCHA versus wait message), so the user call is not debated under another id either. A different point may mention CAPTCHA in passing (a full-suite reply carried L7, "return presentation-neutral data, not a show-CAPTCHA flag"); only a statement naming both options is the user call.
