---
type: llm
---

The user ran /ask-codex:ask with no question after describing, earlier in the conversation, that fetchUser returns an empty object when the API times out.
PASS if the final response shows the question that was sent to Codex (about fetchUser / the timeout behaviour) in a short line before or alongside Codex's result.
FAIL if the response does not say what was asked, asks the user for a question instead of consulting, or presents no Codex result.
