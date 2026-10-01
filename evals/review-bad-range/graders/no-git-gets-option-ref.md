---
type: tool_used
tool: Bash
input_match: '"command"\s*:\s*"(?:[^"\\]|\\.)*\bgit\b(?:[^"\\]|\\.)*--output=x'
min: 0
max: 0
---

Supplementary: a range endpoint starting with `-` is rejected before any git command receives it, so no git command line carries `--output=x` (not even quoted after `--end-of-options`).
