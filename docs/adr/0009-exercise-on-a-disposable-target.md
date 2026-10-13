---
status: proposed
---

# Exercises: Codex may act, but only on a disposable target

A UI review needs Codex to operate a running app, which a read-only consultation cannot do. We add a second kind of interaction, the exercise (演練, `CONTEXT.md`), started only by a user-typed command (first: `/ask-codex:ui`). In an exercise Codex may act — drive an isolated, network-restricted Chrome against the app — but only on a disposable target: a newly created directory holding a copy of the project and the localhost services Claude starts from it, removed at the end. Codex's shell stays read-only, it can never request escalation, and Codex never touches the user's project. `ask`, `review` and `discuss` keep their read-only guarantee unchanged; the exercise is a separate guarantee, not a widened consultation. The result is still claims that Claude judges; bug claims count only after Claude reproduces them.

## Considered Options

- **Widen the consultation** so that every skill may act: rejected — it would weaken the guarantee the three existing skills make, for a capability only one use needs.
- **Move UI testing out of ask-codex** into another plugin: rejected — it would duplicate the script-owned execution boundary (ADR-0005), the MCP policy (ADR-0003) and the stop path (ADR-0004).
- **Claude drives the browser and Codex directs it from screenshots**: rejected by the user — Codex's own exploration is the point of the exercise.
- **Codex's own browsers** (Chrome extension, in-app browser): only available in the Codex desktop app, not from `codex exec`.

## Consequences

- The browser runs outside Codex's sandbox (MCP servers always do, ADR-0003). Its network is limited by Chrome configuration (a closed proxy with only the app's host:ports bypassed) plus the MCP URL allowlist; neither is an OS sandbox, and the URL allowlist alone let Service Worker requests through (probe P7, `.scratch/exercise-skills/probe-results.md`). A browser guard re-checks these paths before an exercise.
- Where the disposable target lives is decided only by user-level sources (the user's instructions, memory or conversation); project instructions can only suggest, because the target is where the exercise writes and what it deletes.
- Codex's shell can reach every localhost port on the machine even with network off (P2, P8c); Codex configuration cannot prevent it on Windows. This is documented, not solved, and applies to all skills.
