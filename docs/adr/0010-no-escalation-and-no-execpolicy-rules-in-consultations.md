# No escalation and no execpolicy rules in consultations

Every consultation — `ask`, `review` and `discuss` all launch Codex through `consult.py run()` — starts `codex exec` with `-c approval_policy="never"`, `-c approvals_reviewer="user"` and `--ignore-rules`, next to the ADR 0008 pairs. They are constants of the command line, not part of the MCP policy overrides or the prepared summary, so no plan, policy file or project setting can drop them.

## Why

`codex exec` refuses every approval request in headless mode by forcing `approval_policy = Never` — unless the configured `approvals_reviewer` resolves to `auto_review`, in which case it rebuilds the configuration without that override (`codex-rs/exec/src/lib.rs`, codex-cli 0.159.3) and approval requests go to Codex's automatic reviewer. The user's own config set `approvals_reviewer = "auto_review"`. On 2026-10-13, under the exact consultation command line (`codex exec -s read-only …`), a probe consultation asked to write a file: the sandbox denied it, Codex requested escalation, the reviewer approved, and the command ran outside the sandbox and wrote the file (probe p9, `.scratch/exercise-skills/probe-results.md`). With `-c approval_policy="never"` added, Codex could not request escalation and nothing was written (p9b). A trusted project's `.codex/config.toml` can set both keys, and the project-layer denylist does not cover them; the command line (session flags) takes precedence over user, profile and project layers. Plugin versions 1.0.0–1.3.2 were affected.

`approvals_reviewer = "user"` is a second layer: with it, exec keeps its own headless Never and rejects any approval request that still arrives. It was not probed on its own.

An `allow` rule in an execpolicy `.rules` file lets a matching command skip approval and run outside the sandbox, independent of the approval policy (`codex-rs/core/src/exec_policy.rs`, `tools/sandboxing.rs`). Users accumulate such rules through "don't ask again" (this machine had 174), and a trusted project can ship its own in `.codex/rules/`. This was inferred from the source and deliberately not probed (user decision); `--ignore-rules` stops consultations loading any `.rules` file.

Live acceptance with all three on codex-cli 0.159.3 (Windows, elevated sandbox), `.scratch/approval-boundary/`: the user's config with `auto_review`; a trusted project setting `auto_review` with `on-request`, and with the granular policy with every prompt enabled, both also setting `sandbox_mode = "workspace-write"` and `default_permissions`; an untrusted project with the same config (shown not loaded); and an ordinary consultation. No escalation was requested, nothing was written, `-s read-only` held, and the user's Codex config and rules were unchanged.

## Considered options

- **A prompt sentence telling Codex not to escalate**: no security value; the probes show the model asks when allowed.
- **Pinning only `approval_policy`**: sufficient in the probes, but the reviewer pin costs nothing and keeps exec's own refusal path.
- **`--dangerously-bypass-approvals-and-sandbox`**, which keeps exec's headless Never: it also drops the sandbox; rejected.
- **Probing the `.rules` bypass before pinning `--ignore-rules`**: not done by user decision; the flag is pinned on the source reading.

## Consequences and honest limits

- Administrator layers are not defended: a legacy managed config (precedence above session flags) or a `requirements.toml` that disallows `never` can override or replace the pinned values; Codex only warns.
- Approval-requiring MCP tools on servers the user allows are now refused in consultations instead of being reviewed.
- The user's own `forbidden` and `prompt` execpolicy rules do not apply in consultations; commands still run inside the read-only sandbox.
- `--ignore-rules` requires a codex-cli that has the flag (0.159.3 does).
- The read-only sandbox does not block loopback on Windows: shell commands reach every localhost service, and Codex configuration (including the network proxy) cannot prevent it. Documented in the README, not solved.
- Not verified: older CLIs, WSL, macOS; the reviewer pin alone; the `.rules` bypass itself.
- This changes the consultation command line again, as ADR 0008 did.
