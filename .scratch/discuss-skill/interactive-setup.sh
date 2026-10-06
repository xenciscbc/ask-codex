#!/usr/bin/env bash
# Ticket 10: throwaway repository and guard baseline for the interactive discussion checks.
# Run from Git Bash: bash .scratch/discuss-skill/interactive-setup.sh
set -euo pipefail
d=/d/tmp/discuss-interactive
rm -rf "$d"; mkdir -p "$d/src" "$d/docs"
git -C "$d" init -q -b main
git -C "$d" config user.email live@example.invalid
git -C "$d" config user.name live
cat > "$d/README.md" <<'EOF'
# Login service
A small Node service. src/login.js checks a username and a password.
Read docs/constraints.md before designing anything for it.
EOF
cat > "$d/docs/constraints.md" <<'EOF'
# Constraints
- The service runs as ONE process on ONE host.
- No Redis, database server or other external store may be added.
- State may live in process memory only; losing it on restart is fine.
EOF
cat > "$d/src/users.js" <<'EOF'
export const users = new Map([["ada", { id: 1, password: "correct horse" }]]);
EOF
cat > "$d/src/login.js" <<'EOF'
import { users } from "./users.js";

export function login(username, password, ip) {
  const user = users.get(username);
  if (!user) return { ok: false, error: "unknown user" };
  if (user.password !== password) return { ok: false, error: "wrong password" };
  return { ok: true, userId: user.id };
}
EOF
git -C "$d" add -A; git -C "$d" commit -q -m init
mkdir -p /d/tmp/discuss-interactive-guard
cp /d/codex/config.toml /d/tmp/discuss-interactive-guard/config.toml.before
sha256sum /d/codex/config.toml | cut -d' ' -f1 > /d/tmp/discuss-interactive-guard/config.sha.before
ls /c/Users/admin/.claude/ask-codex.json >/dev/null 2>&1 && echo present > /d/tmp/discuss-interactive-guard/user-policy.before || echo absent > /d/tmp/discuss-interactive-guard/user-policy.before
tasklist //NH //FO CSV | grep -i codex | cut -d, -f2 | tr -d '"' | sort > /d/tmp/discuss-interactive-guard/pids.before
echo "repo: $d"
echo "config.toml sha256: $(cat /d/tmp/discuss-interactive-guard/config.sha.before)"
echo "user ask-codex.json: $(cat /d/tmp/discuss-interactive-guard/user-policy.before)"
echo "codex pids before: $(wc -l < /d/tmp/discuss-interactive-guard/pids.before)"
