#!/usr/bin/env bash
set -euo pipefail
mkdir -p .stub
echo '{}' > .stub/scenario.json
cat > 'README.md' <<'EOF'
Sample workspace.
EOF
