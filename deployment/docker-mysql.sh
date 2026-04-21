#!/usr/bin/env bash
set -Eeuo pipefail

ACTION="${1:-up}"
SERVICE="${2:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.mysql.yml"
EDGE_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.edge.yml"
ENV_FILE="${SCRIPT_DIR}/.env.mysql"

usage() {
  cat <<'EOF'
Usage: bash deployment/docker-mysql.sh [up|down|ps|logs|restart|health] [service]

Actions:
  up       Build images if needed and start all services in detached mode.
  down     Stop and remove containers (data volumes are preserved).
  ps       Show container status.
  logs     Follow logs for all services or a single service.
  restart  Restart all services or a single service.
  health   Show container status, backend health, and MySQL ping.

Optional service names for logs/restart: mysql | backend | frontend
EOF
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

read_env_var() {
  local key="$1"
  awk -v search="$key" '
    /^[[:space:]]*#/ { next }
    index($0, "=") == 0 { next }
    {
      env_key = substr($0, 1, index($0, "=") - 1)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", env_key)
      if (env_key == search) {
        value = substr($0, index($0, "=") + 1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
        print value
        exit
      }
    }
  ' "$ENV_FILE"
}

if [[ ! -f "$ENV_FILE" ]]; then
  fail "Env file not found: $ENV_FILE

Create it from the template:
  cp deployment/env.mysql.template deployment/.env.mysql
Fill in every CHANGE_ME value, then run this script again."
fi

compose_args=(-f "$COMPOSE_FILE" --env-file "$ENV_FILE")
public_domain="$(read_env_var PUBLIC_DOMAIN)"
if [[ -n "$public_domain" ]]; then
  compose_args=(-f "$COMPOSE_FILE" -f "$EDGE_COMPOSE_FILE" --env-file "$ENV_FILE")
fi

cd "$REPO_ROOT"

case "$ACTION" in
  up)
    docker compose "${compose_args[@]}" up -d --build
    ;;
  down)
    docker compose "${compose_args[@]}" down
    ;;
  ps)
    docker compose "${compose_args[@]}" ps
    ;;
  logs)
    if [[ -n "$SERVICE" ]]; then
      docker compose "${compose_args[@]}" logs -f "$SERVICE"
    else
      docker compose "${compose_args[@]}" logs -f
    fi
    ;;
  restart)
    if [[ -n "$SERVICE" ]]; then
      docker compose "${compose_args[@]}" restart "$SERVICE"
    else
      docker compose "${compose_args[@]}" restart
    fi
    ;;
  health)
    printf '── Container status ──────────────────────────────────────\n'
    docker compose "${compose_args[@]}" ps

    printf '\n── Backend /health ───────────────────────────────────────\n'
    docker compose "${compose_args[@]}" exec backend python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=15).read().decode())
PY

    printf '\n── MySQL ping ────────────────────────────────────────────\n'
    root_pass="$(read_env_var MYSQL_ROOT_PASSWORD)"
    docker compose "${compose_args[@]}" exec mysql mysqladmin ping -h 127.0.0.1 -u root "-p${root_pass}" --silent
    printf 'mysqld is alive\n'

    if [[ -n "$public_domain" ]]; then
      printf '\n── Edge HTTP host-header check ───────────────────────────\n'
      python3 - "$public_domain" <<'PY'
  import http.client
  import sys

  domain = sys.argv[1]
  conn = http.client.HTTPConnection('127.0.0.1', 80, timeout=15)
  conn.request('GET', '/', headers={'Host': domain})
  response = conn.getresponse()
  print(f'HTTP {response.status}')
  if response.status not in (200, 301, 302, 308):
    raise SystemExit(f'Unexpected edge response: HTTP {response.status}')
  PY
    fi
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage
    fail "Unsupported action: $ACTION"
    ;;
esac