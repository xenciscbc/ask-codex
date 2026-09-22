# Script-owned consultation validation

Date: 2026-09-22. Baseline: `9da757caa313bb518b0de1ebfea29457876aabce`.

## Implemented boundary

The main agent integrated policy/confirmation handling, safe argv transport, guarded execution, bounded waits, parallel failure isolation, schema-aware collection and cleanup. The lifecycle executor implemented process identities, cooperative shutdown and durable wrapper receipts. The documentation executor updated both READMEs. Two read-only analysts reviewed standards and specification compliance; their process-group, partial-launch, completion-accounting and reporting findings were corrected and regression-tested.

Named child configurations were executor `gpt-5.6-sol` / `medium` and analyst `gpt-5.6-sol` / `high`, supplied through native dispatch according to repository guidance. Runtime backend model execution identity is not independently attested. No child was authorized to delegate. Reviewers wrote no source files; the main agent checked the resulting change set.

The sections below record the initial implementation validation. The final section records the subsequent review fixes.

## Public CLI integration

`python evals/_harness/consultation_test.py`: **22 tests passed on Windows**, Python 3.11, Git Bash. The same suite passed **22 tests on Ubuntu WSL**, Python 3.12.3. The final full reruns, after lifecycle and cancellation-accounting fixes, passed in 76.848s and 43.188s respectively.

These use the real public Python CLI, Bash launch/stop scripts and local stub Codex. They do not call a real Codex service. Coverage includes spaces/apostrophes/metacharacters, unchanged and changed MCP definitions, strict invalid configuration, layered policies and both policy modes, dotted names, schema fallback, repeated interval decisions with a virtual wall clock, real process completion, mixed parallel outcomes, partial launch failure, lost supervisor receipts, absent stop verification, and cleanup refusal for unresolved stops. Stop tests accept unconfirmed only where the returned evidence supports it; lifecycle-specific tests separately exercise confirmed termination.

## Lifecycle and existing regressions

The focused lifecycle suite passed **27 assertions on elevated Windows Git Bash** and **30 on Linux**. Linux includes normal root exit with a TERM-resistant child; Windows tests distinguish actual verification capability from platform name. Managed Windows sandbox runs also exercised conservative unconfirmed-stop behavior when CIM enumeration was unavailable.

All 18 `evals/_harness/*.test.mjs` files pass: the full inventory was run, then the two affected lifecycle files were rerun after fixes. The final elevated Windows legacy lifecycle result is 104 passed, 0 failed; the focused final results are listed above. Source-prose/hash pins in historical fixtures were removed in favor of the current public CLI and semantic Claude cases; the historical grader fixtures remain tested. CRLF-sensitive fixture parsing was normalized. Python compilation and Bash syntax checks passed; this repository has no configured static typechecker.

## Claude-facing checks

Real Claude Code 2.1.278 ran headlessly in Ubuntu WSL with the stub Codex:

| Case | Runs | Result | Local report |
|---|---:|---|---|
| script-consultation | 1 | score 1.00, 3/3 graders | `evals/results/2026-09-22T05-00-44-732Z/report.html` |
| script-confirmation | 1 | score 1.00, 2/2 graders | `evals/results/2026-09-22T05-03-32-756Z/report.html` |

The first verifies invocation, guarded execution and semantic report content. The second verifies pending project-definition confirmation and no execution. These are narrow samples, not proof of all Claude behavior; later lifecycle/recovery refinements were covered by offline regressions rather than repeating the billable Claude runs.

## Real CLI syntax probe

An isolated `codex-cli 0.154.0` MCP-listing probe confirmed that quoted dotted override paths are still split by its CLI path parser. A root inline table with literal server keys and only `enabled=false` disables the intended servers while retaining HTTP/stdio transport. Adding a replacement stdio command to HTTP definitions can fail parsing. The implementation uses the root-table form for all disabled names and verifies the effective listing afterward. This probe did not start a consultation or connect to an MCP service.

## Instruction size

UTF-8 bytes, normalized to LF to avoid Windows checkout line-ending effects. The mandatory path comprises the ask skill, consultation prompt and selected framing file; scripts and schema are executable/data inputs, not additional required agent reading.

| Required instruction path | Before bytes | After bytes |
|---|---:|---:|
| Ask skill alone | 45,281 | 14,800 |
| Skill + prompt + diagnosis | 47,643 | 17,162 |
| Skill + prompt + follow-up | 48,147 | 17,666 |
| Skill + prompt + second opinion | 47,636 | 17,155 |
| Skill + prompt + targeted check | 47,596 | 17,115 |
| Skill + prompt + technical question | 47,536 | 17,055 |

English is retained. The skill alone shrank about 67%; full required consultation instructions shrank about 63–64%. No replacement always-loaded reference document was added. This measures bytes, not tokens or behavior quality.

## Remaining acceptance gaps

- Interactive Claude flows on both supported platforms remain unverified.
- Windows real-Claude headless operation remains unverified; the available plugin eval harness grants shell tools on Linux/WSL, not native Windows.
- Full consultations with the real Codex service were not run. The specification does not authorize live billable Codex consultations merely by publication.
- Broad follow-up/provenance, combined interactive confirmation and paired-report Claude evaluations were not all rerun. Historical fixture tests remain regression tests for those fixture graders, not evidence that the rewritten skill passed every historical Claude case.
- Windows process management permissions can prevent complete descendant enumeration; this must remain an unresolved stop with retained diagnostics, not successful termination.
- macOS is outside the accepted scope. Python 3.11+ is a new documented prerequisite.

The implementation tickets are marked needs-triage for acceptance review, with acceptance checklists left open where full live coverage is absent. The parent specification is unchanged.

## P1 review fixes

Review baseline: `cc1645e`. Fixed the two reproduced P1 findings:

- POSIX process discovery now combines recursive PPID ancestry, process-group membership and captured identity-matching subtree roots. The new detached-session regression failed before the fix because a positively confirmed stop left the child alive. After the fix, the lifecycle suite passes 34 assertions on Ubuntu WSL and 27 on elevated Windows Git Bash. A child that fully detaches and is reparented before any snapshot remains a process-observation limitation.
- CLI output uses ASCII-safe JSON and flushes the full reply before deleting run files. A CP950 Unicode regression and a closed-pipe retry regression both failed before their respective fixes and pass afterward. A third test verifies that cleanup failure preserves the delivered reply on stdout and reports the retained location separately on stderr. Collection retry uses the same run and does not execute Codex again.

The complete public CLI suite passes 25 tests on Windows (93.028s) and 25 on Ubuntu WSL (46.948s), using only stub Codex. Two read-only analysts reviewed the separate process-lifecycle and reply-delivery fixes with no actionable findings; the main agent integrated the changes and checked the diff. Named role settings remain those documented above; actual backend execution identity remains unconfirmed.

The final ask skill is 15,012 UTF-8 bytes normalized to LF; the earlier size table records the initial implementation. No real Claude or live Codex consultation was rerun for these fixes. The remaining acceptance gaps and ticket statuses above are unchanged.

All 18 Node offline test files passed again after the P1 fixes; see `review-fix-offline-summary.txt`. The full run includes the 27 Windows lifecycle assertions. Python compilation, Bash syntax checks and `git diff --check` also passed.
