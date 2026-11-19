# 01 — `snapshot` raises on a non-object last line of `events.jsonl`

Status: needs-triage

Source: release-1.5, ticket 02's second plan review, item N8. The defect predates that plan; spec D1 deliberately left `snapshot` unchanged.

**The defect.** `consult.py` `snapshot()` reads the last line of a run's `events.jsonl` with `json.loads(...).get("type")`. When that line is valid JSON but not an object, for example `null`, `[]` or `42`, `.get` raises `AttributeError`. `main` does not catch `AttributeError`, so `wait` fails with a traceback instead of returning JSON.

**Who can trigger it.** Codex never writes such a line. Another process that inherited Codex's stdout could, the same handle path that spec F1 describes.

- [ ] Treat a non-object last line as `last_event: "unknown"`, as an unparsable line already is. Add an offline test.

## Comments
