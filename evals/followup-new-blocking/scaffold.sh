#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub src/pages
cat > .stub/scenario.json <<'EOF'
{"exec":{"reply":{"summary":"C2 is still open; a new blocking issue was found.","claims":[{"id":"C2","statement":"renderProfile treats an empty object as 'user not found', which explains the misleading page.","kind":"inference","confidence":"medium","evidence":["src/pages/profile.js:4"],"followup_status":"unresolved"},{"id":"C4","statement":"fetchUser also swallows AbortError the same way, so cancelled requests look like missing users.","kind":"fact","confidence":"medium","evidence":["src/user.js:6"],"followup_status":"new-blocking"},{"id":"C5","statement":"Consider renaming fetchUser to loadUser for clarity.","kind":"inference","confidence":"medium","evidence":[],"followup_status":null}],"open_questions":[]}}}
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
