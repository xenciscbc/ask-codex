---
type: llm
---

The timeout override was set to "abc", which is not a positive whole number.
PASS if the final response says the override "abc" was ignored and the default of 30 minutes applies, and the consultation result is presented normally.
FAIL if it treats "abc" as a valid interval, says nothing about the override, or presents no Codex result.
