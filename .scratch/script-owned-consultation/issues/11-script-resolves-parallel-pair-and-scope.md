# 11 — The script resolves a parallel pair and reports whether the choice differs from the baseline

**What to build:** The resolve operation from ticket 10 also handles a parallel consultation. It parses a leading comma-separated pair and resolves each member separately with its own effort. It stops before any Codex command when the request names more than two models, or when both members resolve to the same model. It also reports, for each resolved choice, whether the user's named model or effort differs from the baseline without that choice (session setting, then configuration). Claude uses that flag to decide on the scope question: this consultation only, or the rest of the session. When no interactive question is available, the choice applies only to this consultation, and Claude discloses that scope. A scope the user already stated is honored.

**Blocked by:** 10 — The script resolves the model and effort of a single-model consultation.

**Status:** ready-for-agent

- [ ] A pair resolves to two independent model/effort choices. A single ambiguous member returns its candidates without resolving the other one silently.
- [ ] Three or more models, or a pair that resolves to the same model, stop before any Codex command with a reason.
- [ ] The baseline-difference result is correct for a named model, a named effort, both, and a choice equal to the current setting (no scope question in the last case).
- [ ] Offline tests through the public script interface cover each of the above.
- [ ] The parallel and session-override Claude-facing cases pass on their argv and behavior graders. Wording graders belong to ticket 09.
- [ ] The skill's pair and scope prose is replaced by the script's status, and the ADR 0005 note from ticket 10 covers this too.
