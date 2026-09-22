# 02: Resolve consultation policy and enforce the MCP guard

**What to build:** A consultation obtains its effective MCP policy from deterministic configuration parsing, rejects invalid existing configuration, and executes only when the MCP guard agrees. Valid server names and unusual paths work without asking Claude to manually construct configuration overrides.

**Blocked by:** 01 — Run a single-model consultation through the script boundary.

Status: needs-triage

- [ ] Move user/project policy parsing, documented precedence, disable-set construction, and effective-policy guard checks into the script boundary.
- [ ] Missing policy configuration uses the documented fallback. Existing malformed JSON, invalid types, unsupported policy values, or invalid server names abort before consultation execution and identify the file and useful non-sensitive reason.
- [ ] An invalid project policy cannot be silently ignored in favor of a broader user policy. Unresolvable Codex configuration and failed listings also prevent execution.
- [ ] Preserve the allowlist and minimal-deny modes, including their existing sandbox limitations; do not add new policy modes or per-tool filtering.
- [ ] Treat valid dotted server names as literal names when constructing overrides; regression tests demonstrate the intended server is disabled rather than a nested configuration key being created.
- [ ] Compare the effective server set and enabled states against the planned policy. Missing, unexpected, or incorrectly enabled servers fail the guard before execution.
- [ ] Provide structured pending-confirmation information for project policy widening and project-defined servers, preserving the existing preflight ordering. Do not treat a project-definition confirmation as an allowlist entry. Full confirmation lifecycle migration belongs to ticket 03.
- [ ] Resolve and display the effective allowed servers in the pre-execution summary without leaking seeded sensitive values.
- [ ] End-to-end stub scenarios cover absent configuration, valid layered configuration, both policy modes, invalid restrictive project configuration, dotted names, listing failures, and guard mismatch; failure cases record no consultation execution.
- [ ] Update the skill to consume policy results rather than repeat parsing instructions. Existing setup-generated valid policies remain usable.

## Notes

Source: the parent specification, especially fail-closed policy handling and literal MCP names. Keep source-confirmation and use-authorization data distinct now so ticket 03 can build on this contract without undoing implicit grants.

## Comments

### Implementation review

Policy resolution, strict invalid-file handling, literal MCP names, and effective-state guard are implemented. The public suite covers both modes, precedence, invalid values, dotted names, and guard mismatch. Isolated real CLI listing probes verify override syntax; real consultation remains unverified.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.
