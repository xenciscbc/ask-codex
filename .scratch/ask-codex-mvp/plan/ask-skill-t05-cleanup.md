Structural fix for skipped cleanup (seen once in ticket 07, once in ticket 05 review-loop-blockers):
move the removal of the run directory to right after the reply has been read, so presenting the
result never happens before cleanup.

(Step 9, append after the two bullets:)
Then **clean up now** — run step 11 immediately, before you present anything. Everything you need
(the reply, the MCP statement, model and effort, timer notes) is already in your context.

(Step 10, replace the closing reminder "Before you send this answer, run step 11 (cleanup) — it is never optional." with:)
Cleanup already ran at the end of step 9; if for any reason it did not, run step 11 now, before you answer.

(Step 11, first sentence becomes:)
Run this right after step 9 (and on every early stop after step 1) — never leave it for after your final answer.
