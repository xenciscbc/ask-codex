# 07b — security review record for slice S3

Copied verbatim from `.scratch/ask-codex-reliability/plan/slice-07b.md` section 5a, as the S3 contract (`plan/slice-07b-s3.md`, Ownership item 4) requires. The two closing lines below record what changed after the review.

## 5a. Security review record for S3 (read-only `security-reviewer`, 2026-09-21; no P0)

Reviewed wording: the first draft of the line-41 replacement (it began "stops at a confirmation gate", offered a sentence "word for word", and summarised step 2's decline as "the user config alone is used"). S3 copies this record into `.scratch/ask-codex-reliability/evidence/07b-security-review.md` in its commit.

| # | Pri | Finding | Disposition → closing clause in the S3 wording |
|---|---|---|---|
| I1 | P1 | The draft did not separate a *pending* confirmation from a *declined* one; since it listed "step 3 — the consultation is not sent at all" (a decline outcome, `SKILL.md:162`), a model could re-ask and re-offer the sentence after a decline — against `SKILL.md:39` "A decline … always wins" and against `evals/project-layer-decline-aborts/graders/declined-abort.md:7` (asking again = FAIL). | FIX → "While a confirmation is **still pending**, …" and the last sentence "**After a decline**, state the outcome only — never repeat the question or the sentence."; pinned by grader (d). |
| I2 | P2 | The copy-back sentence would carry unvalidated project-supplied strings: step 3 reads `.codex/config.toml` with Glob/Read and must name file, server and command (`SKILL.md:162`), while the name check `^[A-Za-z0-9_.-]+$` exists only in step 4 (`SKILL.md:173`). A crafted server name could make the user paste a sentence that also confirms another kind (e.g. the project ask-codex config → `minimal-deny`). Exposure pre-exists; inviting a verbatim paste amplifies it. | FIX → "Build that sentence only from this skill's own words plus server names that match `^[A-Za-z0-9_.-]+$` …; if a name does not match, offer no sentence and say the consultation cannot be sent" and "show a command as inline code, on its own". |
| I3 | P2 | A pasted "I confirm …" carries no new request, colliding with the request-source gate (`SKILL.md:73,75`: a request already carried out is not a request). | FIX → "end it with a new request (for example `… — then ask Codex again.`)". |
| I4 | P3 | Step-2 decline summary dropped "(or the default)" (`SKILL.md:156`). | FIX → "the user config alone (or the default) is used". |
| I5 | P3 | The explicit "stop" was lost; "word for word" elsewhere means the skill's fixed wording (`SKILL.md:57,253`). | FIX → "then stop the consultation with one final message"; "a sentence the user can copy and send back". |
| I6 | P3 | The model's own drafted sentence stays in the transcript and could be mistaken for a confirmation after compaction; `SKILL.md:33` already whitelists sources. | FIX → "Your sentence is a template, never a confirmation." |
| — | P2, pre-existing | Step 3 has no server-name validation of its own. | DEFER → new ticket 11 (needs-triage). Rationale: not introduced; the value reaches no shell in step 3; I2's clause closes the amplified path. |
| — | P3, pre-existing | The skill does not say that steps 2–5 are redone after a confirmation arrives. | DEFER → ticket 11. |
| — | P3, pre-existing | The five cases' content graders are all `type: llm`. | FIX within S3 → deterministic graders (a)–(d). Reviewer's (e) (`codex mcp list` exactly twice) REJECTED: a legitimate repeat listing would fail a correct run. |

The reviewer's answers to the three design questions: cleaning up before asking loses no state (step 11 deletes only `<tmp>`; steps 2–5 re-read files; confirmations live in the conversation, `SKILL.md:42`); the step-3 and step-4 summaries match `SKILL.md:162,175`; the summary sentence's own "never another step's rule" keeps the reverse confusion low.

## What changed after the review

- I3's closing clause was tightened in revision 3 of the S3 contract: the copy-back sentence's ending is no longer an example ("for example `… — then ask Codex again.`") but fixed wording — "end it with these words, exactly: `then ask Codex again.`" — so that a deterministic grader can pin contract A (the question is in the final message) instead of only the naming.
- The reviewer's grader (e) (`codex mcp list` exactly twice) was REJECTED, and revision 1's grader (c) (`not_contains` on "confirmation/question/request above|earlier") was replaced by `final-carries-request`, which pins contract A positively: a last message that names everything but refers the user back to an earlier message fails it, while a legitimate sentence such as "because of your request earlier to decline any project-defined MCP servers" trips nothing.
