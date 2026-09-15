#!/usr/bin/env bash
set -euo pipefail
case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac
mkdir -p .stub src/pages "$HOME/.codex"
cat > .stub/scenario.json <<'EOF'
{"exec":{"by_model":{"gpt-6-astra":{"reply":{"summary":"Timeouts are swallowed into an empty object; a circuit breaker would keep the page honest.","claims":[{"id":"C1","statement":"fetchUser catches TimeoutError and returns an empty object instead of rethrowing.","kind":"fact","confidence":"high","evidence":["src/user.js:7"],"followup_status":null},{"id":"C2","statement":"A circuit breaker around api.get would stop repeated slow calls from piling up.","kind":"inference","confidence":"low","evidence":[],"followup_status":null},{"id":"C3","statement":"Raising the timeout to 10s would fix the user-not-found reports.","kind":"inference","confidence":"medium","evidence":[],"followup_status":null}],"open_questions":[]}},"gpt-5.6-sol":{"reply":{"summary":"Timeouts are swallowed into an empty object; cancelling with AbortController would surface them.","claims":[{"id":"C1","statement":"fetchUser catches TimeoutError and returns an empty object instead of rethrowing.","kind":"fact","confidence":"high","evidence":["src/user.js:7"],"followup_status":null},{"id":"C2","statement":"An AbortController signal would let callers tell a timeout from a missing user.","kind":"inference","confidence":"medium","evidence":[],"followup_status":null},{"id":"C3","statement":"Raising the timeout would only hide the symptom; the error handling is the real problem.","kind":"inference","confidence":"high","evidence":[],"followup_status":null}],"open_questions":[]}}}}}
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
cat > "$HOME/.codex/config.toml" <<'EOF'
model = "gpt-5.6-terra"
model_reasoning_effort = "low"
EOF
cat > "$HOME/.codex/models_cache.json" <<'EOF'
{
  "fetched_at": "2026-09-15T00:00:00Z",
  "etag": "eval-fixture",
  "client_version": "0.154.0",
  "models": [
    {"slug": "gpt-6-astra", "display_name": "GPT-6 Astra", "priority": 1, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}, {"effort": "ultra"}]},
    {"slug": "gpt-reserve", "display_name": "Reserve", "priority": 3, "visibility": "hide", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}]},
    {"slug": "gpt-5.6-sol", "display_name": "GPT-5.6 Sol", "priority": 4, "visibility": "list", "default_reasoning_level": "low",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}, {"effort": "ultra"}]},
    {"slug": "gpt-5.6-terra", "display_name": "GPT-5.6 Terra", "priority": 7, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}, {"effort": "ultra"}]},
    {"slug": "gpt-5.6-luna", "display_name": "GPT-5.6 Luna", "priority": 8, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}]},
    {"slug": "gpt-5.5", "display_name": "GPT-5.5", "priority": 12, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}]},
    {"slug": "codex-auto-review", "display_name": "Codex Auto Review", "priority": 43, "visibility": "hide", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}]}
  ]
}
EOF
