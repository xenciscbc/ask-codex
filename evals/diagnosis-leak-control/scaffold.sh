#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub
echo '{}' > .stub/scenario.json
mkdir -p 'src'
cat > 'src/user.js' <<'EOF'
export async function fetchUser(id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
}
EOF
mkdir -p 'src/pages'
cat > 'src/pages/profile.js' <<'EOF'
import { fetchUser } from "../user.js";
export async function renderProfile(id) {
  const user = await fetchUser(id);
  if (!user.id) return "user not found";
  return `Hello ${user.name}`;
}
EOF
