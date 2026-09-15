# Spec: ask-codex MVP

Status: ready-for-agent

Vocabulary follows `CONTEXT.md` (English equivalents). Decisions respect ADR-0001 (call `codex exec` directly), ADR-0002 (fresh session for follow-up consultations) and ADR-0003 (MCP policy).

## Problem Statement

When Claude is working in Claude Code and gets stuck — the same bug survives repeated fix attempts, or the same Plan/spec keeps bouncing through review rounds without converging — there is no lightweight way for Claude to get an independent opinion from a different model family and then judge that opinion itself.

The official Codex plugin for Claude Code does not cover this:

- `/codex:review` and `/codex:adversarial-review` are user-only commands (model invocation disabled) and must be relayed verbatim; Claude may not weigh in.
- `/codex:rescue` is delegation: it defaults to a write-capable Codex run and forbids Claude-side analysis.

The user wants a consultation, not a delegation: Codex's shell commands run read-only, Codex returns opinions, and Claude decides — claim by claim — what to adopt. MCP servers run outside that sandbox, so which MCP servers Codex may use during a consultation must be controlled explicitly. The user also wants control over when this costs money: Claude may propose a consultation, but only the user can approve it, and the user must be able to pick models and reasoning effort using short aliases.

## Solution

A Claude Code plugin named `ask-codex` providing two skills: `ask` (invoked as `/ask-codex:ask` or by natural-language requests such as "ask codex about this") and `setup` (`/ask-codex:setup`, builds the MCP allowlist config).

- **Manual consultation**: the user invokes the skill (slash command or an explicit verbal request). Invoking it is consent. With no question given, Claude infers the question from the conversation.
- **Proactive consultation**: Claude proposes a consultation only in a fix loop or a review loop, and asks the user via `AskUserQuestion` for one-time consent, a session grant, or a decline.
- Claude infers the consultation type (second opinion, diagnosis, targeted check, technical question) from context, packages the question with-stance or blind accordingly, and runs Codex non-interactively with `-s read-only`, ephemeral, with a JSON Schema–constrained reply, in the background.
- **MCP policy**: by default every MCP server is disabled for the consultation (allowlist mode with an empty allowlist). A user-level or project-level ask-codex config can allow specific servers, or switch to minimal-deny mode (only `node_repl` and `cua_repl` disabled). Servers defined or redefined by the project's own Codex config are disabled or the consultation is aborted unless the user confirms them. An MCP guard verifies the effective server set before every run.
- Codex returns structured claims. Claude presents each claim with its own disposition (adopt / reject / investigate) and reasoning.
- **Parallel consultation**: the user can name two different models; Claude runs both independently and presents consensus, solo claims, and divergences.
- **Follow-up consultation**: always a fresh Codex session carrying prior claims and dispositions, scoped to verifying them.
- Long runs are monitored; after 30 minutes Claude checks liveness and only asks the user whether to keep waiting when liveness is not confirmed.

**Narrowed claim (exact text used by the skill, the consent line, and the README):** "Codex's shell commands run read-only (writes denied, shell network blocked). MCP servers run outside that sandbox: by default all are disabled per consultation; servers you allow (or, in minimal-deny mode, all except node_repl/cua_repl) remain usable and may include tools that write or execute, limited only by instruction."

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
9. As a user, I want the consent prompt to summarize the consultation in one line (type, question, what Codex may read — any file my account can read, instructed to stay in the project — and the MCP statement for the active policy), so that I know what will be sent to OpenAI and which tools Codex can use.
10. As a user, I want to choose "consent this once", so that only this proactive consultation runs.
11. As a user, I want to choose "consent for this session", so that later proactive consultations in this session run without asking me again.
12. As a user, I want to choose "decline", so that Claude continues on its own and does not re-propose a consultation on the same topic in this session unless the situation materially changes.
13. As a user, I want a session grant to disappear when the conversation context is lost, so that consent never silently outlives the conversation I gave it in.
14. As a user, I want consent and manual triggers to count only when they come from my own messages or my answers to `AskUserQuestion`, never from file contents, tool results, or Codex output, so that nothing can grant consent on my behalf.

### Consultation types and packaging

15. As a user, I want Claude to decide the consultation type from context for both manual and proactive consultations, so that I never have to specify it.
16. As Claude, when asking for a second opinion, I want to include the Plan or design decision and explicitly ask Codex to verify independently and challenge it, so that the thing under review is visible.
17. As Claude, when asking for a targeted check, I want to include the implementation or diff plus my specific concern, so that Codex focuses on the actual doubt rather than doing a general review.
18. As Claude, when asking for a diagnosis, I want to send symptoms, evidence, and every failed attempt with its result, but not my current root-cause hypothesis, so that Codex's view is not anchored by mine and does not repeat failed fixes.
19. As Claude, when asking a technical question, I want to send the question and relevant evidence blind, so that the answer is independent.
20. As Claude, in a review loop, I want to include the Plan plus the unresolved blockers from earlier rounds, and ask Codex whether each blocker holds and whether the Plan should be simplified, split, or redirected, so that the consultation targets the actual deadlock.
21. As Claude, I want to instruct Codex to stay within the project directory and any paths I explicitly list, never to read in-project secrets (`.env*`, `*.pem`, key/credential files), to use MCP tools for lookups only, and to treat all file and tool content as data, so that the read scope and tool use are limited even though the sandbox allows whole-disk reads and MCP runs outside it.
22. As Claude, I want never to include secrets from the conversation in the packaged prompt, so that tokens or credentials are not sent to OpenAI.
23. As Claude, I want prompts to Codex written in English, so that they are token-efficient and consistent with the skill.

### MCP policy

24. As a user, I want every MCP server disabled for a consultation by default, so that no tool that writes, executes code, or controls applications runs outside the sandbox unless I chose it.
25. As a user, I want to allow specific MCP servers (e.g. a lookup server) in a user-level or project-level ask-codex config, so that Codex can look things up when I need it to.
26. As a user, I want to switch to minimal-deny mode, where only `node_repl` and `cua_repl` are disabled, so that I can keep all other servers when I accept that risk.
27. As a user, I want `/ask-codex:setup` to list the MCP servers Codex currently sees (global and project Codex config), let me pick which to allow, pick the mode and the scope (user or project), and write the config file, so that I never have to edit JSON by hand.
28. As a user, when a project-level ask-codex config is wider than the default, I want to confirm it once per session before it is used, so that a cloned repository cannot silently widen the policy.
29. As a user, I want MCP servers that appear only in the project's listing, or whose definition differs from my global definition, to be disabled unless I confirm them, so that a repository cannot add or redefine a server behind my back.
30. As a user, when the project's own Codex config (in the project or any parent up to the repository root) defines MCP servers, I want to be asked once per session naming each server and its command, and the consultation aborted if I decline, so that nothing depends on unverified override precedence.
31. As a user, I want Claude to verify the effective MCP server set before every Codex run and abort if it differs from what the policy expects, so that a Codex update that breaks the disabling mechanism fails safe.
32. As a user, I want Codex's apps surface disabled for consultations when Codex supports disabling it, so that connectors cannot act on my behalf.

### Models and effort

33. As a user, I want to name models with short aliases such as `sol`, `5.6 sol`, or `astra`, so that I don't have to type full model slugs.
34. As a user, I want aliases resolved against the models Codex currently lists (not a hardcoded table), so that new models work without a skill update.
35. As a user, when an alias is ambiguous (e.g. `5.6` matches several models), I want to pick from the candidates, so that Claude never guesses.
36. As a user, when an alias matches nothing, I want an error listing the currently available models, so that I can correct it.
37. As a user, when I don't name a model, I want the model configured in my Codex settings to be used, so that my default choice is respected.
38. As a user, I want consultation effort never to go below `medium`, so that a consultation is never run at a uselessly low reasoning level.
39. As a user, I want default effort `high` for `gpt-5.6-sol` and `medium` for `gpt-6-astra`, and for any other model the higher of its own default and `medium`, so that each model runs at a sensible level without me specifying it.
40. As a user, I want the effort in my Codex config to be ignored for consultations, so that a low default there can't drag consultations below the floor.
41. As a user, when I explicitly request `low`, I want it raised to `medium` with a note, so that the floor is a hard rule.
42. As a user, when I request an effort the model doesn't support, I want the model's highest supported level used with a note, so that the consultation still runs.
43. As a user, I want `ultra` used only when I explicitly ask for it, so that Codex's costly automatic delegation never happens by default.
44. As a user, when I specify a model or effort that differs from the current session setting, I want to be asked whether it applies to this consultation only or to the rest of the session, so that my override lasts exactly as long as I intend.
45. As a user, when I re-specify the setting already in force for the session, I want no prompt, so that I'm not asked redundant questions.
46. As a user, I want proactive consultations to use the Codex default model (or my session override), never a model Claude picks for difficulty, so that cost decisions stay mine.

### Parallel consultation

47. As a user, I want to name two different models in one manual consultation (e.g. `astra:high, sol`), so that I get two independent opinions.
48. As a user, I want each model in a parallel consultation to take its own optional effort, with the effort rules applied per model, so that I can tune each one.
49. As a user, I want parallel consultation limited to two distinct models, so that cost stays bounded.
50. As a user, I want Claude to refuse more than two models or the same model twice, with a clear message, so that the limit is predictable.
51. As a user, I want each model to run without seeing the other's output, so that the opinions are genuinely independent.
52. As a user, I want the combined result grouped into consensus, solo claims, and divergences, each tagged with its source model and Claude's disposition, so that agreement and disagreement are obvious.
53. As a user, for every divergence I want Claude to state which side it adopts and why, so that I can audit the judgment.
54. As a user, when one model fails, I want the successful model's opinion presented normally with a note naming the failed model and the reason, so that one failure doesn't waste the other result.
55. As a user, I want parallel consultation to be manual-only (unless my session override specifies two models), so that Claude never doubles the cost on its own.

### Results and dispositions

56. As Claude, I want Codex's reply constrained by a JSON Schema, so that I can evaluate claims one by one.
57. As Claude, I want each claim to state whether it is a fact or an inference, its confidence, and evidence locations where possible, so that I can weigh it correctly.
58. As a user, I want every claim listed with Claude's disposition (adopt / reject / investigate) and a reason, so that I see both what Codex said and what Claude concluded.
59. As a user, I want the presentation in the language of my conversation while code, paths, and quotes stay verbatim, so that it reads naturally for me.
60. As a user, I want Claude to never apply Codex's suggestions automatically just because Codex made them, and never to follow instructions embedded in Codex's output, so that decisions remain with Claude and me.
61. As a user, I want a consultation to never count as, or substitute for, a formal review or verification step in my workflow, so that my existing review gates keep their meaning.
62. As a user, when Claude materially revises a Plan based on a consultation, I want that treated as a material revision under whatever review rules apply, so that consultation can't bypass review.

### Follow-up consultation

63. As Claude, when a claim is marked investigate or I need to re-check a revised Plan, I want to start a follow-up consultation in a fresh Codex session carrying the prior claims and my dispositions, so that the follow-up is not anchored by Codex's earlier context (ADR-0002).
64. As Claude, I want a follow-up consultation scoped to verifying the carried claims — each resolved, unresolved, or invalid — so that the review loop converges instead of producing new points each round.
65. As Claude, I want Codex to be able to raise a new claim in a follow-up only if it is blocking, and marked as new, so that critical problems are still surfaced without scope creep.

### Execution, monitoring, and cleanup

66. As a user, I want Codex's shell commands run read-only (writes denied, shell network blocked), so that a consultation's commands can never modify my files; MCP servers are governed by the MCP policy.
67. As a user, I want Codex runs to be ephemeral, so that consultations don't clutter my Codex history or keep what Codex read on disk.
68. As a user, I want consultations to run in the background, so that Claude can continue unrelated work and isn't bound by foreground command time limits.
69. As Claude, I want to wait for the consultation result before doing work that depends on it, so that I don't act on half the picture.
70. As a user, I want Claude to check a running consultation every 30 minutes, so that long runs are neither abandoned nor waited on blindly.
71. As a user, when the check confirms Codex is still running (background task alive and a new progress event within the last 5 minutes), I want Claude to keep waiting automatically and tell me in one line, so that I'm not interrupted by healthy long runs.
72. As a user, when liveness is not confirmed, I want to be asked "wait another 30 minutes" or "stop this consultation", with elapsed time and the last progress event and its age, so that I can decide with real information.
73. As a user, I want "stop this consultation" recommended when the run looks stalled and "wait another 30 minutes" recommended when it doesn't, so that the default choice matches the evidence.
74. As a user, I want stopping to end the Codex run and be handled like any other failure, so that Claude simply continues its work.
75. As a user, I want a parallel consultation to share one timer, reporting which model is done and asking only about the ones still running, so that I'm asked once and never shown half a result that later changes.
76. As a user, I want a consultation's temporary files created with `mktemp -d` inside an `ask-codex` directory under Claude's session scratchpad when one is listed, otherwise under the system temp directory, so that files stay isolated per session and are private to me.
77. As a user, I want all temporary files deleted after the result is presented — including after failures and stops — so that nothing Codex read lingers on disk.
78. As a tester, I want an `EVAL_ASK_CODEX_TIMEOUT_MINUTES` override (positive integer only, with a notice when active) for the check interval, so that the timeout path is testable without waiting 30 minutes.

### Failure handling

79. As a user, when Codex is missing, not logged in, times out, cannot run in the project location, or returns output that violates the schema, I want a short explanation and Claude to continue its own work without retrying, so that a failed consultation costs no more than necessary.
80. As a user, when Codex is not logged in, I want to be told to run `! codex login`, so that I know the fix.
81. As a user, when Codex returns readable but unstructured output, I want it passed to Claude labeled as unstructured and still judged, so that usable content isn't thrown away.
82. As a user, I want Claude never to fabricate a Codex opinion when Codex failed, so that everything attributed to Codex really came from Codex.

### Installation and docs

83. As a user, I want to install ask-codex as a Claude Code plugin from its GitHub repository, so that installation is a standard plugin flow.
84. As a user, I want an English `README.md` and a Traditional Chinese `README.zh-TW.md`, each briefly covering purpose, installation, and usage and linking to the other, so that both audiences can get started.
85. As a user, I want the README to state the narrowed claim verbatim and list prerequisites (Codex CLI installed and logged in), the MCP policy and setup, known risks (whole-disk read by Codex's shell, MCP servers outside the sandbox, ~25k-token base cost per call, tested Codex version) and known limitations (projects on drives where the Codex Windows sandbox cannot run, persistently trusted projects covered only by the fail-safe), so that I understand the trade-offs before using it.

## Implementation Decisions

### Modules

1. **Plugin manifest and marketplace manifest** — declare the plugin `ask-codex` (skills `ask-codex:ask` and `ask-codex:setup`) and a self-hosted marketplace with the plugin as its single entry.
2. **The `ask` skill** (instructions only; no helper script). Written in English and using the English glossary terms from `CONTEXT.md`. Responsibilities:
   - Trigger description covering manual invocation, verbal requests to consult Codex, fix loops, and review loops — and nothing else.
   - Consent flow for proactive consultations (three options: consent this once / consent for this session / decline); consent counts only from the user's own turns or `AskUserQuestion` answers; session grant and model override live only in conversation context.
   - Consultation-type inference and packaging: with-stance for second opinion and targeted check; blind (including failed attempts, excluding hypotheses) for diagnosis and technical question; review loops include unresolved blockers; secrets never packaged.
   - Model alias resolution: read the Codex model cache in the Codex home (honouring `CODEX_HOME`, else the default home), consider only publicly listed models, fuzzy-match; ambiguous → `AskUserQuestion` with candidates; no match → error listing available models. When no model is given, use the model configured in Codex's config; if none is configured, the highest-priority listed model; if neither file exists, omit the model flag and use effort `medium`. Resolved slugs must match `^[A-Za-z0-9._-]+$`.
   - Effort computation: floor `medium`; defaults `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, others → max(model default, `medium`); explicit `low` → `medium` with a note; unsupported → model's highest supported level with a note; `ultra` only on explicit user request; always one of the known enum values, passed explicitly to Codex as a config override so Codex's configured effort never applies.
   - MCP policy (ADR-0003):
     - Config: user-level `~/.claude/ask-codex.json`, project-level `.claude/ask-codex.local.json`; project values override user values per key; keys `mcp_policy` (`allowlist` default | `minimal-deny`) and `mcp_allow` (server names). No file → allowlist with an empty list.
     - Listings: `codex mcp list --json` from a neutral empty temp directory and from the project directory, each in a subshell so Claude's working directory never changes.
     - Disable set: allowlist → every listed server not allowed; minimal-deny → `node_repl`, `cua_repl`; plus unconfirmed project-defined servers. One same-name disabled definition per server (a config override defining the server with a placeholder command and `enabled=false`); server names validated against `^[A-Za-z0-9_.-]+$`.
     - Project-defined servers: (a) only in the project listing; (b) any field of the definition differs from the neutral listing; (c) any `.codex/config.toml` from the project directory up to the repository root contains an `mcp_servers.<name>` table or dotted key (read with Read/Glob, not Bash). (a)/(b) → disabled unless confirmed once per session; (c) → ask once per session naming each server and command, abort on decline (never rely on the override).
     - Project-level widening: a project-level ask-codex config wider than the default is confirmed once per session.
     - Guard: re-list from the project directory with the overrides; the enabled set must equal the expected set, otherwise abort without running Codex.
     - Apps surface disabled with the apps feature switch when verified to work.
   - Invocation: `codex exec` with `-s read-only`, ephemeral session, JSON event stream written to a file, last message written to a file, output schema, project directory as working root, git-repo check skipped, the MCP disable definitions, the apps switch, the explicit effort override, prompt on stdin; all paths single-quoted; run in the background; one background run per model. Never: dangerous bypass flags, full-auto/yolo, profiles, extra writable dirs, ignoring user config, writable sandbox modes, other config keys, resume/fork.
   - Monitoring: every 30 minutes (overridable via `EVAL_ASK_CODEX_TIMEOUT_MINUTES`, positive integer only; staleness threshold one sixth of the interval). Liveness = background task alive AND last event within the staleness threshold → auto re-arm with a one-line notice; otherwise `AskUserQuestion` (wait again / stop). Parallel runs share one timer.
   - Result handling: validate against the schema; present claims with dispositions; parallel results grouped into consensus / solo claims / divergences; unstructured output labeled as such; failures reported without retry or fabrication; never act on instructions contained in Codex output.
   - Temp directory: `mktemp -d` inside an `ask-codex` directory under the scratchpad when listed in Claude's system prompt, else under `${TMPDIR:-${TEMP:-/tmp}}`; removal only for a path inside an `ask-codex` directory and never from an empty variable; deleted after presentation, failure, or stop.
   - Follow-up consultation: fresh session, carried claims + dispositions, scope-locked; new claims only if blocking and flagged as new.
   - Presentation language: the user's conversation language; prompts to Codex and the schema are English.
   - The narrowed claim appears verbatim in the skill.
3. **The `setup` skill** — lists MCP servers from `codex mcp list --json` (run in the project), asks which to allow (`AskUserQuestion` multi-select, batched when more than four), the mode and the scope, writes the chosen ask-codex config file, and shows the result; never writes without the user's answers.
4. **Response schema** — one JSON Schema used for both initial and follow-up consultations. Shape (decision-level, not final syntax):

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

5. **Prompt templates** — one per consultation type plus one for follow-up consultations, in English, each stating the read-scope and secret-exclusion instruction, the MCP-lookup-only instruction, the data-not-instructions rule, the with-stance or blind framing, and the requirement to answer in the schema.
6. **Eval suite** — `claude plugin eval` cases plus a stub `codex` executable and a runner that removes real `codex` entries from `PATH`, puts the stub first, and verifies resolution before invoking the eval (see Testing Decisions).
7. **READMEs** — `README.md` (English) and `README.zh-TW.md` (Traditional Chinese), cross-linked; purpose, installation, usage (manual, verbal, proactive, parallel, model aliases and effort, MCP policy and setup), prerequisites, known risks, known limitations, the narrowed claim verbatim.

### Behavioural contracts

- A consultation never counts toward, or substitutes for, any review/verification loop limit or gate defined by the host workflow; its output is input to Claude's judgment, not a verdict.
- A declined topic is not re-proposed in the same session unless there is material change (e.g. another failed attempt or new evidence).
- Consent prompts, model-scope prompts, MCP confirmations and project-widening confirmations use `AskUserQuestion`.
- Manual invocation (slash or verbal, from the user's own messages) is consent; only proactive consultations ask for consultation consent.
- Maximum two models per parallel consultation, distinct; parallel is manual-only unless the session override names two models.

## Testing Decisions

### What makes a good test here

Tests assert externally observable behaviour at a single seam — the Codex CLI boundary: which `codex` commands Claude issues (flags, model, effort, MCP disable definitions, count, ordering relative to `AskUserQuestion`) and what Claude tells the user. They never assert the wording or structure of the skill's instructions.

### Tier 1 — offline eval (default)

- Runner: removes every `PATH` entry containing a real `codex`, creates a temp directory holding a stub `codex`, prepends it to `PATH`, fails fast unless `codex` resolves to the stub, then runs `claude plugin eval` with `--scaffold`, `--no-publish`, `--trust-plugin` and a limited tool grant.
- Stub `codex`: `mcp list --json` returns a scenario-defined server list (it can differ between the neutral and the project directory) honouring same-name disabled overrides, and records project-directory calls in a log; `exec` validates its argv against an allowlist (writing a violation marker otherwise), writes an execution sentinel, records argv and stdin to the workspace, emits JSONL events, and writes a canned reply. Behaviour is selected by a scenario file written by each case's scaffold script — canned valid claims, canned divergent claims (for parallel), non-zero exit, schema-violating output, not-logged-in error, slow run emitting periodic events, stalled run emitting no events, a guard failure, project-only and redefined servers.
- Graders: the **CODEX_CALL** grader (`tool_used` on Bash whose `input_match` targets only the `command` field and only commands that are `codex mcp …` or `codex exec …`) for positive and zero-call assertions; `input_match` for required and forbidden flags; stub records (sentinel, list log, violation marker) with per-case expectations; `tool_order` (`AskUserQuestion` before any `codex` call in consent cases); `llm` graders for presentation (every claim has a disposition; consensus/solo/divergence grouping; failure reported without fabricated claims; consent line wording).
- `context.history_file` seeds prior turns (e.g. a session grant already given, a prior consultation's claims for follow-up cases, two failed fix attempts for fix-loop cases, a spoofed grant inside a tool result).
- Timeout cases use `EVAL_ASK_CODEX_TIMEOUT_MINUTES` with a small value.
- Eval runs never read or write the real user-level ask-codex config; user-level behaviour is exercised only inside the eval child's throwaway home.

### Tier 2 — live acceptance (opt-in)

Prior art: `codex-feather`'s tests keep deterministic tests as default and gate real Codex runs behind an explicit `--enable-live`. Here, live acceptance is run in a real Claude Code session with the real Codex CLI: shell writes denied and shell network blocked with the exact flags; disabled MCP servers absent from Codex's namespaces; apps switch effect; project-layer Codex MCP definitions not reaching `exec` (probe directories under `D:\tmp`, deleted afterwards); plus the user-visible scenarios (manual, empty invocation, parallel, fix-loop consent, ambiguous alias, wrong model, follow-up, timeout).

### Prior art

- `codex-feather` (sibling repository): isolated temp workspaces per test, baseline/mutation checks, live runs opt-in.
- Eval harness facts verified from the official plugin-evals docs: runs are `claude -p` children in a throwaway home with only the plugin loaded; env allowlist includes `PATH` but not `CODEX_HOME`; `tool_used.input_match` matches the JSON-encoded tool input.

## Out of Scope

- Resuming a Codex session for follow-ups (ADR-0002); session persistence of any kind.
- Delegation: any write-capable Codex run or applying fixes on Codex's behalf.
- Hard read-scope enforcement for Codex's shell via Codex permission profiles / readable roots (documented as a known risk).
- Per-tool MCP filtering (e.g. allowing only some tools of a server); policy works per server.
- Reducing the ~25k-token base cost; any change to the user's Codex configuration.
- More than two models, the same model twice, or proactive parallel consultations without a session override.
- Claude choosing a stronger model or effort on its own.
- Persisting consent or overrides beyond the current conversation (the ask-codex config file holds only the MCP policy).
- Structured full-diff code review (that is `/codex:review`).
- A helper script or runtime dependency beyond the Codex CLI.
- Publishing to GitHub Issues (the tracker for this repo is local markdown).

## Further Notes

- Verified in this environment (Codex CLI 0.153.4, Windows 11): the read-only sandbox allows reads outside the project and denies writes, and blocks shell network; `codex exec --json` emits events only at step boundaries (no heartbeat), which is why liveness uses event age; `codex exec resume` lacks a sandbox flag (one more reason for ADR-0002).
- MCP evidence: user-config and plugin-provided MCP servers are exposed in `exec`, run outside the sandbox, and lookup calls work without approval; the same-name disabled definition removes a server (config-defined or plugin-provided); documented plugin-scoped keys and feature switches did not; `codex mcp list --json` matched exec behaviour and prints full definitions except per-tool settings. Project-layer Codex MCP definitions were not loaded in untrusted, per-call-trusted, own-`.git`, and repository-sub-directory cases; persistently trusted projects were not tested and rely on the rule-(c) fail-safe.
- Known limitation: a project on a drive where the Codex Windows sandbox cannot run (observed on a RAM disk: `codex exec -C` fails with "os error 1") cannot be consulted; the skill reports the failure.
- Unconfirmed eval facts that may force a case to move from Tier 1 to Tier 2: how `AskUserQuestion` behaves inside a `claude -p` eval child (if it cannot be answered, post-consent behaviour is tested only through `history_file`); whether a scaffold can seed a model cache into the throwaway Codex home.
- Tested environment: Windows 11, Git Bash for the Bash tool, Codex CLI 0.153.4 (installed via a pnpm shim), `CODEX_HOME` set to a non-default directory. Behaviour on macOS/Linux is expected to match but is untested.
- The default-effort table and the list of known models will drift as Codex releases models; revisit on each skill update.
