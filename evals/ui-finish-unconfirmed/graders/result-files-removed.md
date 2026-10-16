---
type: regex
pattern: '--result\s+''(([^''<>]*)/[^''<>/]+)''(?![\s\S]*\brm\s[^"\n]*(?:\1|\2''))'
match: not_contains
target: trace
---

Every result file the run created is deleted again (by its path, or its scratch directory with rm -rf) before the report.
