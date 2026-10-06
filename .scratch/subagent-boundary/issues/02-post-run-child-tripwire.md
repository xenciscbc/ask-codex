# 02 — Post-run tripwire for child-agent activity

Status: needs-triage

**What to build:** codex-cli 0.159.3's `exec --json` stream shows no child activity, but 0.160.0 emits `collab_tool_call` events (openai/codex#50880). A cheap scan of a consultation's events for such entries would flag a regression of the child-agent switches (ADR 0008) on newer CLIs. Version-dependent: a tripwire, not a guarantee.

**Blocked by:** None — can start immediately.

- [ ] collect reports any child/collaboration event it finds, without attributing it to an opinion; offline test with a stub event.
