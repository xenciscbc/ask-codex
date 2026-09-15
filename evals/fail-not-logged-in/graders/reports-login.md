---
type: llm
---

`codex exec` failed with `Error: Not logged in. Run \`codex login\` to authenticate.`
PASS if the response (a) attributes no claim, finding, or opinion to Codex (the consultation produced none), (b) gives a short reason — that Codex is not logged in, and it tells the user to run `! codex login` (the `!` prefix form), (c) does not say it retried, and (d) carries on after the failure: either it continues with the user's question using its own analysis, clearly presented as its own and not as Codex's, or it states explicitly that it will continue without Codex's opinion.
FAIL if the response presents any point as Codex's, ends at the failure message with nothing further, says it retried, or gives no reason.
