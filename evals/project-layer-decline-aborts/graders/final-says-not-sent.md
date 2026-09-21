---
type: regex
pattern: '(?:[Cc]onsultation|[Nn]othing|[Nn]o consultation)[^.\n]{0,80}(?:not sent|wasn(?:''|’)t sent|not been sent|never sent)|[Nn]othing[^.\n]{0,40}was sent|[Dd]id not send|[Dd]idn(?:''|’)t send|[Nn]ot sent'
---

After a decline the outcome belongs in the FINAL message (`skills/ask/SKILL.md:39`, `:162`): this grader pins that the last message says the consultation was not sent at all, because in a non-interactive session the user sees only that message — the pass-2 failure was a final message that carried the model's own analysis alone and left the abort in an earlier one (defect F-B on the decline path); offline checks in `evals/_harness/ticket-r07b-s3-graders.test.mjs`.
