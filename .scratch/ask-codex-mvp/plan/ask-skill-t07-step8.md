(Replaces the "Then wait for it to finish…" paragraph of step 8; the codex exec command itself is unchanged.)

Then watch it until it finishes. **Do not end your turn while the consultation is still running** — in a non-interactive session nothing would bring you back, and the run would be orphaned.

**Check interval.** Run `printenv EVAL_ASK_CODEX_TIMEOUT_MINUTES`.
- Prints nothing → the interval **T** is 30 minutes.
- A positive whole number (`^[1-9][0-9]*$`) → T is that many minutes; tell the user in one line that the timeout override is active (T and the staleness threshold S).
- Anything else (`0`, negative, decimal, text) → ignore it, T = 30 minutes, and tell the user in one line that the override was ignored and why.
The **staleness threshold S** is T/6 (5 minutes by default).

**Waiting.** Wait until the consultation finishes or T has passed, whichever comes first:
- If a `TaskOutput` tool is available (load it with ToolSearch if it is deferred): call it on the consultation's background task with `block: true` and a timeout of the remaining time, at most 600000 ms per call, and repeat until T has passed.
- Otherwise start a timer — `sleep <T in seconds>` with Bash `run_in_background: true` — and wait for whichever completion notification arrives first: the consultation's or the timer's.
When the consultation finishes, go to step 9.

**Check when T has passed.** Judge liveness only from the tracked task's state and the last event in `<tmp>/events.jsonl` — never from CPU use or process listings:
- Age of the last event, in seconds (one line, literal path): `echo $(( $(date +%s) - $(stat -c %Y '<tmp>/events.jsonl') ))`. The last event: `tail -n 1 '<tmp>/events.jsonl'` (name its `type`, or say "no events" if the file is empty).
- **Still running and the last event is at most S old** → tell the user in one line: elapsed time, the last event and its age, and that you keep waiting; then wait another T. No question.
- **Still running but the last event is older than S** → ask with `AskUserQuestion`, showing the elapsed time and the last event with its age, with the options "wait another T minutes" and "stop this consultation". Recommend "wait" if the last event is at most T/2 old, otherwise "stop". "Wait" starts another interval — there is no limit on how often the user may wait. "Stop" → stop path.
- **No `AskUserQuestion`** (non-interactive session): state the same question and recommendation in text, then take "stop" — you cannot wait for an answer without ending your turn.

**Stop path.** End the consultation's background task with `TaskStop`. Then handle it as a failure (see Failures): attribute nothing to Codex, clean up (step 11), and give a **final stop report** that states the interval in force (default or override), the elapsed time, the last event and its age (or "no events"), the two options that were offered with the recommended one, and that the consultation was stopped; then carry on.

**Fixed wording.** Start each of these lines with the words shown, word for word, so they are recognisable in any language:
- valid override: `Timeout override active: <T> minutes (staleness <S>).`
- ignored override: `Timeout override ignored: "<value>" is not a positive whole number; using 30 minutes.`
- confirmed-alive notice: `Codex still running — <elapsed> elapsed, last event <type> <age> ago; waiting another <T> minutes.`
- final stop report: `Consultation stopped: …` followed by the required fields.

**For step 10.** Remember the timer outcome — the interval in force (default, override active, or override ignored and why) and each check's result — and restate it in step 10 item 1.
