Consultation type: follow-up.

This is a follow-up on claims from an earlier consultation. Verify only the carried claims listed in the context below — do not review anything else. Report follow-up statuses as follows (this replaces the `null` rule for `followup_status` in the rules below):

- For each carried claim, reuse its id and set `followup_status` to `resolved` (the question it raised is settled — confirmed or no longer applies), `unresolved` (it still holds and is not settled), or `invalid` (the claim was wrong).
- You may add a new claim only if it is blocking — something that would change the decision. Give it a new id and `followup_status` = `new-blocking`. Do not add non-blocking new points.

Carried claims appear one per line as `<id> [<Claude's disposition>] <statement> — Claude: <reason>`.
