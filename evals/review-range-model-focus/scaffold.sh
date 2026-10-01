#!/usr/bin/env bash
# A git repository on branch feature/errors, one commit ahead of main (src/user.js changed), and a
# Codex home whose model list resolves `sol` to gpt-6-sol. The stub's canned claims cite the
# branch's src/user.js at these lines.
set -euo pipefail
case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac
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
      "summary": "The new error handling hides every failure of fetchUser behind a null result.",
      "claims": [
        {"id": "C1", "statement": "fetchUser now returns null for every failure, so callers cannot tell a timeout from an HTTP error.", "kind": "fact", "confidence": "high", "evidence": ["src/user.js:8"], "followup_status": null},
        {"id": "C2", "statement": "Logging the whole error object can write request URLs with user ids to the console.", "kind": "inference", "confidence": "medium", "evidence": ["src/user.js:7"], "followup_status": null}
      ],
      "open_questions": ["Do callers of fetchUser handle a null result?"]
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
g add src/api.js src/user.js
g commit -q -m "User service"
g checkout -q -b feature/errors
cat > src/user.js <<'EOF'
import { api } from "./api.js";

export async function fetchUser(id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    console.error("fetchUser failed", err);
    return null;
  }
}
EOF
g add src/user.js
g commit -q -m "Handle fetchUser errors"
mkdir -p "$HOME/.codex"
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
    {"slug": "gpt-6-sol", "display_name": "GPT-6 Sol", "priority": 4, "visibility": "list", "default_reasoning_level": "low",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}, {"effort": "ultra"}]},
    {"slug": "gpt-5.6-terra", "display_name": "GPT-5.6 Terra", "priority": 7, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}, {"effort": "ultra"}]},
    {"slug": "gpt-6-luna", "display_name": "GPT-6 Luna", "priority": 8, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}]},
    {"slug": "gpt-5.5", "display_name": "GPT-5.5", "priority": 12, "visibility": "list", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}]},
    {"slug": "codex-auto-review", "display_name": "Codex Auto Review", "priority": 43, "visibility": "hide", "default_reasoning_level": "medium",
     "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}, {"effort": "xhigh"}, {"effort": "max"}]}
  ]
}
EOF
