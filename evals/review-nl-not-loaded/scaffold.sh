#!/usr/bin/env bash
# The review-working-tree repository (one staged, one unstaged, one untracked change). The user asks
# in their own words for the review skill, which only the typed command can load.
# `.stub/exec-stdin.txt` and `.stub/exec.sentinel` start empty: a regex grader fails on a missing
# file, and an allowed `ask` consultation overwrites/appends them.
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
mkdir -p .stub src/pages
: > .stub/exec-stdin.txt
: > .stub/exec.sentinel
cat > .stub/scenario.json <<'EOF'
{
  "exec": {
    "reply": {
      "summary": "The change adds retries and a cache to fetchUser; a timeout now looks like a missing user, and the cache never evicts entries.",
      "claims": [
        {"id": "C1", "statement": "After the last TimeoutError, fetchUser returns an empty object instead of throwing, so callers cannot tell a timeout from a missing user.", "kind": "fact", "confidence": "high", "evidence": ["src/user.js:12"], "followup_status": null},
        {"id": "C2", "statement": "The entries map in src/cache.js grows with every distinct id and never evicts anything.", "kind": "inference", "confidence": "medium", "evidence": ["src/cache.js:4"], "followup_status": null},
        {"id": "C3", "statement": "renderProfile shows \"Please try again later\" for a user that really does not exist, because it cannot tell that case from a timeout.", "kind": "inference", "confidence": "low", "evidence": ["src/pages/profile.js:5"], "followup_status": null}
      ],
      "open_questions": ["Is an unbounded cache acceptable for the expected number of users?"]
    }
  }
}
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
cat > src/pages/profile.js <<'EOF'
import { fetchUser } from "../user.js";

export async function renderProfile(id) {
  const user = await fetchUser(id);
  return `Hello ${user.name}`;
}
EOF
g add src/api.js src/user.js src/pages/profile.js
g commit -q -m "Profile page"
cat > src/pages/profile.js <<'EOF'
import { fetchUser } from "../user.js";

export async function renderProfile(id) {
  const user = await fetchUser(id);
  if (!user.id) return "Please try again later";
  return `Hello ${user.name}`;
}
EOF
g add src/pages/profile.js
cat > src/user.js <<'EOF'
import { api } from "./api.js";
import { remember } from "./cache.js";

export async function fetchUser(id, { retries = 2 } = {}) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return remember(id, await api.get(`/users/${id}`, { timeout: 2000 }));
    } catch (err) {
      if (err.name !== "TimeoutError") throw err;
    }
  }
  return {};
}
EOF
cat > src/cache.js <<'EOF'
const entries = new Map();

export function remember(key, value) {
  entries.set(key, value);
  return value;
}
EOF
