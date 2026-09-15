# 10 — READMEs (English and Traditional Chinese)

**What to build:** Two short, cross-linked READMEs — `README.md` in English and `README.zh-TW.md` in Traditional Chinese — so a new user can understand ask-codex and start using it. Each briefly covers: purpose (consultation, not delegation; Codex stays read-only; Claude judges each claim), installation as a Claude Code plugin from the GitHub repository, prerequisites (Codex CLI installed and logged in), usage (manual via `/ask-codex:ask` or a verbal request; proactive consultation and the three consent options; model aliases and effort rules; parallel consultation; follow-up consultation), and known risks (the read-only sandbox can read the whole disk and scope is limited only by instruction; ~25k-token base cost per call; the Codex CLI version verified in ticket 09). The two versions carry the same content; terminology follows `CONTEXT.md` (Chinese terms in the zh-TW version, their English equivalents in the English one). See spec: user stories 72–74.

**Blocked by:** 09 — Live acceptance.

**Status:** ready-for-agent

- [ ] Both files exist at the repository root and link to each other at the top.
- [ ] Both cover purpose, installation, prerequisites, usage, and known risks, and stay brief.
- [ ] The installation steps are the ones actually used during live acceptance.
- [ ] The tested Codex CLI version and any deviations recorded in ticket 09 are reflected.
- [ ] Terminology matches `CONTEXT.md` in each language; no glossary-avoided synonyms.
