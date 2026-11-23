#!/usr/bin/env bash
# Start / stop / status for the production Docker Compose stack (Caddyfile.tunnel).
#
# Usage:
#   ./scripts/macos/stack.sh start|stop|restart|status|health
#
# Requires Docker Desktop running. Compose uses restart: unless-stopped so containers
# come back after Docker itself restarts (enable "Start Docker Desktop when you log in").

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

export CADDYFILE="${CADDYFILE:-Caddyfile.tunnel}"
COMPOSE=(docker compose -f docker-compose.prod.yml)

die() { echo "error: $*" >&2; exit 1; }

cmd="${1:-}"
[[ -n "$cmd" ]] || die "usage: $0 start|stop|restart|status|health"

case "$cmd" in
  start)
    [[ -f .env ]] || die "missing .env — copy from .env.production.example and generate secrets"
    "${COMPOSE[@]}" up -d --build
    echo "Stack starting. Health: $0 health"
    ;;
  stop)
    "${COMPOSE[@]}" stop
    echo "Stack stopped (volumes preserved)."
    ;;
  restart)
    "${COMPOSE[@]}" restart
    ;;
  status)
    "${COMPOSE[@]}" ps
    ;;
  health)
    curl -fsS http://127.0.0.1/health | python3 -m json.tool 2>/dev/null \
      || curl -fsS http://127.0.0.1/health
    echo
    ;;
  *)
    die "unknown command: $cmd"
    ;;
esac
