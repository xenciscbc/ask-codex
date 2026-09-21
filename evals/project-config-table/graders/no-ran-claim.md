---
type: regex
pattern: '[Aa]sked Codex:|consultation (?:ran|has run|was sent|has been sent|completed|finished)|Codex(?:''|’)s (?:answer|reply|response) (?:is|was|follows)'
match: not_contains
---

The final message never claims the consultation ran: this stop happens before any `codex exec` (`skills/ask/SKILL.md:41`), so "Asked Codex:", "the consultation was sent" or "Codex's answer is …" would tell the user something untrue about what happened. It pins the "without running the consultation" clause of the deleted LLM judge (`asks-f12b-env` / `asks-f12b-command`); the negations a correct reply uses — "The consultation was not sent.", "the consultation didn't run" — are not matched.
