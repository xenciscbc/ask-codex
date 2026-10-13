# No escalation and no execpolicy rules in consultations

Every consultation — `ask`, `review` and `discuss` all launch Codex through `consult.py run()` — starts `codex exec` with `-c approval_policy="never"`, `-c approvals_reviewer="user"` and `--ignore-rules`, next to the ADR 0008 pairs. They are constants of the command line, not part of the MCP policy overrides or the prepared summary, so no plan, policy file or project setting can drop them.

## Why

`codex exec` refuses every approval request in headless mode by forcing `approval_policy = Never` — unless the configured `approvals_reviewer` resolves to `auto_review`, in which case it rebuilds the configuration without that override (`codex-rs/exec/src/lib.rs`, codex-cli 0.159.3) and approval requests go to Codex's automatic reviewer. The user's own config set `approvals_reviewer = "auto_review"`. On 2026-10-13, under the 1.3.2 consultation command line (`codex exec -s read-only …`, same overrides and switches, without `--output-schema` and with a different `-o` path), a probe consultation asked to write a file: the sandbox denied it, Codex requested escalation, the reviewer approved, and the command ran outside the sandbox and wrote the file (probe p9, `.scratch/approval-boundary/evidence/source/`). With `-c approval_policy="never"` added, Codex could not request escalation and nothing was written (p9b). A trusted project's `.codex/config.toml` can set both keys, and the project-layer denylist does not cover them; the command line (session flags) takes precedence over user, profile and project layers. Plugin versions 1.0.0–1.3.2 were affected.

`approvals_reviewer = "user"` is a second layer: with it, exec keeps its own headless Never and rejects any approval request that still arrives. It was not probed on its own.

An `allow` rule in an execpolicy `.rules` file lets a matching command skip approval and run outside the sandbox, independent of the approval policy (`codex-rs/core/src/exec_policy.rs`, `tools/sandboxing.rs`). Users accumulate such rules through "don't ask again" (this machine had 174), and a trusted project can ship its own in `.codex/rules/`. This was inferred from the source and deliberately not probed (user decision); `--ignore-rules` stops consultations loading user and project `.rules` files. The adversarial review showed a trusted project's `forbidden` rules matching the commands run were not applied under the consultation command line.

Live acceptance with all three on codex-cli 0.159.3 (Windows, elevated sandbox), `.scratch/approval-boundary/evidence/live-run-log.md`: the user's config with `auto_review`; a trusted project setting `auto_review` with `on-request`, and one with the granular policy with all five prompt kinds enabled (table recorded in the run log), both also setting `sandbox_mode = "workspace-write"`; an untrusted project with the same config (shown not loaded); and an ordinary consultation. No escalation was requested, nothing was written, `-s read-only` held against the project's `sandbox_mode`, and the user's Codex config and rules were unchanged. The project configs also set `default_permissions`, which Codex ignores by design when `sandbox_mode` or `-s` is present, so it was not tested on its own.

## Considered options

- **A prompt sentence telling Codex not to escalate**: no security value; the probes show the model asks when allowed.
- **Pinning only `approval_policy`**: sufficient in the probes, but the reviewer pin costs nothing and keeps exec's own refusal path.
- **`--dangerously-bypass-approvals-and-sandbox`**, which keeps exec's headless Never: it also drops the sandbox; rejected.
- **Probing the `.rules` bypass before pinning `--ignore-rules`**: not done by user decision; the flag is pinned on the source reading.

## Consequences and honest limits

- Administrator layers are not defended: a legacy managed config (precedence above session flags) or a `requirements.toml` that disallows `never` can override or replace the pinned values; Codex only warns. Codex reported another configuration warning (enabled under-development features) as a `type:"error"` item in the `--json` event stream rather than on stderr in the adversarial run; the requirements warning itself was never produced.
- `--ignore-rules` covers user and project rules only (its help text: "user or project execpolicy `.rules` files"). System-level rules (under `%ProgramData%\OpenAI\Codex\` on Windows), requirements `prefix_rules` and rules a plugin layer brings are presumably still loaded — from a static reading of the codex-cli 0.159.3 binary during the adversarial review; not probed.
- In every live run the model declined to send an escalation request once told the policy is `never`, so Codex's runtime refusal of such a request was never exercised live; it is evidenced only by the refusal strings in the binary. A permissions request in the adversarial run was reported by the model as granting nothing; that result is not visible in the `--json` event stream. The user accepted claim C1 without a passing adversarial review on these two gaps (2026-10-13).
- Approval-requiring MCP tools on servers the user allows are now refused in consultations instead of being reviewed.
- The user's own `forbidden` and `prompt` execpolicy rules do not apply in consultations; commands still run inside the read-only sandbox.
- `--ignore-rules` requires a codex-cli that has the flag (0.159.3 does); an older CLI is expected to fail with an unknown-argument error instead of running without it (not tested).
- The read-only sandbox does not block loopback on Windows: shell commands reach every localhost service, and Codex configuration cannot prevent it (a network-proxy profile blocks proxied requests, but a command that bypasses the proxy still connects). Documented in the README, not solved.
- Not verified: older CLIs, Linux, WSL, macOS; the reviewer pin alone; the `.rules` bypass itself; a profile layer (consultations never pass `--profile`, and a project cannot select one).
- This changes the consultation command line again, as ADR 0008 did.
