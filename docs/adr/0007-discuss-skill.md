# A user-only discuss skill with a fresh Codex session per round

We will add a fourth skill, `discuss`, invoked only as `/ask-codex:discuss [model token] [rounds <n>] [topic]`, in which Claude and one Codex model work a topic (a feature design, an interface, a workflow) over several rounds. In round 1 both produce their own result independently: Claude writes its result to a temporary file before Codex starts, and Codex's prompt carries the topic and context but never Claude's result. Claude integrates the two into tentative agreements and contested points; each later round sends only the contested points, with both sides' full reasons and evidence, and Codex answers each with `accept`, `maintain` or `revise`. The discussion ends when nothing is contested or at the round limit the user chose (2–10; 3 when headless), and the report lists the process, what was agreed (including points both sides dropped) and the user decision items with each side's recommendation and reason.

Every round is one consultation through the unchanged `ask` execution boundary — `consult.py` prepare, run, wait, stop and collect, the same MCP policy and guard (run before every round), model resolution once per discussion — with one script change: a request may carry `reply_schema: "discussion"`, which selects `discussion.schema.json` for Codex's structured output and for reply classification. The reply schema adds per-point `stance`, `revised_statement`, `user_call`, `new_blocking` and `reopen`; the existing consultation schema and the `ask` command line are unchanged (an offline test compares the command line with one captured before the change). ADR 0001, 0003 and 0005 are unchanged; this extends ADR 0002 to multi-round discussion.

## Why a fresh session every round

A discussion looks like the natural case for `codex exec resume`: Codex would keep its own reasoning and not re-explore the project each round. We still start a fresh `--ephemeral` session per round, for two reasons:

- **The read-only guarantee does not hold on resume.** `codex exec resume` takes no `-s/--sandbox` flag (checked on codex-cli 0.159.3), and [openai/codex#40149](https://github.com/openai/codex/issues/40149) (open when this was decided, 2026-10-04) reports a resumed turn writing a file that `-s read-only` had blocked; the only route is an undocumented `-c sandbox_mode=...`. [#49078](https://github.com/openai/codex/issues/49078) reports resumed threads changing permission profiles between turns. Resuming also requires persisting the first session, leaving project content in Codex's history.
- **Multi-round evidence favours separation and full carried context.** [More Rounds, More Noise (arXiv 2603.16244)](https://arxiv.org/abs/2603.16244) found multi-round review worse than single-pass cross-context review (F1 0.376 vs 0.263–0.303; false positives +62%), with more carried context helping within multi-turn conditions. [Not All Flips Are Conformity (arXiv 2606.00820)](https://arxiv.org/abs/2606.00820) attributes about 29% of stance flips to pure conformity and finds that even vacuous reasoning moves 20–39% of resistant agents; [Talk Isn't Always Cheap (arXiv 2509.05396)](https://arxiv.org/abs/2509.05396) reports accuracy falling over debate rounds. No study we found compares same-session and fresh-session debate directly, so the case for resume is not refuted — only unsupported, while its safety cost is concrete.

So each round carries both sides' full reasons and evidence verbatim, concessions must cite specific evidence (or are reported as an `unevidenced concession`), Codex answers `maintain` when it has no new argument, points that flip in round 3 or later are flagged, new points after round 1 must be blocking, and a tentative agreement reopens only by naming a contested point of the same round. The same rules bind Claude.

## Why user-only

As with `review` (ADR 0006), the skill sets `disable-model-invocation: true`: a discussion makes up to ten Codex calls, and a natural-language "discuss this with Codex" is easily confused with a single `ask` second opinion. `ask` points such a request to the command. A harness case with the flag removed confirmed the case detects a model-loaded discussion (5 of 5 runs).

## Considered options

- **Resume one Codex session across rounds:** keeps Codex's reasoning and saves re-exploration, but cannot pass the sandbox flag, has a reported read-only bypass, and persists the session. Revisit when openai/codex#40149 is fixed and resume accepts `-s`.
- **Reuse the consultation schema's `followup_status`:** no script change, but `resolved`/`unresolved`/`invalid` do not say which side accepted what, which made reports and graders ambiguous.
- **Parallel models in a discussion:** a three-party integration with far more complex rules; out of scope.

## Consequences and honest limits

- A discussion multiplies Codex calls (up to ten) and each round re-explores the project.
- The anti-conformity rules are instructions to both models, not enforcement; the evidence label and the late-flip flag in the report are the control.
- Codex output is carried into the next round's prompt; that it is data is an instruction, as everywhere in ask-codex.
- A round that fails, is stopped, cannot be confirmed stopped or returns an unstructured reply ends the discussion with a partial report; nothing is retried.
- Codex's web search tool is not controlled by ask-codex (as for `ask`).
