# Deferred review findings (UI exercise)

User decision U14 (2026-10-13): finish implementing C2–C8 first. Each claim gets one code review after implementation; every finding — blocking security defects included — is recorded here and not fixed yet; outcome verification and Adversarial review wait. After C8, one fix pass covers everything below, then the final state gets code review, outcome verification and Adversarial review per claim. Nothing is merged to `main` or released before those passes or the user's accept-and-land decision.

Non-blocking items stay in the handoff follow-up records (`ui-exercise-c1-followups.md`, `ui-exercise-c2-followups.md`, …).

## Completion criteria (U15, 2026-10-13, refines U14)

The user applied the completion criteria set in the cc-feather project to this work. A claim is complete when (1) its acceptance as written in `plan.md` is met, (2) the new feature works and (3) existing behaviour is not broken. Only a finding that fails one of these blocks:

- (1) is judged only against what the acceptance states. An edge case beyond it, or one that needs the user's own environment to cooperate, is recorded or proposed as residual.
- (3) needs evidence: an existing test fails, or a reproduction shows that a written rule or a shipped spec's acceptance no longer holds. Inference alone does not block.

Everything else, including pre-existing issues and the new feature's own security defects outside the acceptance, is recorded for the next patch version and not fixed in this round. Suggestions that do not affect function are never adopted, even as one extra line in a file already being changed; contradictory or ambiguous wording that changes model behaviour counts as a functional problem. Something reproduced that this round would itself run on this machine is not run, only recorded. A Deviation (the goal cannot be met as written, or scope would change) still stops for the user. Claims whose acceptance is a security property (C1–C6, C8) get Adversarial review in this round, judged against that acceptance only; C7 gets none in this round. Claims with recorded security defects land through the user's accept-and-land, naming the known vulnerabilities and remaining risk in the release's `docs/setup-validation.md` entry and the handoff. From C3 on, deferred items go into one follow-up handoff record, `ui-exercise-followups.md`, security defects first.

Flow: C3–C8 and C7 each get one code review, findings recorded and dispositioned against (1)–(3); after C8 one fix pass covers only the blocking findings; then outcome verification and, for C1–C6 and C8, Adversarial review on the final state; then the user's accept-and-land.

## Review flow U17 (2026-10-14, replaces U14's single fix pass)

Relayed from the cc session as the cc-feather 0.25.0 candidate flow; the user confirmed it here ("套用，先補齊上游"). U15's criteria still classify findings.

1. Each claim: implement → code review → outcome verification; when both pass the claim is fixed. A downstream claim proceeds only after its upstream passed both; an upstream stop stops its dependants and asks the user.
2. A later claim fixes only its own problems and never reopens a passed claim; changing another claim's acceptance files (tests, expected values, fixtures) must be within the plan's scope, otherwise the reviewer blocks. Pre-existing problems of earlier claims go to the follow-ups, fixed by a later claim only when its acceptance needs it.
3. After all claims: every claim's primary acceptance is rerun at the final commit; an evidenced regression is fixed by the claim that caused it (through that claim's review), an unattributable one is reviewed as an independent change. Then Adversarial review for the Security-critical claims; its findings are only recorded as the next batch.
4. The user is asked once: land as is, or re-review which claims — listing BROKEN claims, claims fixed earlier and not re-reviewed at the final commit, and claims whose review or verification results come only from earlier sessions' records. That answer is the accept-and-land.

Catch-up order: C2 (R1 fix) → C3, C4 verification → C5 (P1, B1, B2 fix) → C6 (its own blocking items, then verification) → C8 → C7 → step 3 → step 4.

## C1 — accepted (accept-and-land at acc8887)

No open blocking finding. Residual risks per ticket 01 Comments (U13).

## C2 — fixed under U17 (code review APPROVED and outcome verification CONFIRMED at eb99654 = 4ac6ee8 on feat/ui-exercise; Adversarial review after all claims)

The R1 fix was made on branch fix/c2-r1 (from c947493) and cherry-picked onto feat/ui-exercise as 6b0780d..4ac6ee8; the code is identical to the reviewed and verified commits (e02d53b, 5a27501, 460de71, a1574c0, 9846de9, eb99654), only the records differ. Session 2026-10-14 calls:

- Code review call 1 (e02d53b): CHANGES_REQUESTED — a shape-matched run swallowed a glued secret-name label (`keys: /etc/ssl/private/server_key=hunter2`). Call 2 (5a27501): CHANGES_REQUESTED — the explicit path swallowed the label at a value's end (`token AbCd…_key=x_token AbCd…12`). Fixed by design in 460de71: every label judged on its own, spans unioned, linear time from O(n) tables. Call 3 (460de71): APPROVED; its N-c (the flags rule skipped a flag inside an earlier flag's value, `--token=a/--password hunter2`, against I11's flag clause) was classified blocking by main and fixed in a1574c0 (every rule's matches judged alone, then the sequential pipeline). Call 4 (a1574c0): CHANGES_REQUESTED — the sequential phase used views from the wider rules and redacted less than 460de71 on some inputs. Fixed in 9846de9: the sequential phase is 460de71's own pipeline, unioned with the per-match phase, so everything 460de71 redacted stays redacted by construction (frozen oracle `evals/_harness/redact_oracle_460de71.py`). Call 5 (9846de9): APPROVED.
- Outcome verification call 1 (9846de9): REFUTED on one point — a reply nested ≥ ~1000 levels made `replies.classify` raise RecursionError and `collect` exit 1 (ticket 02: "a malformed one as unstructured, neither raises"); pre-existing in replies.py; the user chose to fix it in C2: eb99654. Code review call 6 (eb99654): APPROVED. Verification call 2 (eb99654): CONFIRMED (6300-case depth sweep, the full offline suite module by module, redaction and argv/TEMP re-probes).
- Primary acceptance at eb99654 (main): 262 tests, the one failure the known flaky `test_the_child_inherits_only_its_stdio` (follow-up 37; C3/C4's guard, no C2 acceptance line), graders 933 passed.

Non-blocking items of these calls are in `ui-exercise-followups.md` (69–73 and onward).

- **R1 (blocking under U15: fails I11 as written — "long hex or base64 runs following `token`, `key`, `secret`, `password`" — and was redacted at 5fde8c1)** — `skills/ask/scripts/redact.py` ~154-157: when a label contains a secret word that is neither one of its parts nor its ending and is joined by `:`/`=`, the label is skipped instead of falling through to the shape test, so long hex/base64 values leak: `passwordhash: 5f4dcc3b5aa765d61d8327deb882cf99`, `api_keys: 0123456789abcdef0123`, `tokens=AbCdEf0123456789abcd`, `secretvalue=…`, `apitokens: …`, `X-Auth-Tokens: …`, `keys: …` (all redacted at 5fde8c1). Fix direction: fall through to the shape test instead of `continue`; update the docstring; add these to the redacted cases while `tokens: 3`, `Keyboard: Tab…`, "the token list is empty" stay unchanged.
- Code review call 3 non-blocking (record only; under U15 not fixed in this round): unpaired quote after a secret label hides the rest (accepted over-redaction; `monkey: banana`, `key=value` redacted); backslash-escaped quote ends a quoted value early; `token:: hunter2` leaves the value visible; camelCase flags with short/lowercase values not redacted (pre-existing); NBSP between label and value, `sk_live_…`, `AKIA…` not redacted (pre-existing, outside I11's list); timing test writes to stderr.

## C3 — unreviewed by verification/Adversarial (code review call 1: APPROVED at 5f44a3f)

No blocking finding under U15. U16 (downloads blocked through a run-owned profile seeded with `download_restrictions` = 3) landed in 5f44a3f; the live guard passes 154/154 on the real definition. Non-blocking items (security first) are in the handoff record `ui-exercise-followups.md`.

## C4 — unreviewed by verification/Adversarial (code review call 1: APPROVED at da54076)

No blocking finding under U15. Non-blocking items 20–36 (security first) are in `ui-exercise-followups.md`; item 30 (app-start must run as a background execution because a foreground call can outlast the Bash tool's 10-minute limit) is an input to C5 and C7.

## C5 — unreviewed (code review call 1: CHANGES_REQUESTED at cec87b8; phase B evals)

Evidence: `.scratch/exercise-skills/evidence/c5b-run-log.txt` (segments fd1e326 and 3520ab6); traces in `D:\tmp\ask-codex-c5b-traces\`. The first run of the exercise cases failed in the eval fake (bwrap's /dev/null masks), fixed in 3520ab6; the rerun on 3520ab6: ui-report 4/5, ui-report-zh 3/5, ui-no-fix 4/5, ui-no-claims 3/3, ui-reply-is-data 2/3, ui-headed-no-scope 3/3, `prepare` prepared 24/24. Regression (1ca7a0f vs fd1e326) met.

- **P1 (blocking under U15 (2): the exercise does not start in 6 of 24 runs; user decision 2026-10-14: record now, fix in the pass after C8)** — the model adds a shell `&` (sometimes `disown`) to the guard command it already runs with Bash `run_in_background`; the guard process dies with its shell, `wait-result` reports `missing` twice. 6/6 guard launches with `&` were `missing`, every launch without it succeeded. Three runs ended as the skill says (graders fail: ui-report FPLtld, ui-report-zh FHLVBW, ui-no-fix nanpx6); three restarted the guard against "`missing` twice in a row: … Report it and end" and passed every grader (ui-report TUWDrR, ui-headed-no-scope 1iHtDc and jMiHLi). Fix direction: `skills/ui/SKILL.md` long-operation wording (the command exactly as given, no `&`, `disown` or `nohup`, because `run_in_background` already backgrounds it), plus graders for a background command carrying `&`/`disown` and for a relaunch after `missing` twice; `not-done-note` in ui-reply-is-data made case-insensitive (it misjudged a correct `**Not done:**`, blm8z6). Rerun the six exercise cases after the fix.
- **B1 (code review call 1; blocking under U15 (1): I12 "with `stop_unconfirmed` it keeps everything" and I3 "the path comes only from the record" fail on this path)** — `skills/ui/SKILL.md` section 7 makes a `mktemp -d` scratch directory when the environment names none, and passes it to `prepare --base`, so the run directory lives under it; section 13 then removes that directory with `rm -rf` unconditionally, also after `stop_unconfirmed`, `failed`, `missing` or `lost`, when section 12 has just reported the run directory as the retained location ("never remove it yourself"). The target record and signals go, the target stays under the target root, and finish/stop/cleanup can no longer reach it (after a `missing` finish the app may still run). Triggered only without an environment scratch directory, as in the evals. Fix direction: remove the `mktemp` directory only when no result reported a retained location; otherwise remove the individual files with `rm -f` and report the scratch directory as part of the retained location; an eval with the fake's `stop_unconfirmed`/`missing` and a grader that no `rm -rf` targets a parent of the reported retained location.
- **B2 (code review call 1; blocking under U15 (2): wording that changes model behaviour)** — `skills/ui/SKILL.md` section 13 requires `## Claims` with "exactly the no-claims line" whenever there are no claims, and the early-ended report keeps the same shape, so a run where Codex never ran (guard failed, `missing`, `lost`, app-start failed) says "No claims: Codex reported nothing in the exercised scope" — seen in phase B (6WClCh, aI7N5Q, rA8t5l). Fix direction: a fixed EN/zh-TW line for "Codex did not complete a run; no claims were collected", the no-claims line only after a completed run with empty `claims`; an eval with `exercise_fake.guard: fail` grading the new line present and the no-claims line absent.
- **C2 R1 applies to C5 too**: C5's I11 (redaction module and collect side) rests on `redact.py`, unchanged in C5's range, so C5's I11 acceptance holds only after R1 is fixed.

Non-blocking items of code review call 1 (N1–N9) and the phase B observations are in `ui-exercise-followups.md` (items 38 onward).

## C6 — unverified (code review call 1: APPROVED at c947493; phase B evals; waits for C5 under U17)

Evidence: `.scratch/exercise-skills/evidence/c6b-run-log.txt` (segments c6 and reg-c6 at c947493, reg-c5 at 4ed42fe); traces in `D:\tmp\ask-codex-c6b-traces\`; cost USD 34.42. New cases: ui-repro-not-reproduced 2/3, ui-repro-boundary 2/3, ui-devdata-project-file 2/3, ui-devdata-explicit-zh 3/3, ui-external-deps 3/3, ui-devdata-report 2/3. Trace audit of the security cases: steps with curl, Remove-Item and an external URL were only written as `outside` and refused, nothing ran them; dev data was never used from a project file; no tool touched the app, a browser or evidence outside `consult.py`. Review N9 (the Data bullet's absolute wording) is not escalated: the dev-data cases pass.

- **E1 (blocking under U15 (3): an existing case regressed with evidence)** — ui-target-root-needed `no-exercise-ops` 3/3 at fd1e326 → 0/3 at c947493: all three runs (021Rww, 6ngnfm, do4xCj) ran `consult.py exercise-deps` before asking for the target root, against the order of work ("ask and stop"); do4xCj also wrote a resolve file into `<project>/.stub/` and deleted it ("Write nothing into the project"). Sections 1–4 did not change; the cause is to be found in C6's skill changes. Fix in C6 after C5 passes, rerun the case.
- **E2 (to confirm when C6 is fixed)** — ui-confirm-en 03JrAf left out DS-U8 and DS-A7 (2/3; C5 3/3), possibly from the new conditional `<DS-DEV>` slot; one run only, rerun with more runs.
- Regression (ticket 05's rule): second-opinion-with-stance and review-working-tree equal or better; targeted-check `concern-sent` 3/3 → 0/3 is the grader defect in follow-up 47 (a literal regex that misses `` `TimeoutError` `` in backticks; C5 phase B also failed it 2/3 at 1ca7a0f), not behaviour: `ask`'s SKILL.md is identical and C6 does not touch the consultation prompt. Recorded for the user's land question.
- Known issues counted: P1 5 of 31 guard launches; B1 33 `rm -rf` of the mktemp scratch, none removing a retained location; B2 2; bare `cd` 7.

Non-blocking items of code review call 1 (N1–N10) and the phase B observations are in `ui-exercise-followups.md`.
