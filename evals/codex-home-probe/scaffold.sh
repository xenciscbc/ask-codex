#!/usr/bin/env bash
set -euo pipefail
case "$HOME" in *claude-eval*) ;; *) echo "refusing to seed a Codex home outside the eval sandbox: HOME=$HOME" >&2; exit 1;; esac
mkdir -p .stub src
echo '{}' > .stub/scenario.json
cat > src/user.js <<'EOF'
export async function fetchUser(id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
}
EOF
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
printf '%s\n' "$HOME" > .stub/scaffold-home.txt
