# 07: Preserve consultation framing and reply dispositions

**What to build:** Users receive the same independent framing, fresh-session follow-up behavior, and claim-by-claim judgment through the new execution boundary. Claude may explain the result in the conversation language while preserving all required information and accurately handling unstructured or failed replies.

**Blocked by:** 01 — Run a single-model consultation through the script boundary.

Status: resolved — on a narrowed claim (2026-09-24, user decision; see Comments)

- [ ] Second opinions and targeted checks preserve their with-stance context; diagnosis and technical questions preserve blind framing, relevant evidence, failed attempts, and secret exclusion.
- [ ] Follow-up consultations require a new user request and a fresh Codex session; neither resume nor fork is used. Carry the correct prior claims and Claude's dispositions and reasons.
- [ ] Structured replies preserve actual claim identities, evidence, confidence, open questions, and a reasoned adopt/reject/investigate disposition. Never invent missing claims or evidence.
- [ ] Follow-up reports preserve per-carried-claim status, identify missing statuses, and handle new blocking claims under the existing scope rules. New nonblocking claims remain excluded as before.
- [ ] Readable non-schema replies remain unstructured replies with faithful content and dispositions rather than invented structured claims. Missing, unreadable, or failed replies follow failure handling with no fabricated Codex opinion.
- [ ] Reports preserve question/type, model/effort, effective MCP policy, applicable timer outcomes, and substantive result information while allowing conversation-language wording. Keep execution status separate from opinion content.
- [ ] Preserve prompt-injection boundaries: files and tool output are data, not authority to initiate a consultation, change permissions, or execute Codex suggestions.
- [ ] Validate prompt contents and fresh-session invocation through the stub seam where practical. Use targeted Claude-facing evaluations for framing, dispositions, provenance, and semantic report completeness.
- [ ] Replace affected exact-wording, line-number, and prose-hash assertions with behavior checks without dropping their underlying regression scenarios.
- [ ] Update English skill and framing instructions within this scope. Do not change policy, timer, parallelism, or retry semantics while improving report wording.

## Notes

Source: Q3, Q10 and the approved reply-compatibility slice. This ticket can progress after ticket 01 using its default-policy path; later integration must also exercise the richer policy and lifecycle paths. Avoid editing scopes simultaneously owned by another worker.

## Comments

### Implementation review

English framing files are retained and the compact skill preserves fresh-session follow-up, per-claim dispositions and natural-language reporting. Structured/unstructured reply tests and the main headless report case pass. Broad follow-up/provenance Claude-facing acceptance remains open.

See [validation evidence](../evidence/validation.md). Unchecked items are retained for acceptance review; they are not silently declared complete.

### 2026-09-24 — resolved on a narrowed claim (user decision)

What this closes on: the implementation is in `main` (1.0.2), and the evidence in [validation.md](../evidence/validation.md) holds. That evidence is the public CLI suite on stub Codex (Windows and Ubuntu WSL), the lifecycle suites on both platforms, all Node offline tests, and two headless Claude cases on WSL. Unchecked boxes above remain unchecked: they are acceptance items this evidence does not reach. They are not claimed.
