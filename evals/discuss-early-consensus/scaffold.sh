#!/usr/bin/env bash
# A one-process login service with a constraints file. The stub's round 1 raises C1-C3, where C3 (a shared Redis)
# contradicts docs/constraints.md, so Claude reliably disputes it and it is carried as a contested point. Round 2
# accepts everything (ids L1-L30 cover whatever points Claude raised; extra ids are ignored by the skill).
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
      {"reply": {"summary": "Claude's objections hold; nothing is left in dispute.", "points": [
        {"id":"C1","statement":"Count failed login attempts per username and per IP address in a sliding window.","reason":"Agreed; nothing new to add.","evidence":[],"kind":"inference","confidence":"high","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C2","statement":"Return the same error text for an unknown user and for a wrong password.","reason":"Agreed; nothing new to add.","evidence":[],"kind":"fact","confidence":"high","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C3","statement":"Keep the failure counters in process memory.","reason":"docs/constraints.md:2 says the service runs as one process and line 3 forbids Redis, so in-process counters are enough; I accept Claude's objection.","evidence":["docs/constraints.md:2","docs/constraints.md:3"],"kind":"fact","confidence":"high","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L1","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L2","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L3","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L4","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L5","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L6","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L7","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L8","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L9","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L10","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L11","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L12","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L13","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L14","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L15","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L16","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L17","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L18","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L19","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L20","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L21","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L22","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L23","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L24","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L25","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L26","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L27","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L28","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L29","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L30","statement":"Claude's point, as stated in the context.","reason":"Checked against the code and the constraints; I accept it as stated.","evidence":[],"kind":"inference","confidence":"medium","stance":"accept","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false}
      ], "open_questions": []}}
    ]
  }
}
EOF
