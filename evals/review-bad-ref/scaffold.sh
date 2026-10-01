#!/usr/bin/env bash
# A git repository on main with one uncommitted change, so a review that ignored the rejected scope
# and fell back to the working tree would reach Codex (and leave a stub sentinel).
set -euo pipefail
g() { git -c user.name=eval -c user.email=eval@example.invalid -c commit.gpgsign=false -c core.autocrlf=false -c core.hooksPath=/dev/null "$@"; }
g init -q
g symbolic-ref HEAD refs/heads/main
# The stub's records and the sandbox's protected placeholder files are not part of the change.
mkdir -p .git/info
cat >> .git/info/exclude <<'EOF'
/.*
/bunfig.toml
/lefthook.yml
/lefthook.yaml
/gradle-wrapper.properties
/maven-wrapper.properties
/pyrightconfig.json
EOF
mkdir -p .stub src
cat > .stub/scenario.json <<'EOF'
{
  "exec": {
    "reply": {
      "summary": "fetchUser now returns null for every failure.",
      "claims": [
        {"id": "C1", "statement": "fetchUser returns null for every failure, so callers cannot tell a timeout from an HTTP error.", "kind": "fact", "confidence": "high", "evidence": ["src/user.js:7"], "followup_status": null}
      ],
      "open_questions": []
    }
  }
}
EOF
cat > src/user.js <<'EOF'
export async function fetchUser(api, id) {
  return api.get(`/users/${id}`, { timeout: 2000 });
}
EOF
g add src/user.js
g commit -q -m "User service"
cat > src/user.js <<'EOF'
export async function fetchUser(api, id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    console.error("fetchUser failed", err);
  }
  return null;
}
EOF
