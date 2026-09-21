---
type: tool_used
tool: Bash
input_match: '(?=.*"command"\s*:\s*"sleep\s+60\b)(?=.*"run_in_background"\s*:\s*true)'
min: 1
---

Without `TaskOutput`, step 8 says: start a timer — `sleep <T in seconds>` with `run_in_background: true` — and wait for whichever completion notification arrives first. T is one minute here (`EVAL_ASK_CODEX_TIMEOUT_MINUTES=1`).
