#!/usr/bin/env bash
# The early-consensus project; round 1 is valid with the disputed shared Redis (C3); round 2 is mode fail.
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
cat > .stub/scenario.json <<'EOF'
{
  "exec": {
    "sequence": [
      {"reply": {"summary": "Login has no throttling and tells an attacker which usernames exist; failure counters should be shared across instances.", "points": [
        {"id":"C1","statement":"Count failed login attempts per username and per IP address in a sliding window, and answer 429 once a key has more than 5 failures in 15 minutes.","reason":"login() answers every wrong password immediately, so an attacker can guess passwords at full speed.","evidence":["src/login.js:6"],"kind":"inference","confidence":"high","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C2","statement":"Return the same error text for an unknown user and for a wrong password.","reason":"Line 5 says unknown user and line 6 says wrong password, which tells an attacker which usernames exist.","evidence":["src/login.js:5","src/login.js:6"],"kind":"fact","confidence":"high","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C3","statement":"Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.","reason":"Without a shared store an attacker can spread attempts across instances and never reach the limit.","evidence":["src/login.js:3"],"kind":"inference","confidence":"medium","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false}
      ], "open_questions": ["How many login attempts per minute does the service expect from honest users?"]}},
      {"mode": "fail"}
    ]
  }
}
EOF
