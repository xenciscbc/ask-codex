#!/usr/bin/env bash
set -euo pipefail
mkdir -p src .codex .stub
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
cat > .codex/config.toml <<'EOF'
[mcp_servers.repo_helper]
command = "repo-helper.exe"
args = ["--serve"]
EOF
echo '{}' > .stub/scenario.json
