#!/usr/bin/env bash
# Throwaway repo with several documents that contradict each other, for the doc-analysis probes.
set -euo pipefail
d="$1"
rm -rf "$d"; mkdir -p "$d/docs" "$d/src"
git -C "$d" init -q -b main
cat > "$d/README.md" <<'EOF'
# Order service
Read the documents under docs/ before changing anything.
EOF
cat > "$d/docs/requirements.md" <<'EOF'
# Requirements
- R1. An order can be cancelled at any time before it ships.
- R2. Refunds are issued within 3 business days of cancellation.
- R3. Customers must receive an email for every status change.
- R4. Order history is kept for 7 years for audit.
EOF
cat > "$d/docs/design.md" <<'EOF'
# Design
- Cancellation is allowed only within 30 minutes of placing the order; after that the order is locked.
- Refunds are batched and run every Friday.
- Emails are sent only when the order ships or is delivered.
- Orders older than 2 years are deleted by a nightly job to save storage.
EOF
cat > "$d/docs/api.md" <<'EOF'
# API
- POST /orders/{id}/cancel — returns 409 once the order has shipped; otherwise cancels it.
- GET /orders?since=... — returns orders up to 7 years old.
- Webhook `order.status_changed` fires on every status change.
EOF
cat > "$d/src/orders.js" <<'EOF'
export function canCancel(order, now) {
  return now - order.placedAt < 30 * 60 * 1000;
}
EOF
git -C "$d" -c user.email=p@example.invalid -c user.name=p add -A
git -C "$d" -c user.email=p@example.invalid -c user.name=p commit -q -m init
