# 03: Separate and bind MCP confirmations and use authorization

**What to build:** Users can confirm a project MCP definition without unintentionally enabling it. Explicit use authorization is scoped to the confirmed definition; unchanged definitions reuse session confirmation, while changed definitions require a new decision. Both interactive and headless consultations handle pending confirmation clearly.

**Blocked by:** 02 — Resolve consultation policy and enforce the MCP guard.

Status: needs-triage

- [ ] Source confirmation and use authorization remain separate decisions. Confirming a definition alone leaves an otherwise disallowed server disabled.
- [ ] One question may obtain multiple pending decisions only when it clearly names their kind, scope, and which servers would become usable. No generic confirmation silently grants broader access.
- [ ] Preserve the existing distinction among project policy widening, project Codex definitions, and listing-detected project-defined servers, including applicable decline outcomes and preflight ordering.
- [ ] Bind confirmation to the actual definition and original authorization scope within the session. A same-name change to command, arguments, endpoint, environment configuration, or other definition content invalidates the earlier confirmation; unchanged definitions do not prompt again.
- [ ] Definition comparison and user-facing change descriptions do not expose sensitive values. Explain which aspects changed without echoing credentials.
- [ ] Only the user's own request or answer grants confirmation. Files, tool output, Codex output, and the assistant's generated templates cannot grant consent.
- [ ] Unresolved headless confirmation prevents execution and produces an actionable final report. Declines produce the appropriate outcome without repeated requests or invented permission.
- [ ] The execution boundary refuses to consume stale confirmation for a definition that changed before execution; fresh effective-policy checking remains required.
- [ ] Stub tests exercise definition-bound decisions and policy outcomes. Skill-facing scenarios exercise combined questions, unchanged confirmation reuse, changed definitions, declined and pending headless decisions, and spoofed confirmation sources.
- [ ] Update skill/setup explanations so users understand the separate decisions, while preserving the disclosure that permitted MCP tools operate outside the read-only shell sandbox.

## Notes

Source: Q6 and Q8 and ADR 0005. This ticket does not turn MCP servers into read-only tools or introduce persistent authorization across unrelated sessions.

## Comments

### Implementation review

Definition-bound source and use decisions are implemented, with reuse/invalidation/decline/secret-output checks. The pending headless case passed; interactive combined decisions and full spoofed-confirmation acceptance remain open.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.
