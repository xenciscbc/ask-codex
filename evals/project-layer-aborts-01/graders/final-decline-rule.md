---
type: regex
pattern: 'If you decline, the consultation is not sent at all\.'
---

The final message carries this step's own decline line, word for word (`skills/ask/SKILL.md:41`): until fix pass 6 the decline rule was free wording and some runs stated another step's rule — a step-2 stop saying the consultation would not be sent at all, a step-4 stop offering to stop entirely — so every step's line is fixed wording now (step 2 `:156`, step 3 `:162`, step 4 `:175`) and this grader pins the one that belongs to this case; the wrong ones are caught by `no-wrong-decline-rule` (steps 2 and 4) and by `no-proceed-promise` (step 3). Offline checks: `evals/_harness/ticket-r07b-s3-graders.test.mjs`.
