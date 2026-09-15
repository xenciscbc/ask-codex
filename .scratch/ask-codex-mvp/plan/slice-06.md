# Slice 06 — Follow-up consultation (revision 3, closing review)

## Readiness record

- Round 1 REVISE (4 blockers) → revision 2.
- Round 2 REVISE (1 blocker) — the second automatic REVISE; dispositioned below; revision 3 opens a new readiness epoch with exactly one closing fresh review; another REVISE pauses the slice for the user.

| Round-2 blocker | Disposition | Where |
|---|---|---|
| The re-check-a-revised-Plan follow-up was claimed but unproven, and clashed with ticket 05's "review-loop consultations are second opinions" | FIX (not narrowed — the ticket and spec story 63 require the re-check form): one step-0 type rule (follow-up when the conversation already holds an earlier consultation's claims about the same Plan or question; otherwise a review-loop consultation is a second opinion); the Proactive section's sentence updated to match; new case `followup-revised-plan`; `review-loop-blockers` added as a regression case | Outcome, Scope, cases 4–5 |

- Closing review REVISE (1 blocker: the shared core's rule 4 tells Codex to set `followup_status` to `null` on every claim, contradicting the follow-up framing — invisible to evals because the stub's reply is canned) → FIX in place: `prompts/consultation.md` joins the scope and rule 4 becomes conditional (`null` unless the Consultation type section says to report follow-up statuses); the offline test assembles the core with each framing file and checks that the follow-up prompt has no unconditional `null` instruction while initial-type prompts still require `null`. Slice paused for the user's decision (cap reached).

Ticket: `.scratch/ask-codex-mvp/issues/06-follow-up-consultation.md` (spec stories **63–65**; the ticket's "52–54" reference is a numbering slip; ADR-0002). Envelope, F-map, lessons, stops: `PLAN.md`. Blocked by 02 (resolved). Serial order: after 05. **Entry gate:** ticket 05's outcome verifier CONFIRMED and recorded. No dollar cap (user decision); 0 live Codex calls.

Revision 2 fixes round 1 (REVISE, 4 blockers): (1) who may start a follow-up now has one answer consistent with ticket 05's proactive rule; (2) the stdin graders bind each carried claim's id to its content and disposition through a fixed line format; (3) non-blocking new points are omitted, matching the `loadUser` grader; (4) each carried claim's status is shown in a fixed format checked by regex.

## Outcome

- **Who starts a follow-up.** A follow-up runs only (a) when the user asks for one (manual — no consent question), or (b) as a proactive consultation inside a fix loop or review loop under ticket 05's rules (consent first) — re-checking a revised Plan after review rounds is the review-loop case. Outside those, when a claim was marked investigate Claude may say in one line that a follow-up with Codex is possible, but never starts one on its own. (Consistent with the user's decision that proactive consultations happen only in fix and review loops.)
- **Type rule (step 0, one rule).** A consultation is a **follow-up** when the conversation already holds an earlier consultation's claims about the same question or Plan and the new consultation is about those claims (following up on claims marked investigate, or re-checking the revised Plan they reviewed). Otherwise the ticket-02 types apply — in particular a review-loop consultation with no earlier consultation on that Plan is a **second opinion** (ticket 05). The Proactive section's sentence becomes: "Review-loop consultations are second opinions — or follow-ups when an earlier consultation in this conversation already reviewed that Plan (carry its claims)."
- **Fresh run.** A follow-up is a new ephemeral `codex exec` exactly like any other consultation — never `resume` or `fork` (ADR-0002).
- **Carried claims.** The claims being followed up: for "follow up on what you marked investigate", every claim Claude marked investigate; for a re-check of a revised Plan, every claim of the earlier consultation on that Plan that was not rejected (the revised Plan text goes into the context too). Each goes into the prompt on its own line in the fixed form `<id> [<disposition>] <statement> — Claude: <reason>` (e.g. `C2 [investigate] renderProfile treats an empty object as 'user not found' — Claude: not yet confirmed that no other path renders it`).
- **Scope lock.** The follow-up framing tells Codex to verify only the carried claims, reuse their ids with `followup_status` = `resolved` / `unresolved` / `invalid`, and add a new claim only if it is blocking (`followup_status` = `new-blocking`).
- **Presentation.** Each carried claim on its own line in the fixed form `<id> [<status>] <statement> — Updated disposition: <adopt|reject|investigate> — <reason>`; a carried claim missing from the reply (or with a `null` status) is shown as `<id> [no status returned]`. New blocking claims appear under the fixed heading `New blocking claim from Codex`, each with a disposition. A new claim that is not `new-blocking` is **omitted** — neither presented nor mentioned.

## Non-goals

- Claude starting a follow-up on its own outside a fix or review loop.
- Resuming or forking a Codex session.
- Any change to ticket 05's triggers.

## Scope

- `prompts/consultation.md` rule 4: `followup_status` = `null` **unless the Consultation type section above tells you to report follow-up statuses** (the only change to the shared core; rules 1–3 unchanged).
- `prompts/framing/follow-up.md`: marker `Consultation type: follow-up.`, the scope lock, the `followup_status` rules, the new-blocking exception, and the carried-claim line format.
- `skills/ask/SKILL.md`: step 0 gets the type rule (type **follow-up**; who may start it, per Outcome) and the Proactive section's review-loop sentence is updated to the same rule; step 7 writes the carried claims into `{{context}}` in the fixed line form; step 10 gains the follow-up presentation (fixed per-claim line, missing-status line, `New blocking claim from Codex` heading, omission of non-blocking new claims).
- Cases, generator, offline grader test, ticket 06 comments. No stub change (custom `exec.reply` carries any `followup_status`; an argv `resume`/`fork` is already a stub violation).

## Eval cases (runs 1, sonnet, `--allow-tools Bash Write`)

History fixture (hand-written, ticket-02 format): the user's `/ask-codex:ask` question about fetchUser and the assistant's presented result with C1 (adopt), C2 (investigate: "renderProfile treats an empty object as 'user not found'"), C3 (reject), each with a reason. Workspace: the ticket-01 scaffold. Prompt for both: `/ask-codex:ask Follow up with Codex on the claim you marked investigate.` (manual).

Standard exec set: skill-fired, one `codex exec`, exec-sentinel, no-violations, no-bare-cd, temp-cleanup.

| # | Case | Stub reply | Graders beyond the standard set |
|---|---|---|---|
| 1 | `followup-carries-claims` | C2 `resolved` | argv `resume\|fork` not_contains (`.stub/exec-argv.json`); stdin: `Consultation type: follow-up\.`, `C2 \[investigate\][^\n]*renderProfile`, `C2 \[investigate\][^\n]*— Claude:`; stdin not_contains `C1 \[adopt\]` and `C3 \[reject\]` (only the investigate claim is carried); last message: `C2 \[resolved\]`, `C2[^\n]*Updated disposition`; llm: C2's status and updated disposition shown with a reason |
| 2 | `followup-new-blocking` | C2 `unresolved`; C4 `new-blocking` ("fetchUser also swallows AbortError…"); C5 `null` ("Consider renaming fetchUser to loadUser") | argv `resume\|fork` not_contains; stdin marker + the two C2 line regexes; last message: `C2 \[unresolved\]`, `C2[^\n]*Updated disposition`, `New blocking claim from Codex`, `AbortError`, not_contains `loadUser`; llm: C4 flagged separately with a disposition, C5 absent |
| 3 | `manual-with-question` (01 regression) | default | as in 01 |
| 4 | `followup-revised-plan` | history: Plan `P-BETA` ("serve the last cached user when the API times out"); an earlier presented consultation on P-BETA with `C1 [investigate]` "P-BETA has no fallback when the cache is empty" and `C2 [adopt]` "P-BETA hides timeouts from monitoring"; the user's revision "P-BETA v2: fall back to a placeholder user and log each timeout". Prompt `/ask-codex:ask Re-check the revised plan with Codex.`; stub reply C1 `resolved`, C2 `resolved` | argv `resume\|fork` not_contains; stdin: `Consultation type: follow-up\.`, `C1 \[investigate\][^\n]*fallback`, `C2 \[adopt\][^\n]*monitoring`, `P-BETA v2`; stdin not_contains `Consultation type: second opinion\.`; last message `C1 \[resolved\]`, `C1[^\n]*Updated disposition` |
| 5 | `review-loop-blockers` (ticket-05 regression; no earlier consultation on its Plan) | as in ticket 05 | as in ticket 05 — still `Consultation type: second opinion.` |

The proactive form of a follow-up (inside a fix or review loop) reuses ticket 05's consent machinery, which ticket 05's cases prove; case 4 proves the re-check packaging itself (asked manually), and case 5 proves that a review loop without an earlier consultation stays a second opinion.

**Offline test (before any paid run)** — `evals/_harness/ticket06-graders.test.mjs`:
- stdin: the shared core + follow-up framing **without** carried claims fails every C2 line regex (the core mentions "C1, C2" and the framing may mention "investigate"); a carried line without `— Claude:` fails that regex; a correct carried block passes; a block also carrying `C1 [adopt]` fails the not_contains grader.
- last message: `C2 [resolved]` passes case 1 and `C2 [unresolved]` does **not** pass case 1's `C2 \[resolved\]`; a presentation without C2's status fails; a reply mentioning `loadUser` anywhere fails case 2's grader; a reply without the heading fails it.
- argv: an argv containing `resume` fails `no-resume`.
- prompt assembly: the core template filled with `prompts/framing/follow-up.md` contains no unconditional "`followup_status` = `null`" instruction and does contain the follow-up status rules; the core filled with each of the four initial framings still requires `null`; the check fails on the current (unconditional) rule-4 wording.

## Red plan

Cases 1 and 2 on the ticket-05 skill: expected failures — no follow-up marker and no fixed carried lines in stdin; no fixed status lines, no heading, likely C5 presented.

## Acceptance

1. Offline checks (incl. `ticket06-graders.test.mjs`), `claude plugin validate`.
2. Cases 1–5 pass.
3. The follow-up framing file exists with its marker and the line format; SKILL.md has the follow-up recognition (with the who-starts rule), packaging and presentation.
4. Fresh verifier CONFIRMED on the ticket-06 criteria (with the who-starts narrowing recorded in ticket 06 Comments).
5. Ticket 06 resolved in one commit (rollback: revert it).
