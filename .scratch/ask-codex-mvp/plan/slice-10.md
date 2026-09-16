# Slice 10 — READMEs (English and Traditional Chinese) — revision 2

Ticket: `.scratch/ask-codex-mvp/issues/10-readmes.md` (spec user stories 83–85). Envelope, F-map rows **F1-claims** (P1 — the narrowed claim verbatim on every surface, README included) and **F10** (tested Codex CLI version stated), known-limitations paragraph, stops: `PLAN.md`. Blocked by 09 (live acceptance — its verifier must land first, because the README reports what the live runs showed) and 11 (resolved). Risk trigger: the README *is* the product's security statement, so plan-verifier before, fresh verifier after. **No Codex calls, no evals, no skill changes.**

Revision 2 fixes round 1 (REVISE, 5 blockers): the claim checker is a named deliverable that reads the sentence from the shipped skill instead of hard-coding it; proactive consultation and its consent block are back in Usage, with the limitation reworded from "paused" to "unreliable"; story 83's non-delivery must be written into ticket 10 and PLAN's deferred list; one single risk/limitation list governs acceptance; and the ~25k-token figure is labelled an estimate with an allowed source.

## Decision taken before drafting (user, 2026-09-16)

The GitHub remote holds only `refs/heads/main` at `47b2e17`; every commit of this work is on the unpushed local branch `design/ask-codex-mvp`. Asked how to write the installation section, the user chose **"document only the tested local install"**. So the README documents the `--plugin-dir` path that live acceptance actually used, and states plainly that installing from GitHub is not available until the branch is published. Spec story 83 (standard plugin flow from GitHub) is therefore **deferred, not delivered** — acceptance 4 below forces that to be recorded where a reader will find it.

## Outcome

`README.md` (English) and `README.zh-TW.md` (Traditional Chinese) at the repository root, cross-linked in their first lines, carrying the same content, so a new user can decide whether to use ask-codex and start using it correctly.

## Deliverables

1. `README.md`, `README.zh-TW.md`.
2. `.scratch/ask-codex-mvp/plan/readme-claim-check.mjs` — the deterministic checker for acceptance 2. It **reads the expected sentence from `skills/ask/SKILL.md`** (the blockquote that opens the skill, the shipped copy of the narrowed claim) and must not contain that sentence as a literal of its own. It fails with a non-zero exit when the sentence is missing from either README, when it is broken across lines, or when markdown markup has been inserted inside it.
3. The record edits acceptance 4 requires (ticket 10 body, ticket 10 Comments, PLAN deferred list).

## Scope — what the READMEs say

1. **Purpose** — consultation, not delegation: Codex gives opinions, Claude judges every claim and owns every change.
2. **Installation (tested only)** — `claude --plugin-dir <path to this repo>` for an interactive session and the same flag for `claude -p`, exactly as used in ticket 09; one line stating that installing from GitHub/marketplace is not available until the branch is published.
3. **Prerequisites** — Codex CLI installed and logged in (`! codex login` when it is not), and the tested version.
4. **Usage** —
   - `/ask-codex:ask`, and a verbal request in conversation;
   - the consultation types (second opinion, diagnosis, targeted check, technical question, follow-up);
   - **proactive consultation**: when the skill offers one by itself (a fix loop or a review loop that is not converging), the three-option consent block (consent this once / consent for this session / decline), what a session grant and a decline mean and how long they last, and that **no `codex` command runs before consent** — including the MCP listings;
   - model aliases and the effort rules, and override scope (this consultation only / rest of the session);
   - parallel consultation (at most two different models) and follow-up consultation (a fresh Codex session, never `resume`);
   - the timeout behaviour: the check interval, the alive notice, the stall question and what stopping does;
   - MCP policy with the ask-codex config files and `/ask-codex:setup`.
5. **Known risks** — the narrowed claim verbatim; Codex's shell can read anything the user's account can read, with scope limited only by instruction; allowed MCP servers run outside the sandbox and may write or execute; **an estimated** ~25k tokens of base input cost per call (labelled as an estimate, source `PLAN.md`; no run measured it).
6. **Known limitations — exactly this list, and acceptance 5 is judged against it:**
   a. A workspace on a drive where the Codex Windows sandbox cannot run (`R:`, a RAM disk: `codex exec -C R:\…` fails with "os error 1"). Source: `PLAN.md` known-limitations paragraph.
   b. Projects trusted persistently in the user's Codex config are covered only by the project-layer fail-safe, not live-tested. Source: same paragraph.
   c. **Proactive consultation is unreliable**: improvement is paused (ticket 05), and in a live fix loop with the plugin loaded no consultation was proposed (ticket 09, I1). The path exists and is documented in Usage; what is unreliable is whether it offers. Never write that it is disabled or absent.
   d. **Stopping a headless consultation currently leaves the Codex process running** and still spending quota; an interactive stop ends it cleanly (ticket 12, from ticket 09's A8/A8b and I3).
   e. **An external program can rewrite the `model` line** in the user's Codex config that the skill reads for its default, so two consultations minutes apart can use different models with no user action (ticket 09, the second guarded-file event).
   **Explicitly excluded from the README, each with its reason:** language drift into another language and markdown around the fixed wordings — both are `/code-review` items on Claude's own output, not user-facing contract, and are recorded in ticket 09; the interactive-vs-headless temp-base difference — an implementation detail with no user-visible consequence.

Terminology follows `CONTEXT.md`. Neither file may use these `_Avoid_` terms in the sense the glossary forbids: 委派 / delegation / rescue for a consultation; query / ask / request as the English noun for 諮詢; 自動諮詢 / auto consultation for proactive; 永久授權 / 全域設定 for a session grant; A+ for minimal-deny; 多模型審查 / multi-model review for parallel; finding / issue for a claim; review / code review for targeted check; resume / continue thread for follow-up; 固定對照表 for model aliases.

## Non-goals

No push, publish or merge; no marketplace test; no change to any file under `skills/`, `evals/`, `docs/adr/` or `.claude-plugin/`; no claim about behaviour that ticket 09 did not record.

## Acceptance

1. Both files exist at the repository root and link to each other in their first lines.
2. **The narrowed claim appears verbatim** — `node .scratch/ask-codex-mvp/plan/readme-claim-check.mjs` exits 0; it reads the expected sentence from `skills/ask/SKILL.md` rather than carrying its own copy, requires the sentence to appear on a single unbroken line with no markup inside it in both READMEs, and exits non-zero when any character of it is changed or it is wrapped. Proven both ways: the passing run and a deliberately mutated copy that fails, both recorded in ticket 10's Comments.
3. The installation section documents only what ticket 09 ran, with the exact flag and no untested step, plus the one-line note about GitHub install.
4. **Story 83's non-delivery is recorded where readers look:** ticket 10's body describes the `--plugin-dir` installation instead of the GitHub flow, ticket 10's Comments carry one line saying spec story 83 is not delivered because the branch is unpushed, and `PLAN.md`'s deferred list carries the same as a numbered item. `grep -n "GitHub" .scratch/ask-codex-mvp/issues/10-readmes.md` returns only sentences about it being unavailable.
5. Every item in Scope 5 and Scope 6 appears in both READMEs and is traceable to its stated source — a recorded result in ticket 09, 05, 11 or 12, **or** an estimate in `PLAN.md`/`spec.md` when the text labels it as an estimate. Nothing outside that list is asserted as a risk or limitation.
6. Terminology: none of the `_Avoid_` terms listed above appears in either file in the forbidden sense.
7. `claude plugin validate .` passes, and `git status --short` shows no change under `skills/`, `evals/`, `docs/adr/` or `.claude-plugin/`.
8. Fresh verifier CONFIRMED against criteria 1–7. Ticket 10's own checklist is satisfied by these criteria; where its item 4 says "any deviations recorded in ticket 09 are reflected", the governing list is Scope 6 with its stated exclusions.

## Stops

1. The narrowed claim cannot be stated verbatim in both files → stop and report; it is a P1 row.
2. A statement cannot be traced to a source allowed by acceptance 5 → remove it rather than soften it, and record why.
3. Ticket 09's verifier returns REFUTED on something the README repeats → pause this slice until that is settled.

## Follow-up dependency

Ticket 12's own checklist requires the README's timeout section to state the guarantee that holds after its fix. So limitation (d) is expected to be rewritten when ticket 12 lands; that later edit is planned work, not an undeclared change.

## Budget

Claude only; no Codex calls (program: 14 of 16 used in ticket 09, 19 of 25 overall). One commit.

## Rollback

`git revert` the single commit; the two READMEs are additive, and the record edits in acceptance 4 revert with it.
