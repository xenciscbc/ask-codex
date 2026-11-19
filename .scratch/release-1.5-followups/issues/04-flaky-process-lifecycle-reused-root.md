# 04 — `process-lifecycle.test.mjs` intermittently fails "status names the reused-root identity mismatch"

Status: needs-triage

Source: release-1.5's final check at d455bfd, 2026-11-19.

- **The failure:** in the full offline suite, run one file after another, `node evals/_harness/process-lifecycle.test.mjs` failed at line 272 with `status names the reused-root identity mismatch`.
- **Reruns:** four isolated reruns right afterwards all passed (39 lifecycle assertions). The test also passed in the full-suite runs at f7250a7 and 13b0c46.
- **Not this plan's change:** `run.sh`, `stop.sh`, `wait.sh`, `_exec.sh` and the test itself are unchanged since the plan's base revision.
- **Earlier occurrence:** an earlier note recorded the same file as flaky once under a parallel runner, during approval-boundary in 1.3.3.

- [ ] Find the timing dependency in the reused-root case (PID reuse, process-identity snapshot) and make the test deterministic, or document the flake.

## Comments
