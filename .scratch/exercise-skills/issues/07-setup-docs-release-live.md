# 07 — Setup check, documentation, release and live acceptance

**What to build:** a machine can be prepared for exercises from `/ask-codex:setup`, both READMEs describe the UI exercise honestly, ADR 0009 is accepted, the version is raised to the next minor release, and one real UI exercise against a throwaway web app with a frontend and a backend passes before tagging (spec: "Setup", "Pinned version policy", "Version", "Testing Decisions — Seam 4"; user stories 61, 67–70; memory: live-verify before release, live testing on this machine).

**Blocked by:** 08 — Attach mode: exercise the user's running dev servers without a copy.

**Status:** resolved — accepted by the user's accept-and-land decision at bff1479 (2026-10-17); code review APPROVED and outcome verification CONFIRMED at 8124f71 (2026-10-17); not Security-critical. Released on the user's word (2026-10-19): `main` pushed and annotated tag `v1.4.0` on 5cf79fa pushed

**Plan:** acceptance amended by `../plan.md` rev 6, claim C7 (invariants listed there).

- [ ] `/ask-codex:setup` checks the exercise dependencies: Chrome version, node, and that the pinned MCP starts.
- [ ] README (English and Traditional Chinese) describes `/ask-codex:ui`, its boundary and its difference from Codex's own browsers; states that the browser's network limit is Chrome configuration plus an MCP allowlist, not an OS sandbox; states that Codex's shell can reach every localhost service in all ask-codex skills (P2, P8c); lists what was not verified (DNS prefetch, headed mode).
- [ ] The pinned MCP version policy is documented: raising it is a release that reruns the P3–P5 and P7 probes.
- [ ] ADR 0009 status accepted; CONTEXT.md terms 演練 and 可丟棄目標 present.
- [ ] Version raised to the next minor release in the plugin and marketplace manifests.
- [ ] Live acceptance (real Codex; the number of calls is stated to the user before starting): one exercise against a throwaway frontend + backend app with `config.toml` hash and PID baselines; screenshots are seen by Codex; guards pass; afterwards the target, the app processes, Codex and the MCP Chrome are gone and `config.toml` is unchanged. Evidence recorded.
- [x] Tag and push only on the user's word.

## Comments

- 2026-10-17 — Live acceptance (2026-10-17, three real Codex calls, headless Claude Code sessions by the user's decision): copy and attach mode passed. The copy-mode rerun after the framing prompt fix showed Codex sees its screenshots. Evidence is in `.scratch/exercise-skills/evidence/c7-live/`. Tag and push are not done; they wait for the user's word.
- 2026-10-19 — On the user's word, `main` was pushed (`1ca7a0f..5cf79fa`) and annotated tag `v1.4.0` was created on 5cf79fa and pushed; both were read back from the remote.
