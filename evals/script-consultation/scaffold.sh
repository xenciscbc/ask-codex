#!/usr/bin/env bash
set -eu
mkdir -p .stub .claude src
printf '%s\n' '{}' > .stub/scenario.json
printf '%s\n' '{"mcp_policy":"allowlist","mcp_allow":[]}' > .claude/ask-codex.local.json
cat > src/user.js <<'EOF'
export async function fetchUser(id) {
  for (let attempt = 0; attempt < 3; attempt++) {
    try { return await api.get(`/users/${id}`); }
    catch (error) { if (error.name !== 'TimeoutError') throw error; }
  }
  return {};
}
EOF
