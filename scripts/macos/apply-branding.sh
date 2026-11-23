#!/usr/bin/env bash
# Set organization name + logo for CA PLUS Tech (requires running prod stack + admin login).
#
# Usage:
#   ADMIN_EMAIL='hradmin@local.hrportal' ADMIN_PASSWORD='…' ./scripts/macos/apply-branding.sh
#
# Never prints the password. Logo: apps/web/public/brand/ca-plus-tech-mark.png (PNG required).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ORG_NAME="${ORG_NAME:-CA PLUS Tech Pvt. Ltd.}"
BASE_URL="${BASE_URL:-http://127.0.0.1}"
ADMIN_EMAIL="${ADMIN_EMAIL:?set ADMIN_EMAIL}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?set ADMIN_PASSWORD}"

LOGO_FILE="${ROOT}/apps/web/public/brand/ca-plus-tech-mark.png"
[[ -f "$LOGO_FILE" ]] || { echo "error: PNG logo missing at $LOGO_FILE" >&2; exit 1; }

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

LOGIN_JSON="$(ADMIN_EMAIL="$ADMIN_EMAIL" ADMIN_PASSWORD="$ADMIN_PASSWORD" python3 - <<'PY'
import json, os
print(json.dumps({"email": os.environ["ADMIN_EMAIL"], "password": os.environ["ADMIN_PASSWORD"]}))
PY
)"

curl -fsS -X POST "${BASE_URL}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "$LOGIN_JSON" >"$TMP"

TOKEN="$(python3 -c "import json; print(json.load(open('$TMP'))['access_token'])")"

ORG_JSON="$(ORG_NAME="$ORG_NAME" python3 - <<'PY'
import json, os
print(json.dumps({"name": os.environ.get("ORG_NAME", "CA PLUS Tech Pvt. Ltd.")}))
PY
)"

curl -fsS -X PATCH "${BASE_URL}/api/v1/org/settings" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -d "$ORG_JSON" >/dev/null

curl -fsS -X PUT "${BASE_URL}/api/v1/org/logo" \
  -H "Authorization: Bearer ${TOKEN}" \
  -F "file=@${LOGO_FILE};type=image/png" >/dev/null

echo "Branding applied: ${ORG_NAME} + logo ($(basename "$LOGO_FILE"))"
