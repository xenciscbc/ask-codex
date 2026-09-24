# 10 — The script resolves the model and effort of a single-model consultation

**What to build:** For a single-model consultation, Claude hands the user's leading request text and this session's existing model/effort choice to a new resolve operation of the consultation script. The script does the deterministic selection that the skill currently spells out in prose: it reads the Codex home's model cache (listed models only) and configured model, validates model and effort tokens, splits `<alias>:<effort>` and a leading `effort <level>`, resolves model aliases, applies the default order (session choice → configured model → listed model with the lowest priority number → no model), and applies the effort rules (always explicit and at least medium; low/minimal/none raised with a note; an unsupported level lowered to the highest supported non-ultra level with a note; ultra only on explicit request and support; the default per model). It returns structured status: `resolved` (model, effort, notes), `ambiguous` (candidates), `invalid` or `unavailable` (reason). The skill's model-selection steps become "call resolve and act on its status". Claude still decides where the model tokens end and the question begins, asks the user when an alias is ambiguous, and discloses notes.

**Blocked by:** None — can start immediately.

**Status:** resolved — see Comments (2026-09-24)

- [ ] The observable selection behavior does not change: every rule above resolves exactly as the skill's current prose does, with no invented model list.
- [ ] The per-model default efforts (currently `sol` → high, `astra` → medium) move into the script unchanged, as data in one place (user decision 2026-09-24). No other fixed alias-to-model table is introduced.
- [ ] Missing cache or config files make that source unavailable; unreadable or malformed configuration is reported, not invented around. Invalid tokens stop before any Codex command.
- [ ] Offline tests through the public script interface cover each rule, including ambiguous and unknown aliases, token validation failures, effort raising/lowering with notes, explicit ultra, and each step of the default order.
- [ ] The Claude-facing alias and effort cases (`alias-*`, `effort-unsupported`, `default-model-config`) pass on their argv graders (the resolved model and effort reaching Codex). Wording graders are not a criterion here; they belong to ticket 09.
- [ ] The skill's selection prose is replaced, not duplicated. ADR 0005 gains a note that model and effort selection moved into the script with unchanged behavior.

## Notes

Source: `/claude-api prompt-audit` finding F5 (2026-09-24). The prose does work whose output is fully determined by its inputs, and a hardcoded default table that has already rotted once lives in the skill. Parallel pairs and the scope comparison are ticket 11.

## Comments

### 2026-09-24 — implemented (`5a2942c`, `c5ead90`, `e0e8b73`)

`consult.py resolve` (new `models.py`) takes the model tokens Claude reads off the request, reads the Codex model cache and configuration, and returns `resolved` / `ambiguous` / `invalid` / `unavailable` / `failed`. SKILL.md keeps the user interaction only; ADR 0005 records the move.

One deviation from this ticket's first wording, and why. The first cut (`5a2942c`) parsed the user's whole text in the script. `/code-review high` showed that it applied the old prose too literally: "Context: …", "Use Redis or Postgres?" and "5 reasons …" were read as model tokens and stopped. Claude now decides which words are model tokens; the script validates and resolves them. The same review led to three more fixes: an unknown effort word is invalid (before, a typo became the model's highest level); a model with no listed levels means unknown support; and an ambiguous result keeps the named effort. Its finding 10 (Codex home from `Path.home()` vs `HOME`) was rejected: `policy.py` reads Claude's ask-codex config from `HOME`, not the Codex home, and the Codex CLI uses the OS home directory.

Evidence:
- `evals/_harness/resolve_test.py` 42/42 through the public CLI. All Node offline tests pass; `consultation_test.py` has one error (`test_partial_parallel_launch_failure_stops_started_consultation`, a Windows file lock during cleanup), which reproduces unchanged on `main`.
- Claude evals, one run each, `claude-sonnet-5`, WSL. The first pass was all 14 model-selection cases on `c5ead90`. The second pass was five cases on `e0e8b73`, after two fixes the first pass forced: the session model is now resolved like a token (it had reached Codex as `-m astra`), and SKILL.md says to pass tokens unrepaired (Claude had repaired `sol;touch${IFS}pwned` to `sol`). On the final bytes every argv grader passes: `alias-sol`, `session-override-persists` and `parallel-two-models` model and effort; `alias-metachar` and `alias-ambiguous` make no Codex call. From the first pass, which touched no selection logic changed later: `alias-astra`, `alias-sol-low`, `default-model-config`, `effort-unsupported`, `parallel-one-fails`, and the two refusal cases (no Codex call).
- Graders that still fail pin the pre-rewrite procedure or wording (`one-codex-exec`, `skill-fired`, `scope-line`, `*-disable-set`, `two-temp-dirs`, `two-background-runs`, `h-*`, `tag-*`, `refusal`, the timer graders of `parallel-shared-timer`) — ticket 09.
- Seen once, not caused here: in the second `session-override-persists` run Claude ran the scripts as `cd '<skill>' && python3 scripts/consult.py …`, against the unchanged "never change the shell's working directory" rule (`no-bare-cd`). The first run of that case passed it.
