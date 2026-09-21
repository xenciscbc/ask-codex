---
type: regex
pattern: 'confirmation needed'
match: not_contains
---

After a decline the final message states the outcome only (`skills/ask/SKILL.md:41`; a decline always wins, `:39`). The pending-confirmation opening `Consultation not sent — confirmation needed.` belongs to a stop that still waits for an answer, never to a declined one, so its words must not appear here.
