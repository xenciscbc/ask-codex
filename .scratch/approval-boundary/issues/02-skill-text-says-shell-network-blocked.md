# 02 — SKILL.md files still say shell network is blocked

Status: needs-triage

`skills/ask/SKILL.md`, `skills/review/SKILL.md` and `skills/discuss/SKILL.md` tell Claude that Codex's shell runs "with shell network blocked". Probes P2 and P8c (2026-10-13, Windows elevated sandbox) show loopback is reachable, and 1.3.3's READMEs now say so. The skill text predates this branch (since 1.0.0) and was left out of ticket 01's scope (found in C3 code review, non-blocking 2).

- [ ] Align the three SKILL.md statements with the README execution boundary (writes and outbound network blocked; loopback reachable on Windows).
- [ ] Check graders or tests that pin the old wording.

## Comments
