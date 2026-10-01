#!/usr/bin/env bash
# A git repository on branch feature/retry, which branched off main and added src/retry.js and
# changed src/user.js. main moved on afterwards (README.md only), so README.md is in `git diff main`
# but not in the branch's own change (`main...HEAD`). Clean working tree.
# The stub's canned claims cite the branch's files at these lines.
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
      "summary": "The branch wraps fetchUser in a generic retry helper that retries every error, not only timeouts.",
      "claims": [
        {"id": "C1", "statement": "withRetry retries every error, including HTTP 4xx responses that cannot succeed on a retry.", "kind": "fact", "confidence": "high", "evidence": ["src/retry.js:6"], "followup_status": null},
        {"id": "C2", "statement": "With the default of two retries and a 2000 ms timeout, a caller can wait about six seconds before fetchUser fails.", "kind": "inference", "confidence": "medium", "evidence": ["src/retry.js:3", "src/user.js:5"], "followup_status": null},
        {"id": "C3", "statement": "fetchUser never passes a retry count, so the default applies to every caller.", "kind": "inference", "confidence": "low", "evidence": ["src/user.js:5"], "followup_status": null}
      ],
      "open_questions": ["Should HTTP errors be retried at all?"]
    }
  }
}
EOF
cat > README.md <<'EOF'
# User service
EOF
cat > src/api.js <<'EOF'
export const api = {
  async get(url, { timeout }) {
    const res = await fetch(url, { signal: AbortSignal.timeout(timeout) });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  },
};
EOF
cat > src/user.js <<'EOF'
import { api } from "./api.js";

export async function fetchUser(id) {
  return api.get(`/users/${id}`, { timeout: 2000 });
}
EOF
g add README.md src/api.js src/user.js
g commit -q -m "User service"
g checkout -q -b feature/retry
cat > src/retry.js <<'EOF'
export async function withRetry(fn, retries = 2) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError;
}
EOF
cat > src/user.js <<'EOF'
import { api } from "./api.js";
import { withRetry } from "./retry.js";

export async function fetchUser(id) {
  return withRetry(() => api.get(`/users/${id}`, { timeout: 2000 }));
}
EOF
g add src/retry.js src/user.js
g commit -q -m "Retry fetchUser"
g checkout -q main
cat > README.md <<'EOF'
# User service

Fetches users from the API.
EOF
g add README.md
g commit -q -m "Describe the service"
g checkout -q feature/retry
