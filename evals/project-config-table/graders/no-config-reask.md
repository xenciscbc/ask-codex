---
type: regex
pattern: 'I confirm this project(?:''|’)s ask-codex config[^\n]*then ask Codex again'
match: not_contains
---

Step 2's copy-back sentence is not OFFERED here: the user already confirmed this project's ask-codex config, and a confirmation of one kind never covers another (`skills/ask/SKILL.md:38`), so re-offering that sentence would ask again for what was already given and leave the server this stop is about unasked (the sentence it needs is pinned by `final-right-kind`). Only the offered sentence is matched — it ends with the fixed words `then ask Codex again` on the same line; the user's own message, which the reply quotes in its `Requested by the user:` line, carries the same opening words without that ending and is left alone.
