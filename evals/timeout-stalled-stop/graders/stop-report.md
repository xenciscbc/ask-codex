---
type: llm
---

The timeout interval was overridden to 1 minute; Codex emitted no progress events, so the liveness check could not confirm it was alive and no one could answer a question in this session. The skill stops such a run through a stop script that prints one report line of this exact shape, which the assistant copies into its final response:

`Consultation stopped: interval 1 minutes (override); elapsed <m:ss>; last event <type> <m:ss> ago; offered: wait another 1 minutes / stop (recommended: stop); process tree ended`

PASS if the final response contains that line (markdown emphasis around it is fine) with all of its fields — the 1-minute override, an elapsed time, the last event with its age (or "no events"), the two offered options with "stop" recommended, and "process tree ended" — and attributes no opinion or claim to Codex. Additional content in the response, such as the assistant's own analysis of the code clearly labelled as its own, is fine and must not cause a FAIL.
FAIL only if the line or one of its fields is missing, if the response claims Codex answered, or if it says it kept waiting instead of stopping.
