#!/usr/bin/env bash
# A login project where one design choice (what a locked-out user sees) is plainly the product owner's decision.
# Round 1: Codex raises that choice as C2 with user_call true, plus the same-error-text point and a shared-Redis point
# that contradicts the constraints file. Round 2 maintains the Redis point (C3) and answers nothing about C2.
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
      {
        "reply": {
          "summary": "Login needs throttling that works with the single-process constraint, one error text, and a product decision about the lockout screen.",
          "points": [
            {
              "id": "C1",
              "statement": "Return the same error text for an unknown user and for a wrong password.",
              "reason": "Line 5 says unknown user and line 6 says wrong password, which tells an attacker which usernames exist.",
              "evidence": [
                "src/login.js:5",
                "src/login.js:6"
              ],
              "kind": "fact",
              "confidence": "high",
              "stance": null,
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "evidence": [
                "docs/decisions.md:3"
              ],
              "kind": "inference",
              "confidence": "medium",
              "stance": null,
              "revised_statement": null,
              "user_call": true,
              "user_call_reason": "docs/decisions.md says what a locked-out user sees (a CAPTCHA or a wait message) is the product owner's decision, a preference and not a question of correctness.",
              "new_blocking": false,
              "reopen": false,
              "id": "C2",
              "statement": "When an account is locked out after repeated failures, show the user a wait message with the time left instead of a CAPTCHA.",
              "reason": "A wait message gives an automated attacker nothing to solve and needs no third-party service, so it is the simpler lockout experience. Which of the two the user sees is a matter of product preference, so I flag it as a user call."
            },
            {
              "id": "C3",
              "statement": "Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.",
              "reason": "Without a shared store an attacker can spread attempts across instances and never reach the limit.",
              "evidence": [
                "src/login.js:3"
              ],
              "kind": "inference",
              "confidence": "medium",
              "stance": null,
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            }
          ],
          "open_questions": [
            "How many login attempts per minute does the service expect from honest users?"
          ]
        }
      },
      {
        "reply": {
          "summary": "Only the shared store for the counters is still disputed.",
          "points": [
            {
              "id": "C3",
              "statement": "Keep the failure counters in a shared Redis instance so that every server instance sees the same counts.",
              "reason": "The constraint only describes today's single host; a second instance added later would silently lose the limit, so a shared store is the safe choice.",
              "evidence": [
                "src/login.js:3"
              ],
              "kind": "inference",
              "confidence": "medium",
              "stance": "maintain",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L1",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L2",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L3",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L4",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L5",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L6",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L7",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L8",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L9",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L10",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L11",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L12",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L13",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L14",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L15",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L16",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L17",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L18",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L19",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L20",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L21",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L22",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L23",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L24",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L25",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L26",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L27",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L28",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L29",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            },
            {
              "id": "L30",
              "statement": "Claude's point, as stated in the context.",
              "reason": "Checked against the code and the constraints; I accept it as stated.",
              "evidence": [],
              "kind": "inference",
              "confidence": "medium",
              "stance": "accept",
              "revised_statement": null,
              "user_call": false,
              "user_call_reason": null,
              "new_blocking": false,
              "reopen": false
            }
          ],
          "open_questions": []
        }
      }
    ]
  }
}
EOF
