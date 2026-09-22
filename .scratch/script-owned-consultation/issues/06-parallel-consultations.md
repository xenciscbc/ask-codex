# 06: Run parallel consultations through the new execution flow

**What to build:** A user-requested consultation with two different models uses the script-owned policy, authorization, waiting, and stopping flow while keeping each opinion independent. Mixed completion, failure, and stop outcomes are reported accurately without losing another model's files or claims.

**Blocked by:** 03 — Separate and bind MCP confirmations and use authorization; 05 — Confirm process-tree stops and retain unresolved diagnostics.

Status: needs-triage

- [ ] Preserve the maximum of two distinct resolved models, model and effort selection rules, and rejection of duplicate or excessive models before execution.
- [ ] Each model receives the same prepared question independently, with its own model/effort, process identity, output, state, and run artifacts; neither receives the other's opinion.
- [ ] Both executions apply the full resolved MCP policy and valid confirmations. The pre-execution summary identifies both models and their effective permissions.
- [ ] Preserve the shared check interval and per-model liveness outcomes. Structured status identifies completed and still-running models without requiring fixed report sentences.
- [ ] Preserve holding replies until all runs have completed or been stopped. Read all needed successful replies before cleanup that could discard them.
- [ ] One run failing or stopping does not cancel a completed opinion, misattribute claims, delete the other run's active files, or override its retention requirements.
- [ ] Successful paired opinions retain consensus, solo-claim, and divergence information with source identities and Claude's dispositions; no opinion is attributed to a failed or stopped model.
- [ ] Preserve no retry after start per model and truthful confirmed/unconfirmed stop results for every stopped run.
- [ ] End-to-end scenarios cover both successful, one completed while another runs, one failure, one stopped, and an unconfirmed stop with the other reply available. Verify independent inputs and per-run artifacts through the existing integration seam where practical.
- [ ] Update parallel skill instructions and behavior graders alongside the implementation. Do not require a particular English heading to prove the comparison information is present.

## Notes

Source: the approved parallel-consultation slice. Ticket 07 does not gate this work: preserve the existing paired-reply semantics here and share the execution contract introduced in ticket 01. Coordinate any shared skill edits with the current owner if work is delegated later.

## Comments

### Implementation review

Two independent executions share guarded preparation and timing. Public tests cover mixed results, partial launch failure, a completed opinion during later launch failure, and a missing stop receipt with another successful opinion. Full paired Claude comparison acceptance remains open.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.
