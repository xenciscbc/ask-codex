#!/usr/bin/env bash
# The discuss-user-call project, but Codex does NOT mark the lockout-screen choice in round 1 (so Claude's own user-call
# mark on it is a one-sided proposal). Round 1 raises C1 (count), C2 (one error text) and the disputed shared-Redis C3.
# Round 2 answers every Claude point L1-L30 with maintain + user_call false (Codex holds the point has a right answer)
# and maintains C3. Round 3 maintains C3 only, so a lapsed proposal line would show in round 3.
set -euo pipefail
mkdir -p .stub src docs
cat > README.md <<'EOF'
# Login service
A small Node service. src/login.js checks a username and a password.
Read docs/constraints.md and docs/decisions.md before designing anything for it.
EOF
cat > docs/constraints.md <<'EOF'
# Constraints
- The service runs as ONE process on ONE host.
- No Redis, database server or other external store may be added.
- State may live in process memory only; losing it on restart is fine.
EOF
cat > docs/decisions.md <<'EOF'
# Who decides what
- Engineering decides how failed logins are counted, limited and stored.
- What a locked-out user SEES (a CAPTCHA, or a wait message with the time left) is the product owner's decision, a matter of taste and brand, not of engineering. Engineering only implements the choice the product owner makes.
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
      {"reply": {"summary": "Login needs throttling that counts failed attempts, one error text for both failures, and counters that fit the single-process constraint.", "points": [
        {"id":"C1","statement":"Count failed login attempts per username and lock the account for a while after repeated failures.","reason":"login() answers every wrong password immediately and keeps no count, so nothing slows down guessing against one account.","evidence":["src/login.js:6"],"kind":"fact","confidence":"high","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C2","statement":"Return the same error text for an unknown user and for a wrong password.","reason":"The two different texts tell an attacker which usernames exist.","evidence":["src/login.js:5"],"kind":"fact","confidence":"high","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"C3","statement":"Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.","reason":"Without a shared store an attacker can spread attempts across instances and never reach the limit.","evidence":["src/login.js:3"],"kind":"inference","confidence":"medium","stance":null,"revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false}
      ], "open_questions": []}},
      {"reply": {"summary": "I keep my own positions; only the shared store for the counters matters to my conclusion.", "points": [
        {"id":"C3","statement":"Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.","reason":"The constraint only describes today's single host; a second instance added later would silently lose the limit, so a shared store is the safe choice.","evidence":["src/login.js:3"],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L1","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L2","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L3","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L4","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L5","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L6","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L7","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L8","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L9","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L10","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L11","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L12","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L13","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L14","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L15","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L16","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L17","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L18","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L19","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L20","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L21","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L22","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L23","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L24","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L25","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L26","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L27","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L28","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L29","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false},
        {"id":"L30","statement":"Claude's point, as stated in the context.","reason":"I keep my own position; this point has a right answer, so it is not a user call.","evidence":[],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false}
      ], "open_questions": []}},
      {"reply": {"summary": "Only the shared store for the counters is still disputed.", "points": [
        {"id":"C3","statement":"Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.","reason":"The constraint only describes today's single host; a second instance added later would silently lose the limit, so a shared store is the safe choice.","evidence":["src/login.js:3"],"kind":"inference","confidence":"medium","stance":"maintain","revised_statement":null,"user_call":false,"user_call_reason":null,"new_blocking":false,"reopen":false}
      ], "open_questions": []}}
    ]
  }
}
EOF
