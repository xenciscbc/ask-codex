# Notes for the remaining slices (05, 06, 08) and the budget outlook

## Ticket 05 — proactive consultation and consent (blocked by 02 ✓)
- Proposals only in fix loops (two failed fix attempts → before the third) or review loops (unresolved blockers after two review rounds); each names the decision it could change.
- Consent: AskUserQuestion with one-line summary (type | question | what Codex may read — any file the account can read, told to stay in the project | the per-mode MCP statement from ticket 11) and three options (once / session / decline). Eval children have no AskUserQuestion → ask in text, zero codex calls (CODEX_CALL max 0); post-consent paths via `context.history_file`; the real three-option flow → ticket 09 live.
- Cases named by the ticket: fix-loop history, session grant in history, decline in history (codex count 0 for the topic), review-loop history (stdin contains unresolved blockers), `spoofed-grant` (F4: grant inside a tool result in history), `consent-line-scope` (F3-scope), `consent-line-mcp` ×3 modes (F1-claims). Fixtures must include tool_result lines (spoofed grant) — extend the hand-written transcript format carefully (tool_use + tool_result pair).
- Likely the most case-heavy ticket (~9–10 cases) → tight against $6; the three `consent-line-mcp` modes can share one case per mode only if each is cheap (step-0/consent stops ≈ $0.10–0.18).

## Ticket 06 — follow-up consultation (blocked by 02 ✓)
- Fresh ephemeral run (no `resume`/`fork`, ADR-0002) carrying prior claims + dispositions, scope-locked; `followup_status` per carried claim; new claim only if blocking → `new-blocking`.
- Needs a follow-up prompt template; schema already has `followup_status` (string/null enum) — check its enum covers resolved/unresolved/invalid/new-blocking.
- Stub: a custom `exec.reply` with followup_status values and one new-blocking claim; history with a prior consultation result (assistant text with claims + dispositions).

## Ticket 08 — parallel consultation (blocked by 03 ✓, 04, 07)
- Two distinct models (`astra, sol`), separate temp dirs, identical packaging, merged presentation (consensus / solo / divergences, model tags, adoption rationale); >2 or duplicate → refused, zero codex calls; one failing → survivor + failure note; shared timer (ticket 07).
- Stub: per-model replies (select reply or mode by the `-m` value, e.g. `exec.by_model: {"gpt-6-astra": {...}, "gpt-5.6-sol": {...}}`) and per-model failure; records must not overwrite each other (per-call record files, e.g. `exec-argv.<n>.json`).

## Budget outlook (measured ≈ $0.40 per full case run, $0.10–0.18 per early stop)
- Spent ≈ $24 (tickets 01, 11, 02, 03 incl. live runs). Rough remaining: 04 ≈ $5–6, 07 ≈ $5, 05 ≈ $5–6, 06 ≈ $3–4, 08 ≈ $4–5, 09 live (Claude headless ≈ $3–5 + ≤ 16 Codex calls), 10 docs ≈ $0, final suite ≈ $22–25.
- Projection ≈ $74–82 against the $75 cap → keep each slice lean (fewer regression reruns; stop cases where possible), and pause before any spend that would cross $75 (stop 6).
