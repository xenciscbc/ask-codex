---
type: regex
pattern: 'Consult Codex\?\s*(\*\*)?\s*(second opinion|diagnosis|targeted check|technical question|follow-up)'
match: not_contains
---

Proactive consultation was removed (reliability ticket 08): the final response must not contain the old consent block, which began `Consult Codex? <type> | …`. Saying in plain words that the user can ask for a Codex consultation is fine, even as a question.
