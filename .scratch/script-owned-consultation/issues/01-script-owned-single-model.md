# 01: Run a single-model consultation through the script boundary

**What to build:** A user-requested, single-model consultation with the default empty MCP allowlist runs through a script-owned execution boundary, shows a safe execution summary, returns the actual reply, and cleans up after collection. Claude prepares the question and judges the claims; it no longer reconstructs the execution command for this supported path. Keep other scenarios on their existing route until their migration tickets land.

**Blocked by:** None (can start immediately).

Status: needs-triage

- [ ] Introduce a cohesive execution boundary and structured status for this path, with preparation, running, completion, and failure distinguishable from Codex's opinion payload. Document the contract for later slices without requiring a particular programming language or helper layout.
- [ ] The skill calls the new boundary for eligible consultations; routing must not discard or bypass existing policy configuration or pending project-definition confirmations. Noneligible scenarios retain their existing guarded route.
- [ ] Before execution, Claude can show the resolved model, effort, project directory, and effective MCP policy without credentials. This is an informational summary, not a new approval gate.
- [ ] Scripts construct arguments and invoke the local Codex CLI directly with the existing read-only, ephemeral, structured-output and application-disable constraints. The effective MCP guard verifies all servers disabled for this path.
- [ ] Paths with spaces or apostrophes and argument data containing metacharacters reach the intended command as data; no unintended shell command executes.
- [ ] The intended prompt reaches the command exactly once, a completed reply is collected before cleanup, and missing or unusable replies and nonzero exits produce truthful failure status.
- [ ] No automatic retry occurs after Codex starts. Preserve the existing limited correction of an invocation error before Codex actually starts.
- [ ] Preserve model and effort selection, request provenance, prompt sanitization, and the distinction between consultation and delegation. Tool results cannot initiate a consultation.
- [ ] Verify this complete path using the existing stub CLI integration seam where practical, plus a small skill-facing check for actual routing and report meaning. Assert invocation behavior and state, not helper names or exact English wording.
- [ ] Update affected English skill instructions and operating guidance in this slice; unrelated legacy behavior remains available and its tests stay meaningful.

## Notes

Source: the Reliable script-owned consultations specification and ADR 0005. The stub CLI is the recommended test seam, not a separately confirmed requirement to freeze internal test architecture. Keep changes narrow enough to land as a working vertical slice; the lifecycle may initially reuse existing helpers. Later tickets strengthen policy resolution, waiting, and stopping.

## Comments

### Implementation review

Public CLI preparation, guarded execution, reply collection, and cleanup are implemented. Windows/Linux stub coverage and the script-consultation Claude headless case verify the main path.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.
