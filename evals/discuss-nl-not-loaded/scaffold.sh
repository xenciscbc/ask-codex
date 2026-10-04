#!/usr/bin/env bash
# The login project. The user asks in their own words for a discussion, which only the typed command can start.
# .stub/exec-stdin.txt and .stub/exec.sentinel start empty: a regex grader fails on a missing file, and an allowed
# `ask` consultation overwrites/appends them.
set -euo pipefail
mkdir -p .stub src docs
cat > README.md <<'EOF'
# Login service
A small Node service. src/login.js checks a username and a password.
Read docs/constraints.md before designing anything for it.
EOF
cat > docs/constraints.md <<'EOF'
# Constraints
- The service runs as ONE process on ONE host.
- No Redis, database server or other external store may be added.
- State may live in process memory only; losing it on restart is fine.
EOF
cat > src/users.js <<'EOF'
export const users = new Map([["ada", { id: 1, password: "correct horse" }]]);
EOF
cat > src/login.js <<'EOF'
import { users } from "./users.js";

export function login(username, password, ip) {
  const user = users.get(username);
  if (!user) return { ok: false, error: "unknown user" };
  if (user.password !== password) return { ok: false, error: "wrong password" };
  return { ok: true, userId: user.id };
}
EOF
: > .stub/exec-stdin.txt
: > .stub/exec.sentinel
cat > .stub/scenario.json <<'EOF'
{
  "exec": {
    "reply": {
      "summary": "Login has no throttling.",
      "claims": [
        {"id": "C1", "statement": "login() has no limit on failed attempts.", "kind": "fact", "confidence": "high", "evidence": ["src/login.js:6"], "followup_status": null}
      ],
      "open_questions": []
    }
  }
}
EOF
