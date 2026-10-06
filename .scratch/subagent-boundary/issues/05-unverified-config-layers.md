# 05 — Child-agent switches against the user config layer, WSL and other platforms

Status: needs-triage

**What to build:** the switches were live-verified on Windows against the default configuration, a v1 and a v2 model, command-line feature enabling, and a trusted project's `.codex/config.toml` enabling agents/MultiAgentV2/fan-out/multi_agent. Not verified: the user's own Codex config enabling them (a live check edits the user's config; documented precedence says the command line wins) and WSL/Linux.

**Blocked by:** None — can start immediately.

- [ ] With the user's consent, a probe with a temporary user-level setting (restored afterwards, config.toml bytes compared) and one probe under WSL.
