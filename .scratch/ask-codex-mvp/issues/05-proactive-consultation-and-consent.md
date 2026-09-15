# 05 — Proactive consultation and consent

**What to build:** Claude proposes a consultation on its own only in a fix loop (the same problem has failed two fix attempts — proposed before the third) or a review loop (the same Plan/spec still has unresolved blockers after two review rounds, from any review source), and each proposal names the decision the consultation could change. Before sending, Claude asks via `AskUserQuestion` with a one-line summary (type | question | what Codex may read, including that it can read the whole project) and three options: consent this once / consent for this session / decline. A session grant skips the prompt for later proactive consultations in the same conversation and vanishes with the conversation context. A decline means Claude continues alone and does not re-propose on the same topic in the session unless there is material change (another failed attempt, new evidence). Review-loop consultations are second opinions that include the unresolved blockers from earlier rounds and ask whether each holds and whether the Plan should be simplified, split, or redirected. A consultation never counts toward or substitutes for any review/verification gate in the host workflow. See spec: user stories 5–13, 19, 50–51.

**Blocked by:** 02 — Consultation types and packaging.

**Status:** ready-for-agent

- [ ] First, determine how `AskUserQuestion` behaves inside a `claude -p` eval child; record in the ticket comments which consent cases can be tested directly and which must use `context.history_file` instead.
- [ ] No proposal outside fix loops and review loops; every proposal states the decision it could change.
- [ ] Consent prompt has exactly the three options and the one-line summary.
- [ ] No `codex` call happens before consent in any proactive case.
- [ ] Session grant suppresses later prompts in the same conversation only.
- [ ] A declined topic is not re-proposed without material change.
- [ ] Review-loop packaging includes the Plan and the unresolved blockers.
- [ ] Eval cases pass: fix-loop history (two failed attempts) → `tool_order` asserts `AskUserQuestion` before any `codex`; session grant in history → no prompt; decline in history → `codex` call count 0 for the same topic; review-loop history → recorded stdin contains the unresolved blockers.
