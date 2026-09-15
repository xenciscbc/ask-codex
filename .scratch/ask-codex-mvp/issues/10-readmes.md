# 10 — READMEs (English and Traditional Chinese)

**What to build:** Two short, cross-linked READMEs — `README.md` in English and `README.zh-TW.md` in Traditional Chinese — so a new user can understand ask-codex and start using it. Each briefly covers: purpose (consultation, not delegation; Claude judges each claim) with the narrowed claim verbatim — "Codex's shell commands run read-only (writes denied, shell network blocked). MCP servers run outside that sandbox: by default all are disabled per consultation; servers you allow (or, in minimal-deny mode, all except node_repl/cua_repl) remain usable and may include tools that write or execute, limited only by instruction." — installation as a Claude Code plugin from the GitHub repository, prerequisites (Codex CLI installed and logged in), usage (manual via `/ask-codex:ask` or a verbal request; proactive consultation and the three consent options; model aliases and effort rules; parallel consultation; follow-up consultation; MCP policy, ask-codex config files and `/ask-codex:setup`), known risks (Codex's shell can read any file the user's account can read and scope is limited only by instruction; allowed MCP servers run outside the sandbox; ~25k-token base cost per call; the Codex CLI version verified in ticket 09), and known limitations (projects on a drive where the Codex Windows sandbox cannot run; persistently trusted projects covered only by the project-layer fail-safe). The two versions carry the same content; terminology follows `CONTEXT.md` (Chinese terms in the zh-TW version, their English equivalents in the English one). See spec: user stories 72–74.

**Blocked by:** 09 — Live acceptance; 11 — MCP policy configuration and setup.

**Status:** ready-for-agent

- [ ] Both files exist at the repository root and link to each other at the top.
- [ ] Both cover purpose, installation, prerequisites, usage, and known risks, and stay brief.
- [ ] The installation steps are the ones actually used during live acceptance.
- [ ] The tested Codex CLI version and any deviations recorded in ticket 09 are reflected.
- [ ] Terminology matches `CONTEXT.md` in each language; no glossary-avoided synonyms.
