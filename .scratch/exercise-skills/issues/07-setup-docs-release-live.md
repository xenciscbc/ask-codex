# 07 — Setup check, documentation, release and live acceptance

**What to build:** a machine can be prepared for exercises from `/ask-codex:setup`, both READMEs describe the UI exercise honestly, ADR 0009 is accepted, the version is raised to the next minor release, and one real UI exercise against a throwaway web app with a frontend and a backend passes before tagging (spec: "Setup", "Pinned version policy", "Version", "Testing Decisions — Seam 4"; user stories 61, 67–70; memory: live-verify before release, live testing on this machine).

**Blocked by:** 06 — Claims are verified and the exercise's data stays isolated.

**Status:** ready-for-agent

- [ ] `/ask-codex:setup` checks the exercise dependencies: Chrome version, node, and that the pinned MCP starts.
- [ ] README (English and Traditional Chinese) describes `/ask-codex:ui`, its boundary and its difference from Codex's own browsers; states that the browser's network limit is Chrome configuration plus an MCP allowlist, not an OS sandbox; states that Codex's shell can reach every localhost service in all ask-codex skills (P2, P8c); lists what was not verified (DNS prefetch, headed mode).
- [ ] The pinned MCP version policy is documented: raising it is a release that reruns the P3–P5 and P7 probes.
- [ ] ADR 0009 status accepted; CONTEXT.md terms 演練 and 可丟棄目標 present.
- [ ] Version raised to the next minor release in the plugin and marketplace manifests.
- [ ] Live acceptance (real Codex; the number of calls is stated to the user before starting): one exercise against a throwaway frontend + backend app with `config.toml` hash and PID baselines; screenshots are seen by Codex; guards pass; afterwards the target, the app processes, Codex and the MCP Chrome are gone and `config.toml` is unchanged. Evidence recorded.
- [ ] Tag and push only on the user's word.

## Comments
