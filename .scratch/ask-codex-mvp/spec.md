# Spec: ask-codex MVP

Status: ready-for-agent

Vocabulary follows `CONTEXT.md` (English equivalents). Decisions respect ADR-0001 (call `codex exec` directly) and ADR-0002 (fresh session for follow-up consultations).

## Problem Statement

When Claude is working in Claude Code and gets stuck — the same bug survives repeated fix attempts, or the same Plan/spec keeps bouncing through review rounds without converging — there is no lightweight way for Claude to get an independent opinion from a different model family and then judge that opinion itself.

The official Codex plugin for Claude Code does not cover this:

- `/codex:review` and `/codex:adversarial-review` are user-only commands (model invocation disabled) and must be relayed verbatim; Claude may not weigh in.
- `/codex:rescue` is delegation: it defaults to a write-capable Codex run and forbids Claude-side analysis.

The user wants a consultation, not a delegation: Codex stays read-only, returns opinions, and Claude decides — claim by claim — what to adopt. The user also wants control over when this costs money: Claude may propose a consultation, but only the user can approve it, and the user must be able to pick models and reasoning effort using short aliases.

## Solution

A Claude Code plugin named `ask-codex` providing one skill, `ask`, invoked as `/ask-codex:ask` or by natural-language requests such as "ask codex about this".

- **Manual consultation**: the user invokes the skill (slash command or an explicit verbal request). Invoking it is consent. With no question given, Claude infers the question from the conversation.
- **Proactive consultation**: Claude proposes a consultation only in a fix loop or a review loop, and asks the user via `AskUserQuestion` for one-time consent, a session grant, or a decline.
- Claude infers the consultation type (second opinion, diagnosis, targeted check, technical question) from context, packages the question with-stance or blind accordingly, and runs Codex non-interactively, read-only, ephemeral, with a JSON Schema–constrained reply, in the background.
- Codex returns structured claims. Claude presents each claim with its own disposition (adopt / reject / investigate) and reasoning.
- **Parallel consultation**: the user can name two different models; Claude runs both independently and presents consensus, solo claims, and divergences.
- **Follow-up consultation**: always a fresh Codex session carrying prior claims and dispositions, scoped to verifying them.
- Long runs are monitored; after 30 minutes Claude checks liveness and only asks the user whether to keep waiting when liveness is not confirmed.

## User Stories

### Invocation and consent

1. As a user, I want to invoke `/ask-codex:ask <question>`, so that Claude consults Codex about exactly what I asked.
2. As a user, I want to invoke `/ask-codex:ask` with no question, so that Claude infers what to ask from the current conversation and sends it without further prompting.
3. As a user, when Claude cannot infer any sensible question from an empty invocation, I want Claude to ask me what to consult about, so that no meaningless consultation is sent.
4. As a user, I want saying "ask codex" or "get Codex's opinion" in plain language to count as a manual consultation, so that I don't have to remember the slash command and am not asked for consent I just gave.
5. As a user, I want Claude to propose a proactive consultation when the same problem has failed two fix attempts, so that a third blind attempt is replaced by an independent diagnosis.
6. As a user, I want Claude to propose a proactive consultation when the same Plan or spec still has unresolved blockers after two review rounds (from any review source), so that the review loop gets an outside second opinion.
7. As a user, I want Claude never to propose a proactive consultation outside fix loops and review loops, so that Codex usage stays rare and deliberate.
8. As a user, I want every proactive proposal to state which decision the consultation could change, so that I can judge whether it is worth the cost.
9. As a user, I want the consent prompt to summarize the consultation in one line (type, question, what Codex may read — including that Codex can read the whole project), so that I know what will be sent to OpenAI.
10. As a user, I want to choose "consent this once", so that only this proactive consultation runs.
11. As a user, I want to choose "consent for this session", so that later proactive consultations in this session run without asking me again.
12. As a user, I want to choose "decline", so that Claude continues on its own and does not re-propose a consultation on the same topic in this session unless the situation materially changes.
13. As a user, I want a session grant to disappear when the conversation context is lost, so that consent never silently outlives the conversation I gave it in.

### Consultation types and packaging

14. As a user, I want Claude to decide the consultation type from context for both manual and proactive consultations, so that I never have to specify it.
15. As Claude, when asking for a second opinion, I want to include the Plan or design decision and explicitly ask Codex to verify independently and challenge it, so that the thing under review is visible.
16. As Claude, when asking for a targeted check, I want to include the implementation or diff plus my specific concern, so that Codex focuses on the actual doubt rather than doing a general review.
17. As Claude, when asking for a diagnosis, I want to send symptoms, evidence, and every failed attempt with its result, but not my current root-cause hypothesis, so that Codex's view is not anchored by mine and does not repeat failed fixes.
18. As Claude, when asking a technical question, I want to send the question and relevant evidence blind, so that the answer is independent.
19. As Claude, in a review loop, I want to include the Plan plus the unresolved blockers from earlier rounds, and ask Codex whether each blocker holds and whether the Plan should be simplified, split, or redirected, so that the consultation targets the actual deadlock.
20. As Claude, I want to instruct Codex to stay within the project directory and any paths I explicitly list, so that the read scope is limited even though the sandbox permits whole-disk reads.
21. As Claude, I want prompts to Codex written in English, so that they are token-efficient and consistent with the skill.

### Models and effort

22. As a user, I want to name models with short aliases such as `sol`, `5.6 sol`, or `astra`, so that I don't have to type full model slugs.
23. As a user, I want aliases resolved against the models Codex currently lists (not a hardcoded table), so that new models work without a skill update.
24. As a user, when an alias is ambiguous (e.g. `5.6` matches several models), I want to pick from the candidates, so that Claude never guesses.
25. As a user, when an alias matches nothing, I want an error listing the currently available models, so that I can correct it.
26. As a user, when I don't name a model, I want the model configured in my Codex settings to be used, so that my default choice is respected.
27. As a user, I want consultation effort never to go below `medium`, so that a consultation is never run at a uselessly low reasoning level.
28. As a user, I want default effort `high` for `gpt-5.6-sol` and `medium` for `gpt-6-astra`, and for any other model the higher of its own default and `medium`, so that each model runs at a sensible level without me specifying it.
29. As a user, I want the effort in my Codex config to be ignored for consultations, so that a low default there can't drag consultations below the floor.
30. As a user, when I explicitly request `low`, I want it raised to `medium` with a note, so that the floor is a hard rule.
31. As a user, when I request an effort the model doesn't support, I want the model's highest supported level used with a note, so that the consultation still runs.
32. As a user, I want `ultra` used only when I explicitly ask for it, so that Codex's costly automatic delegation never happens by default.
33. As a user, when I specify a model or effort that differs from the current session setting, I want to be asked whether it applies to this consultation only or to the rest of the session, so that my override lasts exactly as long as I intend.
34. As a user, when I re-specify the setting already in force for the session, I want no prompt, so that I'm not asked redundant questions.
35. As a user, I want proactive consultations to use the Codex default model (or my session override), never a model Claude picks for difficulty, so that cost decisions stay mine.

### Parallel consultation

36. As a user, I want to name two different models in one manual consultation (e.g. `astra:high, sol`), so that I get two independent opinions.
37. As a user, I want each model in a parallel consultation to take its own optional effort, with the effort rules applied per model, so that I can tune each one.
38. As a user, I want parallel consultation limited to two distinct models, so that cost stays bounded.
39. As a user, I want Claude to refuse more than two models or the same model twice, with a clear message, so that the limit is predictable.
40. As a user, I want each model to run without seeing the other's output, so that the opinions are genuinely independent.
41. As a user, I want the combined result grouped into consensus, solo claims, and divergences, each tagged with its source model and Claude's disposition, so that agreement and disagreement are obvious.
42. As a user, for every divergence I want Claude to state which side it adopts and why, so that I can audit the judgment.
43. As a user, when one model fails, I want the successful model's opinion presented normally with a note naming the failed model and the reason, so that one failure doesn't waste the other result.
44. As a user, I want parallel consultation to be manual-only (unless my session override specifies two models), so that Claude never doubles the cost on its own.

### Results and dispositions

45. As Claude, I want Codex's reply constrained by a JSON Schema, so that I can evaluate claims one by one.
46. As Claude, I want each claim to state whether it is a fact or an inference, its confidence, and evidence locations where possible, so that I can weigh it correctly.
47. As a user, I want every claim listed with Claude's disposition (adopt / reject / investigate) and a reason, so that I see both what Codex said and what Claude concluded.
48. As a user, I want the presentation in the language of my conversation while code, paths, and quotes stay verbatim, so that it reads naturally for me.
49. As a user, I want Claude to never apply Codex's suggestions automatically just because Codex made them, so that decisions remain with Claude and me.
50. As a user, I want a consultation to never count as, or substitute for, a formal review or verification step in my workflow, so that my existing review gates keep their meaning.
51. As a user, when Claude materially revises a Plan based on a consultation, I want that treated as a material revision under whatever review rules apply, so that consultation can't bypass review.

### Follow-up consultation

52. As Claude, when a claim is marked investigate or I need to re-check a revised Plan, I want to start a follow-up consultation in a fresh Codex session carrying the prior claims and my dispositions, so that the follow-up is not anchored by Codex's earlier context (ADR-0002).
53. As Claude, I want a follow-up consultation scoped to verifying the carried claims — each resolved, unresolved, or invalid — so that the review loop converges instead of producing new points each round.
54. As Claude, I want Codex to be able to raise a new claim in a follow-up only if it is blocking, and marked as new, so that critical problems are still surfaced without scope creep.

### Execution, monitoring, and cleanup

55. As a user, I want Codex to run read-only, so that a consultation can never modify my files.
56. As a user, I want Codex runs to be ephemeral, so that consultations don't clutter my Codex history or keep what Codex read on disk.
57. As a user, I want consultations to run in the background, so that Claude can continue unrelated work and isn't bound by foreground command time limits.
58. As Claude, I want to wait for the consultation result before doing work that depends on it, so that I don't act on half the picture.
59. As a user, I want Claude to check a running consultation every 30 minutes, so that long runs are neither abandoned nor waited on blindly.
60. As a user, when the check confirms Codex is still running (background task alive and a new progress event within the last 5 minutes), I want Claude to keep waiting automatically and tell me in one line, so that I'm not interrupted by healthy long runs.
61. As a user, when liveness is not confirmed, I want to be asked "wait another 30 minutes" or "stop this consultation", with elapsed time and the last progress event and its age, so that I can decide with real information.
62. As a user, I want "stop this consultation" recommended when the run looks stalled and "wait another 30 minutes" recommended when it doesn't, so that the default choice matches the evidence.
63. As a user, I want stopping to end the Codex run and be handled like any other failure, so that Claude simply continues its work.
64. As a user, I want a parallel consultation to share one timer, reporting which model is done and asking only about the ones still running, so that I'm asked once and never shown half a result that later changes.
65. As a user, I want a consultation's temporary files placed in Claude's session scratchpad when one is listed, otherwise in the system temp directory, so that files stay isolated per session and avoid permission prompts where possible.
66. As a user, I want all temporary files deleted after the result is presented — including after failures and stops — so that nothing Codex read lingers on disk.
67. As a tester, I want an `EVAL_ASK_CODEX_TIMEOUT_MINUTES` override for the check interval, so that the timeout path is testable without waiting 30 minutes.

### Failure handling

68. As a user, when Codex is missing, not logged in, times out, or returns output that violates the schema, I want a short explanation and Claude to continue its own work without retrying, so that a failed consultation costs no more than necessary.
69. As a user, when Codex is not logged in, I want to be told to run `! codex login`, so that I know the fix.
70. As a user, when Codex returns readable but unstructured output, I want it passed to Claude labeled as unstructured and still judged, so that usable content isn't thrown away.
71. As a user, I want Claude never to fabricate a Codex opinion when Codex failed, so that everything attributed to Codex really came from Codex.

### Installation and docs

72. As a user, I want to install ask-codex as a Claude Code plugin from its GitHub repository, so that installation is a standard plugin flow.
73. As a user, I want an English `README.md` and a Traditional Chinese `README.zh-TW.md`, each briefly covering purpose, installation, and usage and linking to the other, so that both audiences can get started.
74. As a user, I want the README to list prerequisites (Codex CLI installed and logged in) and known risks (whole-disk read in the read-only sandbox, ~25k-token base cost per call, tested Codex version), so that I understand the trade-offs before using it.

## Implementation Decisions

### Modules

1. **Plugin manifest** — declares the plugin `ask-codex` so that its single skill is exposed as `ask-codex:ask`.
2. **The `ask` skill** (instructions only; no helper script, per the "pure SKILL.md" decision). Written in English and using the English glossary terms from `CONTEXT.md`. Responsibilities:
   - Trigger description covering manual invocation, verbal requests to consult Codex, fix loops, and review loops — and nothing else.
   - Consent flow for proactive consultations (three options: consent this once / consent for this session / decline); session grant and model override live only in conversation context.
   - Consultation-type inference and packaging: with-stance for second opinion and targeted check; blind (including failed attempts, excluding hypotheses) for diagnosis and technical question; review loops include unresolved blockers.
   - Model alias resolution: read the Codex model cache in the Codex home (honouring `CODEX_HOME`, else the default home), consider only publicly listed models, fuzzy-match; ambiguous → `AskUserQuestion` with candidates; no match → error listing available models. When no model is given, use the model configured in Codex's config; if none is configured, use the highest-priority listed model.
   - Effort computation: floor `medium`; defaults `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, others → max(model default, `medium`); explicit `low` → `medium` with a note; unsupported → model's highest supported level with a note; `ultra` only on explicit user request. Effort is always passed explicitly to Codex as a config override, so Codex's configured effort never applies. The effort table lives in the skill and is expected to be revised in later releases.
   - Invocation: `codex exec` with read-only sandbox, ephemeral session, JSON event stream to a file, last message to a file, output schema, working root = project directory, git-repo check skipped, prompt on stdin. Run in the background; one background run per model.
   - Monitoring: every 30 minutes (overridable via `EVAL_ASK_CODEX_TIMEOUT_MINUTES`; the staleness threshold keeps the 30:5 ratio, i.e. one sixth of the interval). Liveness = background task alive AND last event within the staleness threshold → auto re-arm with a one-line notice; otherwise `AskUserQuestion` (wait again / stop), recommended option chosen by stale-vs-active. Parallel runs share one timer.
   - Result handling: validate against the schema; present claims with dispositions; parallel results grouped into consensus / solo claims / divergences; unstructured output labeled as such; failures reported without retry or fabrication.
   - Temp directory: `<scratchpad>/ask-codex/<timestamp>/` when a scratchpad is listed in Claude's system prompt, else `$TEMP/ask-codex/<timestamp>/`; deleted after presentation, failure, or stop.
   - Follow-up consultation: fresh session, carried claims + dispositions, scope-locked; new claims only if blocking and flagged as new.
   - Presentation language: the user's conversation language; prompts to Codex and the schema are English.
3. **Response schema** — one JSON Schema used for both initial and follow-up consultations. Shape (decision-level, not final syntax):

   ```
   {
     summary: string,
     claims: [{
       id: string,
       statement: string,
       kind: "fact" | "inference",
       confidence: "high" | "medium" | "low",
       evidence: string[],            // file:line or command/output references
       followup_status?: "resolved" | "unresolved" | "invalid" | "new-blocking"   // follow-up only
     }],
     open_questions: string[]
   }
   ```

4. **Prompt templates** — one per consultation type plus one for follow-up consultations, in English, each stating the read-scope instruction, the with-stance or blind framing, and the requirement to answer in the schema.
5. **Eval suite** — `claude plugin eval` cases plus a stub `codex` executable and a runner that puts the stub first on `PATH` before invoking the eval (see Testing Decisions).
6. **READMEs** — `README.md` (English) and `README.zh-TW.md` (Traditional Chinese), cross-linked; purpose, installation, usage (manual, verbal, proactive, parallel, model aliases and effort), prerequisites, known risks.

### Behavioural contracts

- A consultation never counts toward, or substitutes for, any review/verification loop limit or gate defined by the host workflow; its output is input to Claude's judgment, not a verdict.
- A declined topic is not re-proposed in the same session unless there is material change (e.g. another failed attempt or new evidence).
- Consent prompts and model-scope prompts use `AskUserQuestion`.
- Manual invocation (slash or verbal) is consent; only proactive consultations ask.
- Maximum two models per parallel consultation, distinct; parallel is manual-only unless the session override names two models.

## Testing Decisions

### What makes a good test here

Tests assert externally observable behaviour at a single seam — the Codex CLI boundary: which `codex` commands Claude issues (flags, model, effort, count, ordering relative to `AskUserQuestion`) and what Claude tells the user. They never assert the wording or structure of the skill's instructions.

### Tier 1 — offline eval (default)

- Runner: creates a temp directory holding a stub `codex`, prepends it to `PATH` (PATH is on the eval allowlist, so the skill needs no test hook for the executable), then runs `claude plugin eval` with `--scaffold` and a Bash grant.
- Stub `codex`: records its argv and stdin to the workspace; behaviour selected by a scenario file written by each case's scaffold script — canned valid claims, canned divergent claims (for parallel), non-zero exit, schema-violating output, not-logged-in error, slow run emitting periodic events, stalled run emitting no events.
- Graders: `tool_used` with `input_match` on the JSON-encoded Bash input (flags such as read-only sandbox, ephemeral, output schema, `-m` slug, effort override; absence of `resume`); `tool_order` (`AskUserQuestion` before any `codex` call in proactive cases); `tool_used` with `min: 0, max: 0` (no `codex` call after decline or on over-limit parallel requests); `llm` graders for presentation (every claim has a disposition; consensus/solo/divergence grouping; failure reported without fabricated claims).
- `context.history_file` seeds prior turns (e.g. a session grant already given, a prior consultation's claims for follow-up cases, two failed fix attempts for fix-loop cases).
- Timeout cases use `EVAL_ASK_CODEX_TIMEOUT_MINUTES` with a small value.
- Cases (minimum): manual with question; manual without question; verbal request; fix-loop proposal; session-grant already given (no prompt); declined topic not re-proposed; alias resolution incl. ambiguous alias; effort rules (sol → high, astra → medium, `low` → medium, unsupported → clamped); parallel astra+sol; over-limit parallel refused; follow-up uses a fresh session with carried claims; each failure mode; timeout active vs stalled.

### Tier 2 — live acceptance (opt-in)

Prior art: `codex-feather`'s tests keep deterministic tests as default and gate real Codex runs behind an explicit `--enable-live`. Here, live acceptance is run by hand in a real Claude Code session with the real Codex CLI, covering: manual with question; manual without question; parallel astra+sol (effort medium/high, grouped presentation); simulated fix loop (consent prompt, all three options); ambiguous alias `5.6`; wrong model name (no retry, no fabrication); follow-up consultation (verifies carried claims only); timeout (short override: auto-wait when active, prompt when stalled). Also confirms that Codex writes are denied.

### Prior art

- `codex-feather` (sibling repository): isolated temp workspaces per test, baseline/mutation checks, live runs opt-in.
- Eval harness facts verified from the official plugin-evals docs: runs are `claude -p` children in a throwaway home with only the plugin loaded; env allowlist includes `PATH` but not `CODEX_HOME`; `tool_used.input_match` matches the JSON-encoded tool input.

## Out of Scope

- Resuming a Codex session for follow-ups (ADR-0002); session persistence of any kind.
- Delegation: any write-capable Codex run or applying fixes on Codex's behalf.
- Hard read-scope enforcement via Codex permission profiles / readable roots (documented as a known risk and future hardening).
- Reducing the ~25k-token base cost (e.g. disabling Codex skills loading or custom profiles); any change to the user's Codex configuration.
- More than two models, the same model twice, or proactive parallel consultations without a session override.
- Claude choosing a stronger model or effort on its own.
- Persisting consent or overrides beyond the current conversation.
- Structured full-diff code review (that is `/codex:review`).
- A helper script or runtime dependency beyond the Codex CLI.
- Publishing to GitHub Issues (the tracker for this repo is local markdown).

## Further Notes

- Unconfirmed eval facts that may force a case to move from Tier 1 to Tier 2: how `AskUserQuestion` behaves inside a `claude -p` eval child (if it cannot be answered, post-consent behaviour is tested only through `history_file`); whether a scaffold can seed a model cache into the throwaway Codex home (if not, alias resolution is tested live only, or the stub supplies an equivalent).
- Tested environment: Windows 11, Git Bash for the Bash tool, Codex CLI 0.153.4 (installed via a pnpm shim), `CODEX_HOME` set to a non-default directory. Behaviour on macOS/Linux is expected to match but is untested.
- Verified in this environment: the read-only sandbox allows reads outside the project and denies writes; `codex exec --json` emits events only at step boundaries (no heartbeat), which is why liveness uses event age and not event presence; `codex exec resume` lacks a sandbox flag (one more reason for ADR-0002).
- The default-effort table and the list of known models will drift as Codex releases models; revisit on each skill update.
