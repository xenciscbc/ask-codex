# 08: Complete migration and cross-platform acceptance

**What to build:** The supported consultation workflows use the new execution boundary consistently on Windows with Git Bash and Linux, in interactive and headless sessions. Remove unused legacy orchestration only after its callers are migrated, and deliver accurate operating guidance and validation evidence.

**Blocked by:** 06 — Run parallel consultations through the new execution flow; 07 — Preserve consultation framing and reply dispositions.

Status: resolved — on a narrowed claim (2026-09-24, user decision; see Comments)

- [ ] Inventory remaining consultation entry paths and migrate any legacy callers required for the accepted single-model, policy, parallel, and follow-up behaviors. Delete superseded orchestration only after no supported caller needs it.
- [ ] Run the relevant offline execution integration scenarios on both Windows with Git Bash and Linux, including argument handling, policy guard, waiting, tree stopping, and diagnostic cleanup.
- [ ] Exercise interactive and headless Claude-facing flows on both supported platforms, including pending confirmations, result collection, request provenance, and report completeness. Offline stub checks alone do not establish actual Claude behavior.
- [ ] Verify integrated combinations: definition change before execution, policy-confirmed follow-up, parallel mixed outcomes, and unresolved-stop retention with a successful second opinion available.
- [ ] Mark unavailable environments or live checks as unverified. Do not claim full acceptance or close unresolved verification gaps merely because one platform passed. Do not start live billable consultations without appropriate authorization.
- [ ] Migrate obsolete command-shape, exact-English, line-count, and prose-hash tests to behavior checks while retaining the failures they were intended to prevent. Run required existing regressions affected by the migration.
- [ ] Update installation, dependencies, supported-environment claims, execution summaries, permission explanations, headless handling, and retained-data cleanup guidance to match actual behavior.
- [ ] Keep skill and prompt files in English, remove duplicated deterministic instructions, and record before/after size of the skill and its full mandatory instruction load. Do not hide instruction growth by moving it into another always-loaded document.
- [ ] Confirm preservation of model/effort selection, two-model limit, default interval and override behavior, no retry after start, user-request initiation, and fresh-session follow-up semantics.
- [ ] Confirm disclosures remain accurate: allowed MCP tools are outside the read-only shell sandbox, diagnostics may contain project content, and unconfirmed stops are unresolved.
- [ ] Record any implementation choices or ADR adjustments needed by the accepted architecture without rewriting historical decisions as though the new design had always existed. Do not modify or close the parent specification merely to mark this ticket complete.

## Notes

Source: the approved final migration and acceptance slice. This is the contract-removal and integrated verification step after usable vertical slices have landed, not a substitute for their own tests and documentation. macOS is outside formal acceptance. Exact runtime language and test fixture organization remain implementation choices rather than additional user commitments.

## Comments

### Implementation review

Migration is implemented. Current acceptance evidence, size measurements, historical-test scope and remaining interactive/real-Codex gaps are recorded in ../evidence/validation.md. This ticket is not fully accepted and the parent specification is unchanged.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.

### 2026-09-24 — resolved on a narrowed claim (user decision)

What this closes on: the implementation is in `main` (1.0.2), and the evidence in [validation.md](../evidence/validation.md) holds. That evidence is the public CLI suite on stub Codex (Windows and Ubuntu WSL), the lifecycle suites on both platforms, all Node offline tests, and two headless Claude cases on WSL. Unchecked boxes above remain unchecked: they are acceptance items this evidence does not reach. They are not claimed.

Not verified, and not claimed by this closure:
- Interactive Claude flows on either platform.
- Real-Claude headless operation on native Windows.
- Full consultations with the real Codex service.
- A full Claude eval suite on the current bytes. Many graders still pin the pre-rewrite skill; see [09](09-realign-claude-evals-with-script-owned-skill.md).
- macOS, which is outside the accepted scope.

Known residual process-observation limits are in validation.md and reliability ticket 14 (items 4–6).
