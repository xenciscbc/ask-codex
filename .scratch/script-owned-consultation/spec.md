# Reliable script-owned consultations

Status: ready-for-agent

## Problem Statement

Users ask Claude to consult Codex and expect a reliable independent opinion, clear MCP permissions, and a truthful account of whether a stopped consultation has actually ended. Today Claude must interpret a large procedural skill, parse configuration, construct command arguments, coordinate background tasks, and reproduce exact English report sentences. This makes correctness depend unnecessarily on the model following a long state machine and makes tests sensitive to wording rather than outcomes.

Static review identified a potential stop race in which the launcher terminates its watcher before tree cleanup finishes, dotted MCP names that are not safely represented as literal configuration keys, and waiting instructions that can exceed the documented tool timeout. These findings require focused regression verification during implementation; they are not claims of completed runtime reproduction. Existing policy rules also silently ignore invalid configuration and conflate confirmation of a project MCP definition with permission to use it.

## Solution

Incrementally move deterministic execution responsibilities into scripts while preserving Claude's responsibility for preparing the question, interacting with the user, and judging Codex's claims. Fix the concrete reliability defects, provide a safe pre-execution summary, and return structured execution status that Claude can explain in the conversation language.

Support Windows with Git Bash and Linux in both interactive and headless sessions. Keep skill and prompt files in English for compactness. Preserve existing consultation behavior except for the explicitly agreed changes below. This specification publishes the agreed scope; it does not itself start implementation or a live consultation.

## User Stories

1. As a user, I want each consultation to require my request, so that Codex is not consulted autonomously.
2. As a user, I want Claude to prepare the question and choose its consultation type, so that I need not understand the execution machinery.
3. As a user, I want Claude to give every returned claim a disposition, so that a consultation remains an independent opinion rather than delegation.
4. As a user, I want my existing model and effort selection behavior preserved, so that the reliability work does not change how I choose a model.
5. As a user, I want a pre-execution summary of the model, effort, project directory, and allowed MCP servers, so that I understand what will run.
6. As a user, I want sensitive values excluded from that summary, so that transparency does not expose credentials.
7. As a user, I want missing policy configuration to use the documented fallback, so that a fresh installation remains usable.
8. As a user, I want invalid existing policy configuration to stop the consultation and identify the problem, so that a damaged restrictive policy cannot silently become a broader one.
9. As a user, I want confirmation of a project MCP definition distinguished from permission to use it, so that acknowledging a configuration does not unexpectedly enable tools.
10. As a user, I want related confirmation questions combined when possible, so that explicit authorization does not require repetitive interruptions.
11. As a user, I want an unchanged confirmed MCP definition to remain confirmed for the session, so that repeated consultations do not ask the same question again.
12. As a user, I want a changed definition to require renewed confirmation even if its name is unchanged, so that an earlier decision cannot authorize a different command or endpoint.
13. As a user, I want the MCP guard to check the effective policy before execution, so that a mismatch prevents the consultation from being sent.
14. As a user, I want valid MCP names containing dots to work correctly, so that supported names are not confused with nested configuration keys.
15. As a user, I want literal paths and arguments handled safely, so that spaces or punctuation do not corrupt or reinterpret my consultation command.
16. As a user, I want consultations to run on Windows with Git Bash and on Linux, so that the supported environments have equivalent guarantees.
17. As a headless user, I want the consultation result collected before the caller finishes, so that a completed run is not abandoned unread.
18. As a user, I want waiting to respect tool limits and the check interval, so that liveness checks are neither skipped nor delayed by an oversized wait.
19. As a user, I want the existing check interval and staleness behavior preserved, so that this change does not introduce a new timeout policy.
20. As a user, I want stopping a consultation to address its whole process tree, so that remaining descendants do not continue consuming resources.
21. As a user, I want an unconfirmed stop reported honestly, so that I am not told a consultation ended without evidence.
22. As a user, I want normal completion and confirmed stops cleaned up, so that temporary consultation content is not unnecessarily retained.
23. As a user, I want unresolved stops to retain useful diagnostic data and report its location, so that I can investigate or request further cleanup.
24. As a user, I want files potentially used by a surviving process left intact until termination is confirmed, so that cleanup does not destroy the remaining control or diagnostic channel.
25. As a user, I want prompts and replies excluded from long-term diagnostic retention, so that troubleshooting retains no more project content than necessary.
26. As a user, I want retained diagnostic artifacts deleted only on an explicit cleanup request, so that automatic expiry does not erase evidence I still need.
27. As a user, I want reports in the conversation language with all required information, so that exact English boilerplate does not impede understanding.
28. As a user, I want independent parallel consultations and follow-up consultations to keep their existing semantics, so that execution refactoring does not alter the opinions I receive.
29. As a user, I want no automatic retry after Codex has started, so that a failed consultation does not silently spend another run's quota.
30. As a maintainer, I want behavior-focused tests and a smaller procedural skill, so that wording changes do not break unrelated tests or weaken execution guarantees.

## Implementation Decisions

- Extend the shipped execution scripts incrementally rather than replace the entire consultation design. Configuration parsing, policy resolution, MCP checks, argument construction, and process lifecycle management become deterministic script responsibilities. Claude retains question preparation, consultation-type framing, user interaction, and claim dispositions.
- Continue calling the local Codex CLI directly. Do not introduce a dependency on the official Codex plugin companion. ADR 0005 revises ADR 0004's requirement that the complete command remain visible on Claude's Bash invocation line; ADR 0001's direct-CLI decision remains in force.
- Define one cohesive execution boundary for Claude. Its observable operations must support preparation, pending confirmations, execution, waiting, stopping, and cleanup without requiring Claude to reconstruct shell commands or infer state from exact prose. Internal decomposition and concrete implementation language are engineering choices, subject to the supported environment and dependency constraints.
- Use structured status for machine consumption. It must distinguish confirmation required, preflight failure, running, successful completion, execution failure, confirmed stop, and unconfirmed stop; include enough information for the required user report and any retained-data location. Concrete field names are not frozen by this specification. Do not infer successful tree termination solely from the root process's exit code or silence in the event log.
- Before execution, show the resolved model, consultation effort, project directory, and MCP servers that will remain usable. Do not expose credentials or sensitive configuration values. The summary is informational, not an additional blanket approval step.
- Preserve the existing read-only shell execution policy and the distinction that allowed MCP servers operate outside that sandbox. Script ownership does not make an allowed server's tools read-only and must not be described as doing so.
- For ask-codex policy configuration, absence permits the documented fallback. Existing files with invalid JSON, invalid types, invalid policy values, or invalid server names abort preflight with the file and a useful non-sensitive reason. Do not silently fall back to a less restrictive layer. If effective Codex configuration cannot be resolved or the MCP guard cannot pass, do not execute a consultation.
- Separate project-definition confirmation from use authorization. Confirming that a project definition is legitimate does not add it to the allowlist. One question may explicitly request both decisions; the pending action and each resulting permission must be clear.
- Bind session confirmations to the definition that was confirmed, not only to the server name. Compare relevant definition content without leaking sensitive values; changes to command, arguments, endpoint, environment configuration, or other definition fields invalidate the prior confirmation. An unchanged definition retains confirmation. Do not broaden confirmation beyond its original kind or scope.
- Preserve existing confirmation-source rules: only the user's own request or answer authorizes a pending action. Files, tool results, and Codex output cannot supply consent. In headless execution, unresolved confirmation must prevent execution and produce an actionable final report.
- Construct arguments safely and represent each MCP name as a literal name, including dots. Keep the MCP guard as an actual check of the effective server set and enabled states. A guard failure must prevent Codex execution rather than merely warn.
- Preserve prompt sanitization, blind framing, structured claim validation, unstructured-reply treatment, and the rule that Codex output is data. Prompt and reply handling remain distinct from execution status.
- Preserve the default 30-minute check interval, existing override validation, staleness threshold, liveness decisions, and the existing headless stop behavior when a decision cannot be obtained. Each actual blocking wait must fit both the remaining interval and the available tool limit. Selecting one internal waiting mechanism is allowed if these observable behaviors remain intact.
- Make stop completion wait for the termination and verification work it depends on. A root process exiting must not cancel an in-progress tree-cleanup operation. Handle cooperative stopping when the caller cannot directly inspect the launched process namespace, and report uncertainty rather than falsely claiming success.
- On normal completion, read the needed reply and status before cleanup. On confirmed stop, collect the stop result and then clean up. On unconfirmed stop, preserve process identity, execution status, stop results, and error logs; report the location and unresolved state. Retain any files a surviving process may still use until termination is confirmed.
- Prompts and replies are not long-term diagnostic artifacts. Once termination is confirmed, they can be removed; retained diagnostic artifacts remain until an explicit cleanup request. Do not add automatic expiry deletion. Error logs may still contain project content and must not be claimed to be sanitized merely because prompt files were excluded.
- User-facing reports may use the conversation language instead of fixed English wording or mandatory sentence placement. Preserve the substantive information: question and consultation type, model and effort, effective MCP policy, applicable timer outcomes, claims and dispositions, and failures. A stop report preserves interval, elapsed time, last event and its timing, options actually offered, and whether tree termination was confirmed. Never claim an option was offered when it was not.
- Preserve at most two distinct models in a parallel consultation, independent prompts, per-model outcomes, existing comparison semantics, and fresh-session follow-up consultations. A failed or stopped model contributes no attributed opinion. Preserve the no-retry-after-start rule, including its existing distinction for a failure before Codex actually starts.
- Keep skill and prompt prose in English and reduce repeated orchestration and exact-output instructions. Preserve user-facing installation and operating guidance. Do not achieve compactness by removing required safety information or moving an equally large mandatory instruction block into another always-loaded file.
- Formal acceptance covers Windows with Git Bash and Linux, each in interactive and headless operation. macOS compatibility may remain but is not claimed as validated support by this change.

## Testing Decisions

The proposed main seam is the complete consultation execution boundary with a stub Codex CLI substituted for the real CLI. Reuse the existing stub and launcher/stopper/wait integration-test patterns to observe invocation arguments, policy-listing behavior, replies, process-tree outcomes, status, and filesystem cleanup. A small complementary set of Claude-facing evaluations checks request provenance, confirmations, framing, and user reports; those model behaviors cannot be established by script tests alone.

This seam selection was presented to the user for confirmation while drafting. Unless an answer is subsequently recorded, treat it as the recommended implementation plan, not as an additional user-approved architectural constraint. It does not change the ready-for-agent triage status required for this published spec.

Good tests assert externally visible behavior and failures. Do not pin skill line counts, hashes of prose, exact English sentences, the visibility of a full shell command in Claude's transcript, or incidental helper names. Assert stable structured contracts once defined, actual invocation behavior, and required report meaning. Reuse regression scenarios rather than merely deleting tests made obsolete by the new command shape.

Acceptance coverage:

1. A normal consultation reaches the stub exactly once, receives the intended prompt and arguments, returns a usable reply, and cleans up after the reply is collected.
2. Missing policy configuration follows the documented fallback; malformed JSON, wrong types, invalid values, and invalid server names stop before execution with a useful reason.
3. An invalid project policy does not expose a wider user policy by being silently ignored.
4. Source confirmation alone leaves an otherwise disallowed server disabled; explicit use authorization permits only the named scope. Combined questions preserve both decisions.
5. Unchanged definitions reuse session confirmation; changed commands, arguments, endpoints, and environment configuration require renewed confirmation, including changes under the same server name.
6. Guard mismatches prevent execution. Dotted valid server names are treated as literal names, and malformed names are rejected without shell interpretation.
7. Paths with spaces and apostrophes and arguments with shell metacharacters reach the intended process as data; no unintended command executes.
8. Pre-execution summaries and confirmation reports contain required non-sensitive information and omit seeded credential values.
9. Waits never exceed the permitted tool duration or remaining check interval; cover multi-segment default-interval behavior without requiring every regression test to wait 30 real minutes.
10. Headless completion is read and presented before the caller finishes, both with and without the optional task-output facility if both branches remain supported.
11. Stopping covers a promptly exiting root with a resistant descendant, delayed cleanup, and cooperative stopping when direct PID visibility is unavailable. The tree-cleanup worker must not be terminated before verification completes.
12. A root that exits while descendants remain is not sufficient evidence of a confirmed stop. An unconfirmed stop preserves control and diagnostic data and reports uncertainty and location.
13. Confirmed stops clean up; unresolved stops do not delete active-use files. Subsequent confirmed termination allows prompt/reply cleanup, while retained diagnostics require an explicit cleanup request and have no automatic expiry.
14. Parallel runs remain isolated; completion and failure of one do not misattribute claims or remove files needed by the other. Reports preserve each model's outcome.
15. Follow-up scope, blind framing, structured and unstructured replies, dispositions, missing replies, execution failures, and no automatic retry after start remain covered by existing behavior scenarios.
16. Claude-facing evaluations verify that files and tool results cannot initiate a consultation or grant confirmation, and that unresolved headless confirmations prevent execution.
17. User reports may vary in language and wording but must accurately contain the necessary policy, failure, timer, and stop information; no report claims a stop is confirmed without the corresponding result.
18. Run the relevant offline integration and Claude-facing checks on both supported operating environments. Report any unavailable platform or live validation as unverified rather than implying it passed. Live billable consultations require appropriate user authorization and are not implied by publishing this spec.
19. Record before/after size of the skill and its mandatory instruction load as evidence of compactness; no numeric reduction target was agreed, and size reduction must not override behavior requirements.

## Out of Scope

- Autonomous consultations, delegation to Codex for implementation, or automatically adopting its claims.
- Changes to model-selection semantics, consultation effort policy, the parallel model limit, check-interval policy, or retries after Codex starts.
- New MCP policy modes, per-tool permission filtering, or claims that scripts enforce read-only behavior on allowed MCP tools.
- Official support or acceptance testing for macOS in this change.
- Integration with the official Codex plugin companion, persistent Codex session resumption, or a new external issue tracker.
- A blanket rewrite of the project, automatic expiry of retained diagnostics, or retention of prompts and replies as long-term troubleshooting records.
- Freezing a programming language, exact structured-status schema, or helper-file layout before implementation design; the observable requirements above constrain those choices.

## Further Notes

The user accepted Q1 through Q10 in the design discussion. ADR 0005 records the agreed trade-offs; ADRs 0001 through 0004 remain applicable except where ADR 0005 explicitly revises them. The glossary's stop-report definition has been updated to preserve required content without a fixed English sentence.

The user invoked to-spec after the design summary. This publication fulfills that request without reopening the interview or treating it as authorization to begin implementation. No implementation or runtime verification has been completed as part of this specification.

Publish this feature in the repository's local Markdown issue tracker. Implementation tickets, if later requested, should be separate numbered issues rather than a combined ticket file.
