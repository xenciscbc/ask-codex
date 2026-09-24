# 10 — The script resolves the model and effort of a single-model consultation

**What to build:** For a single-model consultation, Claude hands the user's leading request text and this session's existing model/effort choice to a new resolve operation of the consultation script. The script does the deterministic selection that the skill currently spells out in prose: it reads the Codex home's model cache (listed models only) and configured model, validates model and effort tokens, splits `<alias>:<effort>` and a leading `effort <level>`, resolves model aliases, applies the default order (session choice → configured model → listed model with the lowest priority number → no model), and applies the effort rules (always explicit and at least medium; low/minimal/none raised with a note; an unsupported level lowered to the highest supported non-ultra level with a note; ultra only on explicit request and support; the default per model). It returns structured status: `resolved` (model, effort, notes), `ambiguous` (candidates), `invalid` or `unavailable` (reason). The skill's model-selection steps become "call resolve and act on its status". Claude still decides where the model tokens end and the question begins, asks the user when an alias is ambiguous, and discloses notes.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The observable selection behavior does not change: every rule above resolves exactly as the skill's current prose does, with no invented model list.
- [ ] The per-model default efforts (currently `sol` → high, `astra` → medium) move into the script unchanged, as data in one place (user decision 2026-09-24). No other fixed alias-to-model table is introduced.
- [ ] Missing cache or config files make that source unavailable; unreadable or malformed configuration is reported, not invented around. Invalid tokens stop before any Codex command.
- [ ] Offline tests through the public script interface cover each rule, including ambiguous and unknown aliases, token validation failures, effort raising/lowering with notes, explicit ultra, and each step of the default order.
- [ ] The Claude-facing alias and effort cases (`alias-*`, `effort-unsupported`, `default-model-config`) pass on their argv graders (the resolved model and effort reaching Codex). Wording graders are not a criterion here; they belong to ticket 09.
- [ ] The skill's selection prose is replaced, not duplicated. ADR 0005 gains a note that model and effort selection moved into the script with unchanged behavior.

## Notes

Source: `/claude-api prompt-audit` finding F5 (2026-09-24). The prose does work whose output is fully determined by its inputs, and a hardcoded default table that has already rotted once lives in the skill. Parallel pairs and the scope comparison are ticket 11.
