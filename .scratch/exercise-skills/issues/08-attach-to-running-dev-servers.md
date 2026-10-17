# 08 — Attach mode: exercise the user's running dev servers without a copy

**What to build:** at each `/ask-codex:ui`, the user can choose attach mode instead of the copy: the exercise uses the frontend and backend the user already runs from their project, skipping the copy, install and app start. Codex still works from a new, empty disposable directory with a read-only shell and the same restricted browser, limited to the attached host:ports; the skill never starts or stops the user's servers. Because the app is the user's real dev environment, attach mode counts as using dev data: it needs the user's explicit choice in the conversation for that exercise and is flagged at the top of the report (user decision U6, 2026-10-13; plan claim C8).

**Blocked by:** 06 — Claims are verified and the exercise's data stays isolated.

**Status:** resolved — accepted by the user's accept-and-land decision at bff1479 (2026-10-17); code review APPROVED and outcome verification CONFIRMED at c284dbc (2026-10-17); Adversarial review BROKEN (low) at bff1479; see Comments

**Plan:** acceptance by `../plan.md` rev 6, claim C8 (invariants listed there).

Security-critical (the exercise acts on the user's live dev environment): needs a security analysis of attach mode and an approved plan before any change.

- [ ] The request carries the mode (`copy` or `attach`); attach mode is used only when the user chose it in the conversation for this exercise; project files and memory never select it.
- [ ] Attach mode creates no copy and starts no app process; Codex's working directory is a new empty disposable directory, never the project.
- [ ] Every attached host:port has a listener before the exercise starts; the owning process (name, command line, PID) is shown to the user and confirmed; a listener that changes owner during the exercise stops it.
- [ ] The guard proves the browser restriction without taking the attached ports; the attached ports are reachable in the restricted browser.
- [ ] Finish, stop, failure and the lifetime bounds end Codex, any repro and the exercise's own proxy holder, remove the disposable directory, and never signal the user's servers.
- [ ] The report's scope line says attach mode, the attached processes, and that Codex's browser actions may have changed the user's dev data and project files through the app.
- [ ] The confirmation discloses the accepted residuals (plan U7, U8, AT-3, AT-6, AT-10): Codex's read-only shell can reach the attached servers directly; the app's own development tools can run code as the user; what the dev server serves may reach OpenAI; its proxies use the user's credentials. The report lists Codex shell commands that name an attached port or an HTTP client.

## Comments

- 2026-10-17 — D-2026-10-16b: attach mode takes 127.0.0.1 only; `[::1]` and `localhost` are refused with a fixed sentence (chrome-devtools-mcp 1.10.1 cannot parse an unescaped `[::1]` URL pattern). Adversarial review at bff1479 BROKEN (low, I14 "ended"): a stop during the attach-mode guard reports ended and removes the target before the guard's own browser job has ended. No attached process was affected, and the guard's writes stayed confined. The listener-table rules, the owner handle, never signalling the user's servers, U10, the substituted guard and the real check held. Accepted as a known residual; fix tracked as a follow-up.
