#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.mysql.yml"
EDGE_COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.edge.yml"
ENV_FILE="${SCRIPT_DIR}/.env.mysql"

NO_BUILD=0
SKIP_SMOKE=0
NO_CACHE=0

usage() {
  cat <<'EOF'
Usage: bash deployment/deploy_mysql.sh [options]

Options:
  --env-file PATH   Use a custom env file instead of deployment/.env.mysql
  --no-build        Skip docker compose build and use existing images
  --no-cache        Build images without Docker layer cache
  --skip-smoke      Skip HTTP smoke tests after deployment
  -h, --help        Show this help message

Examples:
  bash deployment/deploy_mysql.sh
  bash deployment/deploy_mysql.sh --env-file /opt/secrets/prod.mysql.env
  bash deployment/deploy_mysql.sh --no-build --skip-smoke
EOF
}

step() {
  printf '\n==> %s\n' "$1"
}

ok() {
  printf '  [OK]  %s\n' "$1"
}

warn() {
  printf '  [WARN] %s\n' "$1"
}

fail() {
  printf '  [FAIL] %s\n' "$1" >&2
  exit 1
}

read_env_var() {
  local key="$1"
  local default_value="${2:-}"
  local value
  value="$(awk -v search="$key" '
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
  ' "$ENV_FILE")"

  if [[ -n "$value" ]]; then
    printf '%s' "$value"
  else
    printf '%s' "$default_value"
  fi
}

wait_service_healthy() {
  local container_name="$1"
  local max_seconds="$2"
  local elapsed=0
  local status=''

  printf '  Waiting for %s to pass health check' "$container_name"
  while (( elapsed < max_seconds )); do
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_name" 2>/dev/null || true)"
    if [[ "$status" == 'healthy' ]]; then
      printf ' healthy\n'
      return 0
    fi
    printf '.'
    sleep 5
    elapsed=$((elapsed + 5))
  done
  printf ' TIMEOUT\n'
  fail "$container_name did not become healthy within ${max_seconds}s. Inspect logs with: docker logs $container_name"
}

while (($#)); do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || fail '--env-file requires a value'
      ENV_FILE="$2"
      shift 2
      ;;
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --no-cache)
      NO_CACHE=1
      shift
      ;;
    --skip-smoke)
      SKIP_SMOKE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "Unknown argument: $1"
      ;;
  esac
done

if [[ "$ENV_FILE" != /* ]]; then
  ENV_FILE="$(cd "$(dirname "$ENV_FILE")" && pwd)/$(basename "$ENV_FILE")"
fi

compose_args=(-f "$COMPOSE_FILE" --env-file "$ENV_FILE")
public_domain=''
acme_email=''

step 'Step 1: Validating prerequisites'

command -v docker >/dev/null 2>&1 || fail 'Docker is not installed or not in PATH.'
docker info >/dev/null 2>&1 || fail 'Docker is not running. Start Docker and retry.'
ok 'Docker is running'

[[ -f "$ENV_FILE" ]] || fail "Env file not found: $ENV_FILE

Create it from the template:
  cp deployment/env.mysql.template deployment/.env.mysql
Then fill in every CHANGE_ME value before running this script."
ok "Env file: $ENV_FILE"

for key in MYSQL_ROOT_PASSWORD MYSQL_APP_PASSWORD SECRET_KEY ADMIN_PASSWORD; do
  value="$(read_env_var "$key")"
  [[ -n "$value" ]] || fail "Required variable '$key' is missing or empty in $ENV_FILE"
  [[ "$value" != CHANGE_ME* ]] || fail "'$key' still contains a placeholder value in $ENV_FILE"
done
ok 'All required env vars present and non-placeholder'

[[ -f "$COMPOSE_FILE" ]] || fail "Compose file not found: $COMPOSE_FILE"
ok "Compose file: $COMPOSE_FILE"

public_domain="$(read_env_var PUBLIC_DOMAIN)"
acme_email="$(read_env_var ACME_EMAIL)"
if [[ -n "$public_domain" ]]; then
  [[ -f "$EDGE_COMPOSE_FILE" ]] || fail "Edge compose file not found: $EDGE_COMPOSE_FILE"
  [[ -n "$acme_email" ]] || fail "ACME_EMAIL is required when PUBLIC_DOMAIN is set"
  compose_args=(-f "$COMPOSE_FILE" -f "$EDGE_COMPOSE_FILE" --env-file "$ENV_FILE")
  ok "Edge proxy enabled for domain: $public_domain"
fi

if (( NO_BUILD == 0 )); then
  step 'Step 2: Building Docker images'
  cd "$REPO_ROOT"
  build_cmd=(docker compose "${compose_args[@]}" build --pull)
  if (( NO_CACHE == 1 )); then
    build_cmd+=(--no-cache)
  fi
  "${build_cmd[@]}"
  ok 'All images built successfully'
else
  step 'Step 2: Skipping image build (--no-build flag set)'
fi

step 'Step 3: Starting services (MySQL -> backend -> frontend)'
cd "$REPO_ROOT"
docker compose "${compose_args[@]}" up -d
ok 'All containers started'

step 'Step 4: Waiting for all services to be healthy'
wait_service_healthy econsite-mysql 120
wait_service_healthy econsite-backend 180
wait_service_healthy econsite-frontend 60

step 'Step 5: Bootstrapping MySQL application schema'
docker exec -i econsite-backend python - <<'PY'
import sys
sys.path.insert(0, ".")
from app.data.repositories.mysql_bootstrap import MySQLBootstrap

MySQLBootstrap().bootstrap()
print("Schema bootstrap complete.")
PY
ok 'Application schema bootstrapped'

step 'Step 6: Seeding admin user (init_db.py)'
if docker exec econsite-backend python -m app.init_db; then
  ok 'Admin user seeded'
else
  warn 'init_db.py returned non-zero (admin user may already exist). Continuing.'
fi

if (( SKIP_SMOKE == 0 )); then
  step 'Step 7: Running API smoke tests'

  backend_port="$(read_env_var BACKEND_PORT 7999)"
  backend_port="${backend_port##*:}"
  base_url="http://127.0.0.1:${backend_port}"

  python3 - "$base_url" <<'PY'
import json
import sys
import urllib.request

base_url = sys.argv[1]

def fetch_json(path: str):
    with urllib.request.urlopen(base_url + path, timeout=15) as response:
        if response.status != 200:
            raise SystemExit(f"{path} returned HTTP {response.status}")
        return json.loads(response.read().decode())

fetch_json("/health")
with urllib.request.urlopen(base_url + "/api/products", timeout=15) as response:
    if response.status != 200:
        raise SystemExit(f"/api/products returned HTTP {response.status}")

print("Smoke tests passed.")
PY

  engine="$(docker exec -i econsite-backend python - <<'PY'
from app.config import settings
print(settings.db_engine)
PY
  )"
  engine="$(printf '%s' "$engine" | tr -d '[:space:]')"
  if [[ "$engine" != 'mysql' ]]; then
    fail "Backend runtime reported db_engine=$engine, expected mysql"
  fi

  if [[ -n "$public_domain" ]]; then
    python3 - "$public_domain" <<'PY'
import http.client
import sys

domain = sys.argv[1]
conn = http.client.HTTPConnection('127.0.0.1', 80, timeout=15)
conn.request('GET', '/', headers={'Host': domain})
response = conn.getresponse()
if response.status not in (200, 301, 302, 308):
    raise SystemExit(f'Edge host-header check failed: HTTP {response.status}')
print(f'Edge host-header check passed: HTTP {response.status}')
PY
  fi

  ok 'Smoke tests passed'
else
  step 'Step 7: Skipping smoke tests (--skip-smoke flag set)'
fi

step 'Step 8: Deployment complete — service status'
cd "$REPO_ROOT"
docker compose "${compose_args[@]}" ps

frontend_port="$(read_env_var FRONTEND_PORT 3000)"
frontend_port="${frontend_port##*:}"
backend_port="$(read_env_var BACKEND_PORT 7999)"
backend_port="${backend_port##*:}"

printf '\n  Frontend  : http://localhost:%s\n' "$frontend_port"
printf '  Backend   : http://localhost:%s\n' "$backend_port"
printf '  DB engine : mysql (ecomdb_phase6)\n\n'
if [[ -n "$public_domain" ]]; then
  printf '  Public URL : https://%s\n\n' "$public_domain"
fi
printf '  Day-to-day operations:\n'
printf '    bash deployment/docker-mysql.sh [up|down|ps|logs|restart|health]\n'