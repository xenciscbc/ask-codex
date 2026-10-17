# 05 — `/ask-codex:ui` runs an exercise end to end

**What to build:** the user types `/ask-codex:ui [model tokens] [--headed] [scope or focus]` and gets a complete exercise: Claude resolves the target root from user-level sources only, works out and confirms the app's start commands and ports, starts the app from the copy, runs the guards, sends the UI framing prompt, runs Codex, and writes a report that starts with the scope line, lists out-of-scope observations separately and never fixes anything; at the end everything is stopped and the target removed. The skill is user-only; `ask` answers natural-language UI test requests by naming the command (spec: Solution, "Framing prompt", "Claude's side"; user stories 1–14, 19–20, 26–27, 39–43, 49–52; ADR 0006/0007 user-only pattern).

**Blocked by:** 03 — Guards stop an exercise whose browser restriction does not hold; 04 — App processes are part of the exercise's start, stop and cleanup.

**Status:** resolved — accepted by the user's accept-and-land decision at bff1479 (2026-10-17); code review APPROVED and outcome verification CONFIRMED at 5621b3b (2026-10-16); Adversarial review BROKEN at bff1479; see Comments

**Plan:** acceptance amended by `../plan.md` rev 6, claim C5 (invariants listed there).

- [ ] The skill cannot be invoked by the model; the plugin's skill list includes it; `ask` has a pointer line naming `/ask-codex:ui` for UI testing requests.
- [ ] Model tokens resolve through `ask`'s resolve step with the consultation effort floor; two model tokens are refused before anything starts.
- [ ] The target root comes only from the user's global instructions, memory or this conversation; a location suggested by project instructions is asked, not used; with no user-level source Claude asks.
- [ ] Start commands, ports and environment are worked out from the copy and confirmed with the user (user-stated values win) before the app starts.
- [ ] The framing prompt tells Codex to discover its browser tools first, stay in scope, judge from screenshots, check several viewports including a phone size, read console and failed network requests, and list out-of-scope observations separately; it carries a unique marker line.
- [ ] Without a scope the framing asks for the app's main flows; with `--headed` the request's headed flag is set, otherwise headless.
- [ ] The report's first line is the scope line: app, ports, scope, model, headless or headed, data source, guard ran or reused from cache.
- [ ] "No claims" is never presented as approval of the UI; no fix is made or offered as done.
- [ ] Temp files are in the scratch location and removed after the report; nothing is written into the project.
- [ ] Evals at Seam 3 (deterministic graders over final messages and traces): not model-invocable and natural-language request answered with the command only at `--runs 5`; project-suggested target location asked, not used; report starts with the scope line and separates out-of-scope items; no fix offered as done; other cases at `--runs 3`.
- [ ] Regression: `second-opinion-with-stance`, `targeted-check`, `review-working-tree` at `--runs 3` on `1ca7a0f` and on this ticket's commit; no grader's pass rate drops beyond named pre-existing patterns.

## Comments

- 2026-10-17 — Adversarial review at bff1479 BROKEN (I11): the same redaction gap as ticket 02, including a Markdown-bold label layout. I16, I9 and I13 held. Accepted as a known residual; fix tracked as a follow-up.
