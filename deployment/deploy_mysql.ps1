<#
.SYNOPSIS
    First-time production deployment for the MySQL engine variant of econsite.

.DESCRIPTION
    Orchestrates the complete first-time deployment:
      Step 1 — Validate prerequisites (Docker, env file, required vars)
      Step 2 — Build Docker images
      Step 3 — Start services (MySQL → backend → frontend)
      Step 4 — Wait for all services to pass Docker health checks
      Step 5 — Bootstrap MySQL application schema inside the backend container
      Step 6 — Seed the admin user via init_db.py
      Step 7 — Smoke-test key API endpoints
      Step 8 — Print final service status

    Prerequisites:
      - Docker Desktop (or Docker Engine) running
      - deployment\.env.mysql populated from deployment\env.mysql.template
        (every CHANGE_ME value replaced with real credentials)

.PARAMETER EnvFile
    Absolute or relative path to the env file.
    Default: <repo_root>\deployment\.env.mysql

.PARAMETER NoBuild
    Skip the image build step and use cached/pulled images instead.
    Useful for re-deploying without code changes.

.PARAMETER SkipSmoke
    Skip the Step 7 API smoke tests (useful in air-gapped environments).

.EXAMPLE
    # Normal first-time deployment from repo root:
    .\deployment\deploy_mysql.ps1

    # Use a secrets file stored outside the repo:
    .\deployment\deploy_mysql.ps1 -EnvFile C:\secrets\prod.mysql.env

    # Redeploy containers only (cached images), skip smoke:
    .\deployment\deploy_mysql.ps1 -NoBuild -SkipSmoke

.NOTES
    DO NOT EXECUTE in environments where infrastructure is unavailable.
    Written for PowerShell 5.1+.
#>

[CmdletBinding()]
param(
    [string]$EnvFile   = '',
    [switch]$NoBuild,
    [switch]$SkipSmoke
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $PSNativeCommandUseErrorActionPreference = $false
}

# $PSScriptRoot = deployment\ ; repo root is one level up.
$RepoRoot    = Split-Path -Parent $PSScriptRoot
$DeployDir   = $PSScriptRoot
$ComposeFile = Join-Path $DeployDir 'docker-compose.mysql.yml'
$EdgeComposeFile = Join-Path $DeployDir 'docker-compose.edge.yml'

if (-not $EnvFile) {
    $EnvFile = Join-Path $DeployDir '.env.mysql'
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

function Write-Step([string]$Msg) {
    Write-Host "`n==> $Msg" -ForegroundColor Cyan
}

function Write-Ok([string]$Msg) {
    Write-Host "  [OK]  $Msg" -ForegroundColor Green
}

function Write-Warn([string]$Msg) {
    Write-Host "  [WARN] $Msg" -ForegroundColor Yellow
}

function Write-Fail([string]$Msg) {
    Write-Host "  [FAIL] $Msg" -ForegroundColor Red
    throw $Msg
}

# Parse a KEY=VALUE env file into a hashtable.
# Lines beginning with # and blank lines are skipped.
function Read-EnvFile([string]$Path) {
    $cfg = @{}
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if ($line -and $line -notmatch '^\s*#' -and $line -match '^([^=]+)=(.*)$') {
            $cfg[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
    return $cfg
}

function Resolve-HostPort([string]$Value, [string]$DefaultPort) {
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $DefaultPort
    }
    $segments = $Value.Split(':')
    return $segments[$segments.Length - 1]
}

# Poll Docker inspect until the named container reports 'healthy' or times out.
function Wait-ServiceHealthy([string]$ContainerName, [int]$MaxSeconds = 180) {
    Write-Host "  Waiting for $ContainerName to pass health check" -NoNewline
    $elapsed = 0
    while ($elapsed -lt $MaxSeconds) {
        $status = docker inspect --format='{{.State.Health.Status}}' $ContainerName 2>$null
        if ($status -eq 'healthy') {
            Write-Host ' healthy' -ForegroundColor Green
            return
        }
        Write-Host '.' -NoNewline
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    Write-Host ' TIMEOUT' -ForegroundColor Red
    Write-Fail "$ContainerName did not become healthy within ${MaxSeconds}s. Inspect logs:`n  docker logs $ContainerName"
}

# ─── Step 1: Validate prerequisites ───────────────────────────────────────────

Write-Step 'Step 1: Validating prerequisites'

# 1a. Docker running
try {
    Get-Command docker -ErrorAction Stop | Out-Null
    $null = docker info --format '{{.ServerVersion}}' 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'docker info failed' }
    Write-Ok 'Docker is running'
} catch {
    Write-Fail 'Docker is not running or not installed. Start Docker Desktop and retry.'
}

# 1b. Env file present
$EnvFile = $EnvFile -replace '/', '\'
if (-not (Test-Path $EnvFile)) {
    Write-Fail @"
Env file not found: $EnvFile

Create it from the template:
  Copy-Item deployment\env.mysql.template deployment\.env.mysql
Then fill in every CHANGE_ME value before running this script.
"@
}
Write-Ok "Env file: $EnvFile"

# 1c. Parse env file
$cfg = Read-EnvFile $EnvFile
$PublicDomain = if ($cfg.ContainsKey('PUBLIC_DOMAIN')) { $cfg['PUBLIC_DOMAIN'] } else { '' }
$AcmeEmail    = if ($cfg.ContainsKey('ACME_EMAIL')) { $cfg['ACME_EMAIL'] } else { '' }

# 1d. Required vars must be present and not placeholder values
$required = @(
    'MYSQL_ROOT_PASSWORD',
    'MYSQL_APP_PASSWORD',
    'SECRET_KEY',
    'ADMIN_PASSWORD'
)
foreach ($key in $required) {
    if (-not $cfg.ContainsKey($key) -or [string]::IsNullOrWhiteSpace($cfg[$key])) {
        Write-Fail "Required variable '$key' is missing or empty in $EnvFile"
    }
    if ($cfg[$key] -like 'CHANGE_ME*') {
        Write-Fail "'$key' still contains a placeholder value. Set a real value in $EnvFile"
    }
}
Write-Ok 'All required env vars present and non-placeholder'

# 1e. Compose file present
if (-not (Test-Path $ComposeFile)) {
    Write-Fail "Compose file not found: $ComposeFile"
}
Write-Ok "Compose file: $ComposeFile"

if ($PublicDomain) {
    if (-not (Test-Path $EdgeComposeFile)) {
        Write-Fail "Edge compose file not found: $EdgeComposeFile"
    }
    if ([string]::IsNullOrWhiteSpace($AcmeEmail)) {
        Write-Fail "ACME_EMAIL is required when PUBLIC_DOMAIN is set in $EnvFile"
    }
    Write-Ok "Edge proxy enabled for domain: $PublicDomain"
}

# ─── Step 2: Build Docker images ──────────────────────────────────────────────

$composeArgs = if ($PublicDomain) {
    @('-f', $ComposeFile, '-f', $EdgeComposeFile, '--env-file', $EnvFile)
} else {
    @('-f', $ComposeFile, '--env-file', $EnvFile)
}

if (-not $NoBuild) {
    Write-Step 'Step 2: Building Docker images (this may take several minutes)'
    Push-Location $RepoRoot
    try {
        docker compose @composeArgs build --no-cache --pull
        if ($LASTEXITCODE -ne 0) { Write-Fail 'docker compose build failed. Review output above.' }
        Write-Ok 'All images built successfully'
    } finally {
        Pop-Location
    }
} else {
    Write-Step 'Step 2: Skipping image build (-NoBuild flag set)'
}

# ─── Step 3: Start the stack ──────────────────────────────────────────────────

Write-Step 'Step 3: Starting services (MySQL -> backend -> frontend)'
Push-Location $RepoRoot
try {
    docker compose @composeArgs up -d
    if ($LASTEXITCODE -ne 0) { Write-Fail 'docker compose up failed. Review output above.' }
    Write-Ok 'All containers started'
} finally {
    Pop-Location
}

# ─── Step 4: Wait for health checks ───────────────────────────────────────────

Write-Step 'Step 4: Waiting for all services to be healthy'
Wait-ServiceHealthy 'econsite-mysql'    -MaxSeconds 120
Wait-ServiceHealthy 'econsite-backend'  -MaxSeconds 180
Wait-ServiceHealthy 'econsite-frontend' -MaxSeconds 60

# ─── Step 5: Bootstrap MySQL application schema ───────────────────────────────

Write-Step 'Step 5: Bootstrapping MySQL application schema'
Write-Host '  Running MySQLBootstrap().bootstrap() inside backend container...'

$bootstrapPy = @'
import sys
sys.path.insert(0, ".")
from app.data.repositories.mysql_bootstrap import MySQLBootstrap
MySQLBootstrap().bootstrap()
print("Schema bootstrap complete.")
'@

$output = $bootstrapPy | docker exec -i econsite-backend python - 2>&1
Write-Host ($output | Out-String)

if ($LASTEXITCODE -ne 0) {
    Write-Fail 'Schema bootstrap failed. Check output above and verify MYSQL_* env vars in .env.mysql'
}
Write-Ok 'Application schema bootstrapped'

# ─── Step 6: Seed admin user ──────────────────────────────────────────────────

Write-Step 'Step 6: Seeding admin user (init_db.py)'
$initOutput = docker exec econsite-backend python -m app.init_db 2>&1
Write-Host ($initOutput | Out-String)

if ($LASTEXITCODE -ne 0) {
    # Admin user may already exist if this is a re-deploy — treat as warning.
    Write-Warn 'init_db.py returned non-zero (user may already exist). Continuing.'
} else {
    Write-Ok 'Admin user seeded'
}

# ─── Step 7: Smoke tests ──────────────────────────────────────────────────────

if (-not $SkipSmoke) {
    Write-Step 'Step 7: Running API smoke tests'

    $BackendPort = Resolve-HostPort -Value $(if ($cfg.ContainsKey('BACKEND_PORT')) { $cfg['BACKEND_PORT'] } else { '7999' }) -DefaultPort '7999'
    $BaseUrl     = "http://localhost:$BackendPort"

    # 7a. Health
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/health" -UseBasicParsing -TimeoutSec 15
        if ($resp.StatusCode -eq 200) {
            Write-Ok "GET /health -> 200 OK"
        } else {
            Write-Fail "GET /health returned HTTP $($resp.StatusCode)"
        }
    } catch {
        Write-Fail "GET /health failed: $_"
    }

    # 7b. Products API
    try {
        $resp = Invoke-WebRequest -Uri "$BaseUrl/api/products" -UseBasicParsing -TimeoutSec 15
        if ($resp.StatusCode -eq 200) {
            Write-Ok "GET /api/products -> 200 OK"
        } else {
            Write-Fail "GET /api/products returned HTTP $($resp.StatusCode)"
        }
    } catch {
        Write-Fail "GET /api/products failed: $_"
    }

    # 7c. Backend runtime config — confirms DB_ENGINE=mysql
    try {
        $engine = docker exec econsite-backend python -c "from app.config import settings; print(settings.db_engine)" 2>$null
        $engine = ($engine | Out-String).Trim()
        if ($engine -eq 'mysql') {
            Write-Ok "Backend runtime reports db_engine=mysql"
        } else {
            Write-Fail "Backend runtime config: expected db_engine=mysql, got '$engine'"
        }
    } catch {
        Write-Warn "Unable to confirm DB_ENGINE via backend container runtime (non-blocking)"
    }

    if ($PublicDomain) {
        try {
            $edgeCheck = docker exec econsite-edge sh -c "wget --server-response --spider --header='Host: $PublicDomain' http://127.0.0.1/ 2>&1 | head -n 1"
            Write-Ok "Edge host-header check completed for $PublicDomain"
            Write-Host ($edgeCheck | Out-String)
        } catch {
            Write-Warn "Edge host-header check failed: $_"
        }
    }
} else {
    Write-Step 'Step 7: Skipping smoke tests (-SkipSmoke flag set)'
}

# ─── Step 8: Final status ─────────────────────────────────────────────────────

Write-Step 'Step 8: Deployment complete — service status'
Write-Host ''
Push-Location $RepoRoot
docker compose -f $ComposeFile --env-file $EnvFile ps
Pop-Location

$FrontendPort = Resolve-HostPort -Value $(if ($cfg.ContainsKey('FRONTEND_PORT')) { $cfg['FRONTEND_PORT'] } else { '3000' }) -DefaultPort '3000'
$BackendPort  = Resolve-HostPort -Value $(if ($cfg.ContainsKey('BACKEND_PORT'))  { $cfg['BACKEND_PORT'] }  else { '7999' }) -DefaultPort '7999'

Write-Host ''
Write-Host '  Frontend  : ' -NoNewline
Write-Host "http://localhost:$FrontendPort" -ForegroundColor Green
Write-Host '  Backend   : ' -NoNewline
Write-Host "http://localhost:$BackendPort" -ForegroundColor Green
if ($PublicDomain) {
    Write-Host '  Public URL: ' -NoNewline
    Write-Host "https://$PublicDomain" -ForegroundColor Green
}
Write-Host '  DB engine : mysql (ecomdb_phase6)' -ForegroundColor Green
Write-Host ''
Write-Host '  Day-to-day operations:'
Write-Host '    .\deployment\docker-mysql.ps1 [up|down|ps|logs|restart|health]'
Write-Host ''
