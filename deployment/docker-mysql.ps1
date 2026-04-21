<#
.SYNOPSIS
    Day-to-day operations helper for the MySQL deployment stack.

.DESCRIPTION
    Wraps common docker compose commands for docker-compose.mysql.yml.
    Mirrors the interface of docker-local.ps1 (MongoDB stack) so the same
    muscle-memory applies to both stacks.

    Requires deployment\.env.mysql to exist. Copy from
    deployment\env.mysql.template and fill in credentials before first use.

.PARAMETER Action
    up       — Build images if needed and start all containers in detached mode.
    down     — Stop and remove containers (data volumes are preserved).
    ps       — Show running container status.
    logs     — Follow log output (all or a named service).
    restart  — Restart all or a named service.
    health   — Show container status + hit /health on the backend + MySQL ping.

.PARAMETER Service
    Optional service name for the logs and restart actions: mysql | backend | frontend.

.EXAMPLE
    .\deployment\docker-mysql.ps1 up
    .\deployment\docker-mysql.ps1 logs backend
    .\deployment\docker-mysql.ps1 restart backend
    .\deployment\docker-mysql.ps1 down
    .\deployment\docker-mysql.ps1 health

.NOTES
    For a first-time full deployment (schema bootstrap + smoke tests) use:
      .\deployment\deploy_mysql.ps1
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'ps', 'logs', 'restart', 'health')]
    [string]$Action = 'up',

    [Parameter(Position = 1)]
    [string]$Service
)

$ErrorActionPreference = 'Stop'

$RepoRoot    = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $PSScriptRoot 'docker-compose.mysql.yml'
$EdgeComposeFile = Join-Path $PSScriptRoot 'docker-compose.edge.yml'
$EnvFile     = Join-Path $PSScriptRoot '.env.mysql'

if (-not (Test-Path $EnvFile)) {
    Write-Error @"
Env file not found: $EnvFile

Create it from the template:
  Copy-Item deployment\env.mysql.template deployment\.env.mysql
Fill in every CHANGE_ME value, then run this script again.
"@
    exit 1
}

# ── Parse env file for values needed in the health action ─────────────────────
function Read-EnvVar([string]$Path, [string]$Key) {
    $line = Get-Content $Path | Where-Object { $_ -match "^\s*$Key\s*=" } | Select-Object -First 1
    if ($line -and $line -match '=(.+)$') { return $Matches[1].Trim() }
    return ''
}

$composeArgs = @('-f', $ComposeFile, '--env-file', $EnvFile)
$publicDomain = Read-EnvVar $EnvFile 'PUBLIC_DOMAIN'
if ($publicDomain) {
    $composeArgs = @('-f', $ComposeFile, '-f', $EdgeComposeFile, '--env-file', $EnvFile)
}

Push-Location $RepoRoot
try {
    switch ($Action) {

        'up' {
            docker compose @composeArgs up -d --build
        }

        'down' {
            docker compose @composeArgs down
        }

        'ps' {
            docker compose @composeArgs ps
        }

        'logs' {
            if ($Service) {
                docker compose @composeArgs logs -f $Service
            } else {
                docker compose @composeArgs logs -f
            }
        }

        'restart' {
            if ($Service) {
                docker compose @composeArgs restart $Service
            } else {
                docker compose @composeArgs restart
            }
        }

        'health' {
            Write-Host '── Container status ──────────────────────────────────────' -ForegroundColor Cyan
            docker compose @composeArgs ps

            Write-Host ''
            Write-Host '── Backend /health ───────────────────────────────────────' -ForegroundColor Cyan
            docker compose @composeArgs exec backend python -c @"
import urllib.request
resp = urllib.request.urlopen('http://127.0.0.1:8000/health')
print(resp.read().decode())
"@

            Write-Host ''
            Write-Host '── MySQL ping ────────────────────────────────────────────' -ForegroundColor Cyan
            $rootPass = Read-EnvVar $EnvFile 'MYSQL_ROOT_PASSWORD'
            docker compose @composeArgs exec mysql `
                mysqladmin ping -h 127.0.0.1 -u root "-p${rootPass}" --silent
            if ($LASTEXITCODE -eq 0) {
                Write-Host 'mysqld is alive' -ForegroundColor Green
            } else {
                Write-Host 'MySQL ping failed' -ForegroundColor Red
            }

            if ($publicDomain) {
                Write-Host ''
                Write-Host '── Edge HTTP host-header check ───────────────────────────' -ForegroundColor Cyan
                $edgeStatus = docker compose @composeArgs exec edge sh -c "wget --server-response --spider --header='Host: $publicDomain' http://127.0.0.1/ 2>&1 | head -n 1"
                Write-Host ($edgeStatus | Out-String)
            }
        }
    }
} finally {
    Pop-Location
}
