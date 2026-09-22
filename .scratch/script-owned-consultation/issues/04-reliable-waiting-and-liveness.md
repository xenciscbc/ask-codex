# 04: Wait reliably and perform timely liveness checks

**What to build:** Interactive and headless single-model consultations wait within tool limits, check liveness at the configured interval, and collect completion before the caller ends. Users retain the existing wait-or-stop behavior without the model calculating unsafe blocking durations.

**Blocked by:** 01 — Run a single-model consultation through the script boundary.

Status: needs-triage

- [ ] Waiting exposes structured completion or still-running state through the execution boundary and is actually used by the skill.
- [ ] Preserve the default 30-minute interval, positive-whole-number override validation, staleness threshold, recommendations, and repeated user-selected waits.
- [ ] Every blocking wait is bounded by both the remaining interval and the active tool's maximum duration. Do not issue a full 30-minute timeout to a tool with a shorter cap.
- [ ] Multi-segment waiting performs the liveness check when the interval expires rather than silently resetting or exceeding it.
- [ ] Preserve task/event-based liveness decisions and the existing headless stop decision when a stale run requires a user decision that cannot be obtained. An actual process-tree stop can use the existing stopping path until ticket 05 replaces it.
- [ ] A headless caller does not finish while a consultation is still running or leave a completed reply unread. If optional task-output branches remain, verify both available and unavailable cases; a unified mechanism is acceptable if behavior is preserved.
- [ ] Report timer overrides and meaningful liveness outcomes with required information but without exact-English sentence constraints. Do not equate recent output with proof of eventual completion.
- [ ] Deterministic tests cover interval boundaries, shortened tool caps, repeated waits, override rejection, completion between checks, and missing launcher completion state without making every test sleep 30 real minutes.
- [ ] Retain a process-level integration check for real completion signaling and a skill-facing headless scenario for result collection. Verify relevant behavior rather than pinning instruction text or line counts.
- [ ] Update English skill instructions to remove duplicated timer arithmetic and describe only the interaction needed to consume the waiting result.

## Notes

Source: the parent specification's wait-limit defect and unchanged timer policy. This ticket must not add a new automatic timeout or retry policy.

## Comments

### Implementation review

Bounded foreground waiting, default/override intervals, repeated decisions, liveness snapshots and check history are implemented. Tests use a virtual wall clock for interval transitions and real processes for completion; full interactive long-duration acceptance remains open.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.
