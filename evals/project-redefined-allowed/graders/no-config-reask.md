---
type: regex
pattern: 'I confirm this project(?:''|’)s ask-codex config'
match: not_contains
---

Step 2's copy-back sentence is not offered here: the user already confirmed this project's ask-codex config, and a confirmation of one kind never covers another (`skills/ask/SKILL.md:38`), so re-offering that sentence would ask again for what was already given and leave the project-defined server unasked. The sentence this stop needs is step 4's, pinned by `final-right-kind`.
