# Script-owned execution and structured status

We will fix concrete defects and incrementally move deterministic consultation work into scripts: configuration parsing, MCP checks, command construction, and process lifecycle management. Claude retains question preparation, user interaction, and claim dispositions; scripts provide structured status and a pre-execution summary of the model, effort, working directory, and allowed MCP servers without exposing sensitive values. This revises ADR 0004's requirement to keep the complete command on Claude's Bash invocation line, while preserving ADR 0001's direct use of the Codex CLI rather than the official plugin companion.

Skill and prompt files remain in English for compactness. User-facing reports may follow the conversation language, preserving required information without fixed English sentences; tests should verify execution behavior, structured status, and required report information instead of exact prose. The initial supported environments are Windows with Git Bash and Linux, both interactive and headless; macOS is outside this acceptance scope.

Normal completion and confirmed stops permit run-directory cleanup. An unconfirmed stop retains the data needed for investigation and reports its location and unresolved state. Confirming a project MCP definition does not itself authorize use: source confirmation and use authorization remain separate decisions, although one explicit question may obtain both.

A missing policy configuration file permits the documented fallback. An existing policy file with invalid syntax or invalid values aborts the consultation and identifies the file and reason; it must not silently fall back to a potentially broader policy. Session confirmation is bound to the MCP definition that the user confirmed: an unchanged definition retains confirmation, while a changed definition requires renewed confirmation, with pending changes batched into one question where possible.

For an unconfirmed stop, retain process identity, execution status, stop results, and error logs for investigation. Prompts and replies are not retained as long-term diagnostic artifacts, but files potentially still used by a running process must remain until termination is confirmed. Report the retained location; cleanup of retained diagnostic artifacts requires an explicit user request, with no automatic expiry deletion.

Other consultation behavior remains unchanged unless explicitly covered above: model and effort selection, at most two distinct models in parallel, the default 30-minute check interval, no automatic retry after Codex starts, and a user request for each consultation. This is an incremental reliability and policy-handling change, not a redesign of those behaviors.

## Consequences

This moves complexity from model instructions into code that needs cross-platform tests and maintenance as Codex changes. It also requires revising existing command-shape and exact-wording tests. Retained error logs may still contain project content and must not be described as sanitized merely because prompts and replies are excluded. The user approved the ticket breakdown and subsequently invoked the implementation skill; implementation is authorized, while validation evidence is reported separately from these design decisions.

## Implementation notes

The execution boundary uses Python 3.11+ for standard-library JSON and TOML parsing, with Bash retaining process-tree management. This adds an explicit Python prerequisite rather than implementing a partial TOML parser. Arguments cross the Windows/Git Bash boundary as NUL-delimited data, avoiding re-interpretation of embedded quotes.

An isolated local Codex CLI probe showed that quoting a dotted name inside a command-line override path still splits the name. Disabled servers therefore use literal keys in a root MCP inline table, changing only their enabled flag so an HTTP transport is not merged with a conflicting stdio command. The same form handles ordinary names without changing transport; every resulting policy still passes the effective MCP guard before execution.

A single `wait` call blocks for at most 60 seconds so that every call finishes within the Bash tool's default 120-second timeout, and the skill needs no timeout instruction for it. Raising that bound past the default timeout requires restoring a timeout instruction in `SKILL.md`.
