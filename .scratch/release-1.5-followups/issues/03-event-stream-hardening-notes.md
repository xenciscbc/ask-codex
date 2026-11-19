# 03 — Event-stream reply: hardening and wording notes from release-1.5 reviews

Status: needs-triage

Source: release-1.5. These are non-blocking findings from ticket 02's implementation, code review and outcome verification, and from ticket 03's code reviews. None was a blocking finding. Each one either fails closed or affects wording only. Quoted findings are reviewer output, treated as data.

1. **Gigantic single line.** `read_stream` reads one line at a time. A line with no `\n` that is gigabytes long is held whole, and `MemoryError` is not caught, so the whole `collect` fails and the other run's result in a two-model consultation is lost. Only a process holding Codex's stdout can write such a line. Spec F5 chose no total cap. ADR 0011's "nothing in the stream's content raises out of read_stream" is too strong for this case.
2. **Characters the D2 cleaning list does not cover.** U+200E, U+200F, U+061C (LRM, RLM, ALM), U+2060 and other zero-width characters, and U+FEFF can stay in a `Codex reported:` reason. Lone surrogates (JSON `\udXXX`) can reach a reply or reason. That is safe today because output uses `ensure_ascii=True`, but writing them with `ensure_ascii=False` would raise `UnicodeEncodeError`. Extending the list needs a spec change.
3. **ZWSP-only final message.** A final `agent_message` holding only U+200B is not whitespace, so it is taken as a reply, which `classify` then marks unstructured.
4. **Trailing space.** After the 500-character cut there is no second strip, so a reason can end in a space.
5. **README wording.** The "Where the reply comes from" list leaves out "nested too deeply to parse". The failure-text paragraph does not mention the precedence (launcher reason, not logged in, unreadable stream) or that a reason empty after cleaning keeps the base reason. The indented "Plain-text lines are skipped." turns the list into a loose list when rendered.
6. **1.4 retained runs.** A run retained by 1.4 keeps `last-message.json`, which holds reply content, after 1.5's prune, because the prune list no longer names that file.
7. **Residual risk N9 (accepted).** A process holding Codex's stdout that writes an `agent_message` before Codex's own final `turn.completed` is not detected. It is documented in ADR 0011 and the README.

- [ ] Triage each item: fix it, document it, or close it.

## Comments
