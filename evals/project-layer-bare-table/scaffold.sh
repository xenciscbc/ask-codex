#!/usr/bin/env bash
set -euo pipefail
mkdir -p src .stub
cat > src/user.js <<'EOF'
export async function fetchUser(id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
}
EOF
cat > .stub/scenario.json <<'EOF'
{}
EOF
mkdir -p '.codex'
cat > '.codex/config.toml' <<'EOF'
[mcp_servers]
repo_helper.command = "repo-helper.exe"
EOF
