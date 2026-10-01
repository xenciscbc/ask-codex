#!/usr/bin/env bash
set -euo pipefail
d=/d/tmp/review-live
rm -rf "$d"; mkdir -p "$d/src"
git -C "$d" init -q -b main
git -C "$d" config user.email live@example.invalid
git -C "$d" config user.name live
cat > "$d/src/retry.js" <<'EOF'
export async function withRetry(fn, attempts) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      last = err;
    }
  }
  throw last;
}
EOF
git -C "$d" add -A; git -C "$d" commit -q -m init
cat > "$d/src/retry.js" <<'EOF'
export async function withRetry(fn, attempts) {
  let last;
  for (let i = 0; i <= attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      last = err;
      await new Promise((r) => setTimeout(r, 100 * i));
    }
  }
  return last;
}
EOF
git -C "$d" status --short
echo "--- guarded"
sha256sum /d/codex/config.toml 2>/dev/null || echo "no D:/codex/config.toml"
ls /c/Users/admin/.claude/ask-codex.json 2>/dev/null || echo "user ask-codex.json absent"
echo "--- codex pids"
tasklist //NH //FO CSV | grep -i codex | cut -d, -f2 | sort > /d/tmp/review-live-pids-before.txt
wc -l < /d/tmp/review-live-pids-before.txt
