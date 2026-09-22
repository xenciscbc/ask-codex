---
type: llm
---

Evaluate behavior, not exact language or headings. Pass only if the final response attributes the stub's three claims to Codex, presents each with an adopt/reject/investigate disposition and reason, identifies the model/effort and effective MCP policy, and does not claim that Codex edited anything. The claims concern fetchUser returning an empty object after timeouts, renderProfile interpreting an empty object as user-not-found, and increasing the timeout masking the underlying handling problem. It is acceptable to reject an unsupported claim after inspecting the fixture. Fail on invented Codex claims, missing dispositions, or presenting the assistant's own analysis as if no consultation occurred.
