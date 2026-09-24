# 05: Confirm process-tree stops and retain unresolved diagnostics

**What to build:** Stopping a consultation waits for process-tree cleanup and reports whether termination was actually confirmed. Confirmed stops clean up; unresolved stops retain the data needed to investigate and tell the user where it is, without destroying files a remaining process may use.

**Blocked by:** 04 — Wait reliably and perform timely liveness checks.

Status: resolved — on a narrowed claim (2026-09-24, user decision; see Comments)

- [ ] Reproduce and fix the launcher/watcher race: a promptly exiting root must not cancel an in-progress descendant termination or verification operation.
- [ ] Cover whole-tree stopping on supported platforms, including resistant descendants and cooperative stopping when the caller cannot directly inspect the run's PID namespace.
- [ ] Root exit, an exit-code file, or a quiet event log alone cannot establish confirmed termination. Missing identity or incomplete verification yields an unconfirmed status rather than a fabricated success.
- [ ] The structured stop result distinguishes confirmed and unconfirmed stops and carries interval, elapsed time, last event and timing, options actually offered, termination evidence or uncertainty, and retained location where relevant.
- [ ] Claude reports stop results accurately in the conversation language, without requiring a fixed English sentence or fixed sentence placement. No claims are attributed to a stopped consultation.
- [ ] Confirmed stops collect required status before cleanup. Normal completion continues to collect the reply before cleanup.
- [ ] Unconfirmed stops retain process identity, execution status, stop results, and error logs. Files potentially still used by surviving processes remain until termination is confirmed.
- [ ] Once termination is confirmed, prompts and replies can be removed and are not long-term diagnostic artifacts. Retained diagnostics require an explicit cleanup request; no automatic expiry deletion is added.
- [ ] Cleanup operates only on the intended run artifacts. Repeated status checks or cleanup attempts must not reinterpret an unrelated reused PID as the original consultation or remove unrelated data.
- [ ] User reports identify retained data and unresolved state. Documentation does not claim retained error logs are sanitized merely because prompts and replies are excluded.
- [ ] Process-level tests cover early root exit, delayed cleanup, resistant descendants, unavailable PID visibility, confirmed and unconfirmed outcomes, subsequent confirmation, and preservation/removal of the correct files. Report any platform branch not actually exercised as unverified.
- [ ] The skill consumes the new stopping and cleanup behavior, replacing unconditional deletion after an unconfirmed stop and obsolete exact-wording graders with substantive checks.

## Notes

Source: Q5, Q9 and ADR 0005. The goal is verified termination and useful retention, not a new background retention service or broader process-management facility.

## Comments

### Implementation review

Identity-bound stopping, cooperative watcher shutdown, durable wrapper completion and conservative diagnostic retention are implemented. See validation.md for exact platform evidence and limitations; the checklist remains an acceptance record rather than a claim that every live branch ran.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.

### 2026-09-24 — resolved on a narrowed claim (user decision)

What this closes on: the implementation is in `main` (1.0.2), and the evidence in [validation.md](../evidence/validation.md) holds. That evidence is the public CLI suite on stub Codex (Windows and Ubuntu WSL), the lifecycle suites on both platforms, all Node offline tests, and two headless Claude cases on WSL. Unchecked boxes above remain unchecked: they are acceptance items this evidence does not reach. They are not claimed.
