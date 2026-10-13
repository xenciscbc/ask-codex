# 03 — Guards stop an exercise whose browser restriction does not hold

**What to build:** before Codex starts, the exercise checks its dependencies and proves the browser's network restriction with a fixed check page, without calling Codex. A failed guard means no Codex launch. A passed guard is reused while the configuration fingerprint is unchanged and for at most 12 hours. The live run of the guard with real Chrome is the first proof that the launch settled in 02 passes the bypass list literally (spec: "Guards as a CLI subcommand", "Guard cache"; user stories 55–60; probe P7, P7b with `probe-leaks.py` as prior art).

**Blocked by:** 02 — An exercise runs through the script on a disposable target.

**Status:** ready-for-agent

**Plan:** acceptance amended by `../plan.md` rev 5.1, claim C3 (invariants listed there).

Security-critical (it is the check that the browser restriction holds): needs a security review and an approved plan before any change.

Open point for the plan: the check page is served on an exercise port's loopback host, while the app also needs those ports. Settle whether the guard runs before the app takes its ports or how the page's port relates to the fingerprint, without letting a guard on one configuration cover another.

- [ ] Dependency check: the installed Chrome stable version is read from the system and must be 149 or later; node must be present; either failure stops the exercise with a clear message and no Codex call.
- [ ] Browser guard: starts the exercise's MCP launch configuration directly over stdio (no Codex) and requires: the check page loads; image, iframe, fetch, WebSocket, Worker, sendBeacon and Service Worker requests to another loopback port are blocked (a guard-owned listener receives nothing); page and Service Worker requests to an external host fail; WebRTC yields no server-reflexive candidate.
- [ ] The guard leaves no Chrome or MCP process behind (checked against a PID baseline in the live check).
- [ ] Cache: key = Chrome executable version, MCP package version and the full launch argument list; stored with the user-level run state, never in the project; reused within 12 hours on an identical key; any key change or expiry forces a new run.
- [ ] An exercise run refuses to start Codex without a current pass for its exact fingerprint (offline at Seam 2, the guard replaced by a fake through the environment: fail → no Codex launch; cache hit → no guard run; changed port, Chrome or MCP version → guard runs again; 12 hours + 1 second → guard runs again).
- [ ] The report data names whether the guard ran or was reused from cache, and when it passed.
- [ ] Live, no Codex: with the real configuration the guard passes; with the bypass list removed (Service Worker gap) the guard fails. Both runs recorded as evidence.

## Comments
