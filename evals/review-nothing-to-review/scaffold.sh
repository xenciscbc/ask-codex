#!/usr/bin/env bash
# A git repository on main with a clean working tree: nothing to review.
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
echo '{}' > .stub/scenario.json
cat > src/user.js <<'EOF'
export async function fetchUser(api, id) {
  return api.get(`/users/${id}`, { timeout: 2000 });
}
EOF
g add src/user.js
g commit -q -m "User service"
