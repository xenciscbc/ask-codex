# 06 — Claims are verified and the exercise's data stays isolated

**What to build:** Claude reproduces every bug claim itself in the same disposable target before calling it confirmed, disposes every layout problem and UX suggestion with a reason, and keeps the exercise away from the user's real data: isolated data is prepared for the copy, external dependencies are listed and asked about before the app starts, and dev data is used only when the user says so in the conversation for this exercise, flagged at the top of the report. Chosen evidence can be kept at a location the user names; everything else goes with the target (spec: "Claude's side"; user stories 21–25, 45–48, 53–54; Decision log Q11, Q13, Q14, Q16; probe P2b).

**Blocked by:** 05 — `/ask-codex:ui` runs an exercise end to end.

**Status:** ready-for-agent

- [ ] Each bug claim is reproduced by Claude in the browser on the same target; reproduced → confirmed; not reproduced → "not confirmed" with what Claude tried; nothing is dropped silently.
- [ ] Each layout and UX claim is disposed as adopt, reject or investigate with a reason.
- [ ] Before starting the app, Claude prepares isolated data for the copy (seeded database copy, test accounts) and lists every external dependency of the backend, asking before starting.
- [ ] Dev data is used only on an explicit statement by the user in this conversation for this exercise; project files and memory never switch it on; when used, the report's top says so and that the exercise may have written outside the target.
- [ ] Screenshots and logs are removed with the target unless the user asks to keep chosen evidence; kept evidence is moved to the user-named location before the target is removed.
- [ ] Evals at Seam 3: unreproduced bug marked not confirmed; dev data only with an explicit statement (a project file asking for dev data does not switch it on); external dependency asked before start; at `--runs 3`, deterministic graders preferred.
- [ ] Regression as in 05 against 05's commit.

## Comments
