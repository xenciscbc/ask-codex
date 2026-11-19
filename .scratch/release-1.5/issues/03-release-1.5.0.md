# 03 — Release 1.5.0: version, release notes, live acceptance

Status: ready-for-agent
Spec: `.scratch/release-1.5/spec.md` — cites Outcome, D4, I1, Security analysis dispositions (F1, F7), Plan review 1 dispositions (B4, N6), Plan review 2 dispositions (B3), Overall acceptance
Blocked by: 02
Security-critical: no (spec, Claim classification)

## What to do

- **Version:** set it to `1.5.0` in `.claude-plugin/plugin.json`, and in `.claude-plugin/marketplace.json` if that file carries a version.
- **`README.md` and `README.zh-TW.md`:** add 1.5.0 release notes.
  - `/ask-codex:ui` is removed.
  - Consultations now take Codex's reply from the `--json` event stream, so they work with codex-cli 0.170.0 when the run directory is on a RAM disk.
  - A failed run reports Codex's own error text.
  - A 1.4.0 install leaves `%LOCALAPPDATA%\ask-codex\` behind, and the user may delete it.
  - Any README statement about how the reply is written to a file is updated to match ADR 0011.
- **Live acceptance:** run one real, harmless consultation through the skill's own scripts (`resolve` → `prepare` → `run` → `wait` → `collect`), under codex-cli 0.170.0.
  - Base directory: the session scratchpad on R:.
  - Project: this repository.
  - Model: `gpt-6.2-astra`, effort `high`.
  - Prompt: a trivial one that sends no project content beyond the consultation template. One Codex call, meaning one `codex exec`; the preflight `codex mcp list` does not count.
  - Spec F1 and F7: call `collect` only after at least 20 seconds have passed since `wait` reported `finished`, so any notify-hook process (about 13 s in ticket 12) has ended. Before `collect`, copy the run's `events.jsonl` to the session scratchpad. Record the types of its last three lines and whether any line follows `turn.completed`.
  - Record the result in this ticket's Comments: CLI version, run directory drive, `collect` state, reply format, elapsed time.
  - A successful `collect` removes the run directory itself. Run `cleanup` only when `collect` retained it.

## Acceptance

1. `plugin.json` (and `marketplace.json` if versioned) says `1.5.0`. Both READMEs carry the release notes above.
2. The live consultation's `collect` returns `state: collected` with `runs[0].state = completed` and a `structured` reply. The run directory was on R:. `codex --version` printed `codex-cli 0.170.0` at the time. The copied stream has no event after `turn.completed`, where an event is a JSON object with a string `type`. Any plain-text line after it is recorded as observed. If an event does follow it, `collect` will have no reply and this item fails. The release then stops and the finding goes to the user to decide; it is not repaired here.
3. These tests pass: `node evals/_harness/setup-skill.test.mjs`, `node evals/_harness/review-skill-graders.test.mjs` and `node evals/_harness/discuss-skill-graders.test.mjs`. They are the tests that read `plugin.json`, `marketplace.json` or the README anchors. The spec's Overall acceptance (the full offline suite) is run by the final check, not as part of this claim.
4. Postcondition, not part of outcome verification: merge to `main`, tag `v1.5.0` and push happen only on the user's word. Main checks the tag and remote state after that operation.

## Comments
