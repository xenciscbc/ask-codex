# 02 — Post-run tripwire for child-agent activity

Status: needs-triage

**What to build:** codex-cli 0.159.3's `exec --json` stream already shows `collab_tool_call` items for the parent's `wait` when a child runs (live2, live-t1 and probe-disabled evidence; not the spawn itself), and 0.160.0 reportedly emits more `collab_tool_call` events (openai/codex#50880). A cheap scan of a consultation's events for such entries would flag a regression of the child-agent switches (ADR 0008) on newer CLIs. Version-dependent: a tripwire, not a guarantee.

**Blocked by:** None — can start immediately.

- [ ] collect reports any child/collaboration event it finds, without attributing it to an opinion; offline test with a stub event.
