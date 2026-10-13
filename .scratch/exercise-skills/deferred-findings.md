# Deferred review findings (UI exercise)

User decision U14 (2026-10-13): finish implementing C2–C8 first. Each claim gets one code review after implementation; every finding — blocking security defects included — is recorded here and not fixed yet; outcome verification and Adversarial review wait. After C8, one fix pass covers everything below, then the final state gets code review, outcome verification and Adversarial review per claim. Nothing is merged to `main` or released before those passes or the user's accept-and-land decision.

Non-blocking items stay in the handoff follow-up records (`ui-exercise-c1-followups.md`, `ui-exercise-c2-followups.md`, …).

## C1 — accepted (accept-and-land at acc8887)

No open blocking finding. Residual risks per ticket 01 Comments (U13).

## C2 — unreviewed (code review call 3: CHANGES_REQUESTED at d7b699d)

- **R1 (blocking, I11 regression)** — `skills/ask/scripts/redact.py` ~154-157: when a label contains a secret word that is neither one of its parts nor its ending and is joined by `:`/`=`, the label is skipped instead of falling through to the shape test, so long hex/base64 values leak: `passwordhash: 5f4dcc3b5aa765d61d8327deb882cf99`, `api_keys: 0123456789abcdef0123`, `tokens=AbCdEf0123456789abcd`, `secretvalue=…`, `apitokens: …`, `X-Auth-Tokens: …`, `keys: …` (all redacted at 5fde8c1). Fix direction: fall through to the shape test instead of `continue`; update the docstring; add these to the redacted cases while `tokens: 3`, `Keyboard: Tab…`, "the token list is empty" stay unchanged.
- Code review call 3 non-blocking (record only): unpaired quote after a secret label hides the rest (accepted over-redaction; `monkey: banana`, `key=value` redacted); backslash-escaped quote ends a quoted value early; `token:: hunter2` leaves the value visible; camelCase flags with short/lowercase values not redacted (pre-existing); NBSP between label and value, `sk_live_…`, `AKIA…` not redacted (pre-existing, outside I11's list); timing test writes to stderr.
