# 03 — Model aliases and effort rules

**What to build:** The user can name a model by alias (`sol`, `5.6 sol`, `astra`, …) and optionally an effort, and Claude resolves them correctly. Aliases are matched fuzzily against the models Codex currently lists publicly (from the Codex model cache in the Codex home, honouring `CODEX_HOME`); an ambiguous alias (e.g. `5.6`) opens an `AskUserQuestion` with the candidates; no match gives an error listing the available models. With no model named, the Codex-configured model is used (or, if none is configured, the highest-priority listed model). Effort follows the consultation-effort rules: floor `medium`; defaults `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, others max(model default, `medium`); explicit `low` → `medium` with a note; an unsupported level → the model's highest supported level with a note; `ultra` only on explicit request. When the user's model/effort override differs from the current session setting, Claude asks whether it applies to this consultation only or to the rest of the session; re-stating the current setting asks nothing. Proactive consultations never pick a model or effort on Claude's own judgment. See spec: user stories 22–35.

**Blocked by:** 01 — Manual consultation tracer bullet.

**Status:** ready-for-agent

- [ ] First, determine whether an eval scaffold can seed a model cache into the throwaway Codex home; if not, record the fallback (stub-supplied equivalent or live-only coverage) in the ticket comments before building cases.
- [ ] Alias resolution uses only publicly listed models and never a hardcoded alias table.
- [ ] Ambiguous alias → `AskUserQuestion` with candidates; no match → error listing available models; no Codex call in either case until resolved.
- [ ] Effort is always passed explicitly; the configured Codex effort never reaches a consultation.
- [ ] `low` is raised to `medium` with a note; unsupported levels clamp to the model's maximum with a note; `ultra` is never chosen implicitly.
- [ ] Override scope prompt appears only when the override differs from the session setting; a session-scoped override persists for later consultations in the same conversation.
- [ ] Eval cases pass: `sol` → `-m gpt-5.6-sol` with effort `high`; `astra` → `gpt-6-astra` with `medium`; `sol:low` → `medium` with a note; ambiguous `5.6` prompts and makes no Codex call; unknown alias errors with no Codex call.
- [ ] Eval `alias-metachar` (F9): an alias containing shell metacharacters is rejected with no `codex exec` (CODEX_CALL `max: 0`); resolved slugs always match `^[A-Za-z0-9._-]+$`.
