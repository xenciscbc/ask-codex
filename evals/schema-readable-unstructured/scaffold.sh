#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub src
cat > .stub/scenario.json <<'EOF'
{"exec":{"mode":"schema-violation"}}
EOF
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
