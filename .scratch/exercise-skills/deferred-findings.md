# Deferred review findings (UI exercise)

User decision U14 (2026-10-13): finish implementing C2–C8 first. Each claim gets one code review after implementation; every finding — blocking security defects included — is recorded here and not fixed yet; outcome verification and Adversarial review wait. After C8, one fix pass covers everything below, then the final state gets code review, outcome verification and Adversarial review per claim. Nothing is merged to `main` or released before those passes or the user's accept-and-land decision.

Non-blocking items stay in the handoff follow-up records (`ui-exercise-c1-followups.md`, `ui-exercise-c2-followups.md`, …).

## Completion criteria (U15, 2026-10-13, refines U14)

The user applied the completion criteria set in the cc-feather project to this work. A claim is complete when (1) its acceptance as written in `plan.md` is met, (2) the new feature works and (3) existing behaviour is not broken. Only a finding that fails one of these blocks:

- (1) is judged only against what the acceptance states. An edge case beyond it, or one that needs the user's own environment to cooperate, is recorded or proposed as residual.
- (3) needs evidence: an existing test fails, or a reproduction shows that a written rule or a shipped spec's acceptance no longer holds. Inference alone does not block.

Everything else, including pre-existing issues and the new feature's own security defects outside the acceptance, is recorded for the next patch version and not fixed in this round. Suggestions that do not affect function are never adopted, even as one extra line in a file already being changed; contradictory or ambiguous wording that changes model behaviour counts as a functional problem. Something reproduced that this round would itself run on this machine is not run, only recorded. A Deviation (the goal cannot be met as written, or scope would change) still stops for the user. Claims whose acceptance is a security property (C1–C6, C8) get Adversarial review in this round, judged against that acceptance only; C7 gets none in this round. Claims with recorded security defects land through the user's accept-and-land, naming the known vulnerabilities and remaining risk in the release's `docs/setup-validation.md` entry and the handoff. From C3 on, deferred items go into one follow-up handoff record, `ui-exercise-followups.md`, security defects first.

Flow: C3–C8 and C7 each get one code review, findings recorded and dispositioned against (1)–(3); after C8 one fix pass covers only the blocking findings; then outcome verification and, for C1–C6 and C8, Adversarial review on the final state; then the user's accept-and-land.

## C1 — accepted (accept-and-land at acc8887)

No open blocking finding. Residual risks per ticket 01 Comments (U13).

## C2 — unreviewed (code review call 3: CHANGES_REQUESTED at d7b699d)

- **R1 (blocking under U15: fails I11 as written — "long hex or base64 runs following `token`, `key`, `secret`, `password`" — and was redacted at 5fde8c1)** — `skills/ask/scripts/redact.py` ~154-157: when a label contains a secret word that is neither one of its parts nor its ending and is joined by `:`/`=`, the label is skipped instead of falling through to the shape test, so long hex/base64 values leak: `passwordhash: 5f4dcc3b5aa765d61d8327deb882cf99`, `api_keys: 0123456789abcdef0123`, `tokens=AbCdEf0123456789abcd`, `secretvalue=…`, `apitokens: …`, `X-Auth-Tokens: …`, `keys: …` (all redacted at 5fde8c1). Fix direction: fall through to the shape test instead of `continue`; update the docstring; add these to the redacted cases while `tokens: 3`, `Keyboard: Tab…`, "the token list is empty" stay unchanged.
- Code review call 3 non-blocking (record only; under U15 not fixed in this round): unpaired quote after a secret label hides the rest (accepted over-redaction; `monkey: banana`, `key=value` redacted); backslash-escaped quote ends a quoted value early; `token:: hunter2` leaves the value visible; camelCase flags with short/lowercase values not redacted (pre-existing); NBSP between label and value, `sk_live_…`, `AKIA…` not redacted (pre-existing, outside I11's list); timing test writes to stderr.

## C3 — unreviewed by verification/Adversarial (code review call 1: APPROVED at 5f44a3f)

No blocking finding under U15. U16 (downloads blocked through a run-owned profile seeded with `download_restrictions` = 3) landed in 5f44a3f; the live guard passes 154/154 on the real definition. Non-blocking items (security first) are in the handoff record `ui-exercise-followups.md`.
