# 03 — Event-stream reply: hardening and wording notes from release-1.5 reviews

Status: needs-triage

Source: release-1.5. These are non-blocking findings from ticket 02's implementation, code review and outcome verification, and from ticket 03's code reviews. None was a blocking finding. Each one either fails closed or affects wording only. Quoted findings are reviewer output, treated as data.

1. **Gigantic single line.** This was fixed in release-1.5 after its Adversarial review: a `MemoryError` while reading, decoding or parsing now makes only that run unreadable. What remains:
   - The fix is tested with a mocked `MemoryError`, not with a real gigantic allocation.
   - D2's cleaning of a huge parsed failure message, and `classify` of a huge reply, can still raise.
   - Whether Codex caps `aggregated_output` is unverified.
   - A huge reply that is still readable can raise `MemoryError` in `main()`'s `json.dumps` of the `collect` result. The outcome verification of ticket 02 found this under a job memory limit: a 21 MB `agent_message` at 80–90 MB. The whole `collect` then fails and the other run is not delivered. This predates the plan, because the `-o` path also serialized the reply. ADR 0011's "never affects another run" holds only for failures inside `read_stream`.
2. **Characters the D2 cleaning list does not cover.** U+200E, U+200F, U+061C (LRM, RLM, ALM), U+2060 and other zero-width characters, and U+FEFF can stay in a `Codex reported:` reason. Lone surrogates (JSON `\udXXX`) can reach a reply or reason. That is safe today because output uses `ensure_ascii=True`, but writing them with `ensure_ascii=False` would raise `UnicodeEncodeError`. Extending the list needs a spec change.
3. **ZWSP-only final message.** A final `agent_message` holding only U+200B is not whitespace, so it is taken as a reply, which `classify` then marks unstructured.
4. **Trailing space.** After the 500-character cut there is no second strip, so a reason can end in a space.
5. **README wording, part 1 (ticket 03's later review):** the very-large-line note does not mention reason precedence. A launcher reason or "not logged in" wins over `Codex events could not be read`. The note also says "a line too large" where the ADR covers any `MemoryError` in `read_stream`, and "detected" in the residual-risk note means the run has no reply.
5b. **README wording, part 2.** The "Where the reply comes from" list leaves out "nested too deeply to parse". The failure-text paragraph does not mention the precedence (launcher reason, not logged in, unreadable stream) or that a reason empty after cleaning keeps the base reason. The indented "Plain-text lines are skipped." turns the list into a loose list when rendered.
6. **1.4 retained runs.** A run retained by 1.4 keeps `last-message.json`, which holds reply content, after 1.5's prune, because the prune list no longer names that file.
7. **Residual risk N9, widened (accepted by the user on 2026-11-19).** A process holding Codex's stdout can rewrite the stream and plant a reply. It can insert before Codex's own final `turn.completed`, or seek-overwrite after Codex exits, because `launch()` opens `events.jsonl` with `"wb"`. This was reproduced synthetically by release-1.5's Adversarial review. It is documented in ADR 0011 and the README. Possible hardening:
   - Give Codex an append-only handle (Windows `FILE_APPEND_DATA` without `FILE_WRITE_DATA`; note that POSIX `O_APPEND` can be cleared with `fcntl`).
   - Or verify with real Codex whether sandboxed commands inherit the handle at all.

- [ ] Triage each item: fix it, document it, or close it.

## Comments
