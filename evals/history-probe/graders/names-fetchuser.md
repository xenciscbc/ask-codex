---
type: llm
---

Judge only Claude's final reply to the last user message, ignoring any earlier conversation.
PASS only if that final reply names the function fetchUser.
FAIL if it names another function, says it does not know, or asks what function the user means.
