---
type: regex
pattern: 'prepare\s+''(([^''<>]*)/[^''<>/]+)''(?![\s\S]*\brm\s[^"\n]*(?:\1|\2''))'
match: not_contains
target: trace
---

The request file (it holds the prompt) is deleted again.
