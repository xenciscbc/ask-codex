# 03 — Web search is an outbound channel in read-only consultations

Status: needs-triage

**What to build:** a consultation still exposes `web.run` (live probes, 2026-10-06). It is not governed by the shell network block and could carry project content out under injected instructions. Decide whether consultations should disable web search (and how, on this CLI) or document it.

**Blocked by:** None — can start immediately.

- [ ] Decision recorded; if disabled, a live probe shows `web.run` absent and ordinary consultations unaffected.
