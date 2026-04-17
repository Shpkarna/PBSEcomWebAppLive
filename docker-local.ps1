param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'ps', 'logs', 'restart', 'health')]
    [string]$Action = 'up',

    [Parameter(Position = 1)]
    [string]$Service
)

$ErrorActionPreference = 'Stop'

$composeFile = Join-Path $PSScriptRoot 'deployment/docker-compose.yml'
$envFile = Join-Path $PSScriptRoot 'deployment/.env.aiecom'
$composeArgs = @('-f', $composeFile, '--env-file', $envFile)

Push-Location $PSScriptRoot

try {
    switch ($Action) {
        'up' {
            & docker compose @composeArgs up -d --build
        }
        'down' {
            & docker compose @composeArgs down
        }
        'ps' {
            & docker compose @composeArgs ps
        }
        'logs' {
            if ($Service) {
                & docker compose @composeArgs logs -f $Service
            } else {
                & docker compose @composeArgs logs -f
            }
        }
        'restart' {
            if ($Service) {
                & docker compose @composeArgs restart $Service
            } else {
                & docker compose @composeArgs restart
            }
        }
        'health' {
            & docker compose @composeArgs ps
            Write-Host ''
            Write-Host 'Backend health:'
            & docker compose @composeArgs exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health').read().decode())"
            Write-Host ''
            Write-Host 'Mongo ping:'
            & docker compose @composeArgs exec mongo mongosh --quiet -u root -p rootpassword --authenticationDatabase admin --eval "db.adminCommand('ping')"
        }
    }
}
finally {
    Pop-Location
}