# 01 — Manual consultation tracer bullet

**What to build:** A user types `/ask-codex:ask <question>` and gets back Codex's opinion as a list of claims, each with Claude's disposition (adopt / reject / investigate) and a reason. Under the hood Claude runs Codex in the background, read-only, ephemeral, with a JSON Schema–constrained reply and a JSON event stream, waits for the result, presents it in the user's conversation language, and deletes its temporary files. Model = the one configured in Codex; effort = the consultation-effort rules for that model (floor `medium`; `gpt-5.6-sol` → `high`, `gpt-6-astra` → `medium`, otherwise max(model default, `medium`)), always passed explicitly so Codex's configured effort never applies. This ticket also stands up the whole delivery and test skeleton: the `ask-codex` plugin exposing the `ask` skill, the single response schema (summary, claims with id / statement / kind fact|inference / confidence / evidence / optional followup_status, open_questions), an English prompt template, the stub `codex` executable, the runner that puts the stub first on `PATH` before `claude plugin eval`, and the first eval case. See spec: Solution, Implementation Decisions (modules 1–5), Testing Decisions Tier 1.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The plugin loads in Claude Code and the skill is invocable as `/ask-codex:ask`.
- [ ] The skill instructions are in English and use the English glossary terms from `CONTEXT.md` (consultation, claim, disposition, …).
- [ ] The Codex invocation uses: read-only sandbox, ephemeral session, JSON event stream written to a file, last message written to a file, the response schema, the project directory as working root, git-repo check skipped, prompt on stdin, and an explicit effort override.
- [ ] The run happens in the background; Claude does not act on anything that depends on the result before it arrives.
- [ ] The prompt instructs Codex to stay within the project directory and any paths Claude explicitly lists.
- [ ] Every returned claim is presented with a disposition and reason; Claude never applies a suggestion just because Codex made it.
- [ ] Temporary files live under `<scratchpad>/ask-codex/<timestamp>/` when a scratchpad is listed in Claude's system prompt, otherwise under `$TEMP/ask-codex/<timestamp>/`, and are deleted after presentation.
- [ ] Stub `codex` records argv and stdin and selects its behaviour from a scenario file written by the case's scaffold; the runner prepends the stub to `PATH` and invokes the eval with scaffolding and a Bash grant.
- [ ] Eval case "manual with question" passes: `tool_used` + `input_match` asserts the flags above; an `llm` grader asserts every claim has a disposition.
- [ ] One live check with the real Codex CLI confirms a write attempt inside the project is denied.
