#!/usr/bin/env bash
set -eu
mkdir -p .stub .codex .claude
printf '%s\n' '{}' > .stub/scenario.json
printf '%s\n' '{"mcp_policy":"allowlist","mcp_allow":[]}' > .claude/ask-codex.local.json
printf '%s\n' '[mcp_servers.repo_helper]' 'command="project-helper"' > .codex/config.toml
printf '%s\n' 'not-executed' > .stub/exec.sentinel
