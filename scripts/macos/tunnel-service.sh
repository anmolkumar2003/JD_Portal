#!/usr/bin/env bash
# Manage Cloudflare Quick Tunnel as a macOS LaunchAgent (survives Terminal close).
#
# Usage:
#   ./scripts/macos/tunnel-service.sh install|start|stop|restart|status|uninstall|url
#
# Notes:
# - Quick Tunnel URL changes whenever cloudflared restarts.
# - Closing Terminal does NOT stop a LaunchAgent.
# - Mac sleep / shutdown WILL interrupt the tunnel and the local stack until awake/boot.
# - Does NOT publish Postgres, Valkey, or MinIO — only tunnels to localhost:80 (Caddy).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL="com.hrportal.cloudflared"
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="${HOME}/Library/Logs/hr-portal"
TEMPLATE="${ROOT}/scripts/macos/com.hrportal.cloudflared.plist.template"

die() { echo "error: $*" >&2; exit 1; }

find_cloudflared() {
  if command -v cloudflared >/dev/null 2>&1; then
    command -v cloudflared
    return
  fi
  for p in /opt/homebrew/bin/cloudflared /usr/local/bin/cloudflared; do
    [[ -x "$p" ]] && { echo "$p"; return; }
  done
  die "cloudflared not found. Install with: brew install cloudflared"
}

cmd="${1:-}"
[[ -n "$cmd" ]] || die "usage: $0 install|start|stop|restart|status|uninstall|url"

case "$cmd" in
  install)
    cf="$(find_cloudflared)"
    mkdir -p "${HOME}/Library/LaunchAgents" "$LOG_DIR"
    sed \
      -e "s|__CLOUDFLARED__|${cf}|g" \
      -e "s|__LOG_DIR__|${LOG_DIR}|g" \
      "$TEMPLATE" >"$PLIST_DEST"
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"
    launchctl enable "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    launchctl kickstart -k "gui/$(id -u)/${LABEL}"
    echo "Installed and started LaunchAgent ${LABEL}"
    echo "Logs: ${LOG_DIR}/cloudflared.*.log"
    echo "After the URL appears in the log, set CORS_ORIGINS and WEB_BASE_URL, then:"
    echo "  CADDYFILE=Caddyfile.tunnel docker compose -f docker-compose.prod.yml up -d api web"
    ;;
  start)
    [[ -f "$PLIST_DEST" ]] || die "not installed — run: $0 install"
    launchctl kickstart -k "gui/$(id -u)/${LABEL}"
    echo "Started ${LABEL}"
    ;;
  stop)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    echo "Stopped ${LABEL}"
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    if launchctl print "gui/$(id -u)/${LABEL}" >/dev/null 2>&1; then
      echo "LaunchAgent: loaded"
      launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null | sed -n '1,40p'
    else
      echo "LaunchAgent: not loaded"
    fi
    if pgrep -f 'cloudflared tunnel' >/dev/null 2>&1; then
      echo "cloudflared: running (pid $(pgrep -f 'cloudflared tunnel' | tr '\n' ' '))"
    else
      echo "cloudflared: not running"
    fi
    "$0" url || true
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    rm -f "$PLIST_DEST"
    echo "Uninstalled ${LABEL}"
    ;;
  url)
    err="${LOG_DIR}/cloudflared.err.log"
    out="${LOG_DIR}/cloudflared.out.log"
    url=""
    for f in "$err" "$out"; do
      [[ -f "$f" ]] || continue
      url="$(grep -Eo 'https://[a-zA-Z0-9.-]+\.trycloudflare\.com' "$f" | tail -1 || true)"
      [[ -n "$url" ]] && break
    done
    if [[ -n "$url" ]]; then
      echo "$url"
    else
      echo "No trycloudflare.com URL found yet. Check: tail -f ${LOG_DIR}/cloudflared.err.log" >&2
      exit 1
    fi
    ;;
  *)
    die "unknown command: $cmd"
    ;;
esac
