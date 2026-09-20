# 17 — A consultation sometimes changes the shell's working directory with a bare `cd`

**What to build:** the skill never runs a bare `cd`; every command that needs a different directory uses `env -C '<dir>'` as the procedure already specifies, so a consultation cannot move the user's shell out from under them.

**Blocked by:** None — can start immediately.

**Status:** resolved — not reproduced (reliability ticket 06, 2026-09-20); skill unchanged

## Evidence (final suite at `f5cfb07`, 2026-09-16)

`second-opinion-with-stance` scored 0.92, failing `no-bare-cd` ("Bash called 1x, expected 0..0"). The grader's pattern is `'"command"\s*:\s*"\s*cd\s'`, which matches only a command whose first token is `cd`, so this is a real violation rather than a substring false positive — the Ground rules say never to use `cd`, and every other case in the suite passed that grader.

Not retested on the fixed bytes: the case was not part of the ticket-13 rerun set, so its current rate is unknown (1 of 1 observed failures).

## Impact

Claude Code's Bash tool keeps its working directory between calls, so a bare `cd` inside a consultation can leave the user's shell in another directory for every later command in the session — a side effect from something that is supposed to be read-only and self-contained.

## Acceptance criteria

- [ ] `second-opinion-with-stance` passes `no-bare-cd` on 3 of 3 runs.
- [ ] No case in the suite regresses on `no-bare-cd`.
- [ ] If the violation comes from a step whose command genuinely needs a directory, that step's example in the skill uses `env -C` explicitly rather than leaving it implied.

## Comments

**2026-09-20 — closed as not reproduced (reliability ticket 06).** Reliability ticket 01, probe E (2026-09-18, `.scratch/ask-codex-reliability/evidence/01-stop-behaviour.md`): `second-opinion-with-stance --keep-temp --runs 5` on the then-current bytes scored 1.00 on all five runs, `no-bare-cd` included; the five kept traces (12, 12, 14, 13 and 11 Bash calls) contain no command with `cd` in any position — not as the first token and not after `;`, `&&`, `|`, `(` or a newline. One more data point from real use: the live headless consultation of reliability ticket 04 (scenario H, 2026-09-20) made 18 Bash calls, none with `cd` in any position. The single failure at `f5cfb07` stands as a one-off; there is no step to point an `env -C` example at, so the skill is unchanged and the Ground rule "Never use `cd`" keeps its wording. Acceptance 1 is met with 5 of 5 instead of 3 of 3; acceptance 3 does not apply (no step identified). Acceptance 2 ("no case in the suite regresses on `no-bare-cd`") is checked by the full-suite rerun of reliability ticket 07 — if a case fails that grader there, this ticket is reopened with that trace.
