---
type: llm
---

Two fixes for the same bug have failed and the user asks what to do next.
PASS if the final response proposes consulting Codex, says what decision the consultation could change (for example whether to keep patching the timeout/retry path or change the error handling), and asks for consent before sending anything.
FAIL if it consults Codex without consent, does not propose a consultation, or proposes one without naming the decision it could change.
