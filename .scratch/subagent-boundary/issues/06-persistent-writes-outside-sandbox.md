# 06 — Codex notes and goals tools write outside the read-only sandbox

Status: needs-triage

**What to build:** a read-only consultation lists `notes.write_file`/`append_to_file`/`list_files_by_prefix` and `create_goal`/`update_goal` (live probes, 2026-10-06). They write to Codex's own stores, not the project, but notes persist across Codex sessions, so injected content could plant instructions for later sessions. Find where they write, whether a consultation can switch them off (feature flags or `-c`), and decide.

**Blocked by:** None — can start immediately.

- [ ] Facts on what each tool writes and where; decision; if switched off, a live probe shows the tools absent and ordinary consultations unaffected.
