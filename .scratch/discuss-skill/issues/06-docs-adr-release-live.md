# 06 — Docs, ADR-0007, version 1.3.0, one live discussion and independent verification

**What to build:** users and future maintainers can find and understand the discussion: the README in both languages shows usage lines and a capability paragraph, lists the honest limits as known risks (call multiplication and re-exploration per round, anti-conformity rules are instructions not enforcement, Codex output carried forward is data), and points to the MCP policy section and to `codex mcp list` for allowlist server names. ADR-0007 records the user-only discuss skill, the fresh-session-per-round decision with its sources (openai/codex#40149, #49078; arXiv 2603.16244, 2606.00820, 2509.05396) and the selectable reply schema. The glossary changes only if implementation changed a term. Plugin version 1.3.0. Then one real harmless discussion proves the whole path with a real Codex model, and a fresh verifier checks the full spec claim. Plan slice S3 (spec user stories 52–53).

**Blocked by:** 03 — round limit choice; 04 — early end with partial report; 05 — concessions need evidence, user-preference points go to the user.

**Status:** ready-for-agent

- [ ] README (both languages), ADR-0007 and version 1.3.0 describe the shipped behaviour; the glossary's 討論 section matches what shipped.
- [ ] Live: one real `/ask-codex:discuss rounds 2 <topic>` on a throwaway repository under `D:/tmp` with a real Codex model — real Codex accepts the discussion schema, both rounds structured, three-section report produced, nothing edited, Codex `config.toml` hash unchanged, no leftover Codex processes. At most 2 real Codex calls, plus one rerun only after a reproduced fix.
- [ ] A fresh `verifier` confirms the full spec claim on the final commits.
- [ ] No tag or push until the user says.
