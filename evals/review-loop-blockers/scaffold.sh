#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub
echo '{}' > .stub/scenario.json
mkdir -p src/pages
cat > src/user.js <<'EOF'
import { api } from "./api.js";

export async function fetchUser(id) {
  try {
    return await api.get(`/users/${id}`, { timeout: 2000 });
  } catch (err) {
    if (err.name === "TimeoutError") return {};
    throw err;
  }
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
cat > src/api.js <<'EOF'
export const api = {
  async get(url, { timeout }) {
    const res = await fetch(url, { signal: AbortSignal.timeout(timeout) });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  },
};
EOF
