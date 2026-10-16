---
type: regex
pattern: 'Install:[^\n]*make_accounts\.py[^\n]*\bbackend\b|Install:[^\n]*\bbackend\b(?!/make_accounts)[^\n]*make_accounts\.py'
---

The Install line shows the install command with its working directory, backend/ (C5 code review B-1, plan I9); a path prefix
`backend/make_accounts.py` is not a working directory.
