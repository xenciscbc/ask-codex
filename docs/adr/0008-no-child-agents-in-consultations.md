# No child agents in consultations

Every consultation — `ask`, `review` and `discuss` all launch Codex through `consult.py run()` — starts `codex exec` with child agents switched off: the constant pairs `-c agents.enabled=false` and `-c features.multi_agent_v2.enabled=false`, next to `--disable apps`. They are part of the command line, not of the MCP policy overrides or the prepared summary, so no plan, policy file or project setting can drop them.

## Why

Codex's multi-agent tools are on by default (MultiAgentV2 for most current models). A child agent's role file sets its own `sandbox_mode`, model and `mcp_servers`, and the role's sandbox overrides the parent's. On 2026-10-06, under the exact consultation command line (`codex exec -s read-only …`, codex-cli 0.159.3), Codex spawned an `executor` child from a user-level role file with `sandbox_mode = "workspace-write"` (codex-feather installs four such roles), and the child wrote a file in the project. A child can also bring MCP servers the preflight MCP guard never listed, and runs on its role's model, not the consultation's. Plugin versions 1.0.0–1.3.1 were affected.

Live probes (`.scratch/subagent-boundary/`):

- `--disable multi_agent`: did not stop the spawn (the model catalog selects MultiAgentV2).
- `-c agents.enabled=false`: removed the spawn tools under the default configuration, for a v2 model (gpt-5.6-sol) and a v1 model (gpt-5.6-luna), with `spawn_agents_on_csv` absent too; ordinary and document-analysis consultations completed normally with no delegation noise.
- But an explicitly enabled `multi_agent_v2` feature — on the command line, or in a trusted project's `.codex/config.toml` — brought the `collaboration` tools back and a child wrote again. An untrusted project's config was ignored. Hence the second pair: command-line `-c` takes precedence over the user and project config files.

## Considered options

- **Children allowed for read-only side work, with the analysis and answer kept by the main agent** (the user's preferred direction): not achievable safely. Codex has no per-invocation role allowlist, a role file's sandbox overrides the parent's, and generic children — the only ones that would inherit the consultation's model — fail under `--ephemeral` ("no rollout found"). Revisit when Codex offers an enforced ceiling on a child's sandbox.
- **`--disable multi_agent`**: ineffective for MultiAgentV2 (probe; openai/codex#50880).
- **A hook that denies spawns**: spawn calls do not reach PreToolUse (openai/codex#49736, #36519).
- **`max_depth = 0`** or tuning the `multi_agent_v2` table: not enforced / only partial (openai/codex#46704, #50880).
- **`--ignore-user-config`**: breaks the Windows sandbox setup (ADR 0003).
- **A prompt sentence telling Codex no children are available**: no security value once the tools are absent; not added.

## Consequences and honest limits

- Verified on codex-cli 0.159.3 (Windows) for the default configuration, a v1 and a v2 model, command-line feature enabling, and a trusted project's config enabling agents and MultiAgentV2. Not verified: the user's own config file enabling them (needs an edit to the user's Codex configuration; precedence documentation says the command line wins), older CLIs (where `[agents]` may be a role map), and WSL.
- The `codex exec --json` event stream of 0.159.3 shows no child activity, so a consultation cannot itself detect a child; this relies on the switches.
- Other tools a read-only consultation still sees — `notes.write_file`/`append_to_file`, `create_goal`/`update_goal` (Codex's own stores) and `web.run` — are separate follow-ups, not covered here.
- This deliberately changes the consultation command line that ADR 0007 described `discussion` as leaving unchanged.
