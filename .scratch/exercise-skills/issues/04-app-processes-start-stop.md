# 04 — App processes are part of the exercise's start, stop and cleanup

**What to build:** the app's frontend and backend are started by the script from the disposable target and recorded in the exercise's run record, so that a normal finish, a failure or a stop always ends the Codex process tree, the app's process trees and the MCP-launched Chrome, and then removes the target, reusing the ADR 0004 stop path. The stop report says, per item, whether it was confirmed ended (spec: "Stop and cleanup", Claude's side "start the app from the copy"; user stories 19–20, 26–27, 62–66).

**Blocked by:** 02 — An exercise runs through the script on a disposable target.

**Status:** ready-for-agent

Security-critical (it ends processes and removes the target): needs a security review and an approved plan before any change.

- [ ] The request carries the app start commands (working directory inside the target, environment) and ports; a working directory outside the target is refused.
- [ ] Each start command runs as its own recorded process tree; the script confirms every app port answers before Codex starts.
- [ ] A start that fails or a port that never answers is reported with the app's output; no Codex call is made; every started app tree is ended and the target removed.
- [ ] The existing check interval, liveness check and stop rules apply to exercises unchanged.
- [ ] Stop and cleanup end the Codex tree, every app tree and the MCP-launched Chrome; the result reports each as confirmed ended or not, never "called stop" as "stopped".
- [ ] The target is removed after a normal finish, a failure and a stop; if removal fails, its location is reported.
- [ ] A failed or stopped exercise is never retried automatically.
- [ ] Offline at Seam 1 with the Codex stub and fake app commands (long-running listeners): after finish, failure and stop no recorded process is alive and the target is gone; a stop during app start ends the partly started app.
- [ ] All existing offline harness tests pass, including the run and stop script tests.

## Comments
