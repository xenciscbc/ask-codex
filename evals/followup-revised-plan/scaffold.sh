#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub src/pages
cat > .stub/scenario.json <<'EOF'
{"exec":{"reply":{"summary":"P-BETA v2 addresses both earlier concerns.","claims":[{"id":"C1","statement":"P-BETA has no fallback when the cache is empty, so first-time visitors still see 'user not found'.","kind":"inference","confidence":"medium","evidence":[],"followup_status":"resolved"},{"id":"C2","statement":"P-BETA hides timeouts from monitoring, because the cached path never reports the failure.","kind":"fact","confidence":"medium","evidence":[],"followup_status":"resolved"}],"open_questions":[]}}}
EOF
cat > src/user.js <<'EOF'
export async function fetchUser(id, { retries = 2 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await api.get(`/users/${id}`, { timeout: 2000 });
    } catch (err) {
      if (err.name === "TimeoutError") {
        continue;
      }
      throw err;
    }
  }
  return {};
}
EOF
cat > src/pages/profile.js <<'EOF'
import { fetchUser } from "../user.js";
export async function renderProfile(id) {
  const user = await fetchUser(id);
  if (!user.id) return "user not found";
  return `Hello ${user.name}`;
}
EOF
