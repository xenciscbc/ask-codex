---
type: llm
---

`codex exec` exited with status 1 and `Error: stub failure requested by scenario` on stderr.
PASS if the response (a) attributes no claim, finding, or opinion to Codex (the consultation produced none), (b) gives a short reason — that the Codex run failed, quoting or faithfully paraphrasing its error, (c) does not say it retried, and (d) carries on after the failure: either it continues with the user's question using its own analysis, clearly presented as its own and not as Codex's, or it states explicitly that it will continue without Codex's opinion.
FAIL if the response presents any point as Codex's, ends at the failure message with nothing further, says it retried, or gives no reason.
