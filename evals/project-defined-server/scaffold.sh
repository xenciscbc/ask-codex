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
echo '{"project_extra": [{"name": "repo_tool", "command": "repo-tool.exe"}]}' > .stub/scenario.json
