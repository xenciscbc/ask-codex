---
type: regex
pattern: '[Ii] confirm the project|then ask Codex again'
match: not_contains
---

After a decline the final message states the outcome only: it never repeats the question and never offers the copy-back sentence again (`skills/ask/SKILL.md:41`; a decline always wins, `:39`). Either half — the drafted "I confirm the project …" sentence or its fixed ending `then ask Codex again.` — fails the run.
