---
description: "Probe (no skill): are TaskOutput and TaskStop usable in an eval child with the ticket-07 grant?"
max_turns: 10
timeout_seconds: 300
allowed_tools: [Bash, TaskOutput, TaskStop]
---

Start `sleep 120` with Bash `run_in_background: true`. Call `TaskOutput` on that task with `block: true` and `timeout: 5000` and report the status it returns. Then call `TaskStop` on it and report the result.
