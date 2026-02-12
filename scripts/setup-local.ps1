# setup-local.ps1 — Bootstrap IPRS locally via Docker Compose
# Usage: .\scripts\setup-local.ps1
param(
    [switch]$SkipBuild,
    [int]$Timeout = 120
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

Write-Host "=== IPRS Local Setup ===" -ForegroundColor Cyan

# 1. Check prerequisites
Write-Host "`n[1/5] Checking prerequisites..." -ForegroundColor Yellow
$missing = @()
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { $missing += "docker" }
if (-not (Get-Command "docker-compose" -ErrorAction SilentlyContinue) -and
    -not (docker compose version 2>$null)) { $missing += "docker compose" }
if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing prerequisites: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor Red
    exit 1
}
Write-Host "  Docker: OK" -ForegroundColor Green

# 2. Build images
if (-not $SkipBuild) {
    Write-Host "`n[2/5] Building Docker images (this may take a few minutes)..." -ForegroundColor Yellow
    docker compose -f "$ROOT\docker\docker-compose.yml" build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Build: OK" -ForegroundColor Green
} else {
    Write-Host "`n[2/5] Skipping build (--SkipBuild)" -ForegroundColor Yellow
}

# 3. Start all services
Write-Host "`n[3/5] Starting services..." -ForegroundColor Yellow
docker compose -f "$ROOT\docker\docker-compose.yml" up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Compose up failed" -ForegroundColor Red
    exit 1
}

# 4. Wait for database health
Write-Host "`n[4/5] Waiting for database to be ready..." -ForegroundColor Yellow
$elapsed = 0
while ($elapsed -lt $Timeout) {
    $health = docker inspect --format='{{.State.Health.Status}}' iprs-db 2>$null
    if ($health -eq "healthy") {
        Write-Host "  Database: healthy" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
    Write-Host "  Waiting... ($elapsed s)" -ForegroundColor Gray
}
if ($elapsed -ge $Timeout) {
    Write-Host "ERROR: Database did not become healthy within ${Timeout}s" -ForegroundColor Red
    exit 1
}

# 5. Verify all services
Write-Host "`n[5/5] Verifying services..." -ForegroundColor Yellow
$services = @(
    @{ Name = "marketdata";   Port = 8001 },
    @{ Name = "orchestrator"; Port = 8002 },
    @{ Name = "results";      Port = 8003 },
    @{ Name = "portfolio";    Port = 8005 },
    @{ Name = "risk";         Port = 8006 },
    @{ Name = "regulatory";   Port = 8007 },
    @{ Name = "ingestion";    Port = 8008 },
    @{ Name = "frontend";     Port = 80   }
)

# Give services a moment to start
Start-Sleep -Seconds 5

$allOk = $true
foreach ($svc in $services) {
    try {
        $url = "http://localhost:$($svc.Port)/health"
        if ($svc.Name -eq "frontend") { $url = "http://localhost:$($svc.Port)/" }
        $response = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-Host "  $($svc.Name) (port $($svc.Port)): OK" -ForegroundColor Green
    } catch {
        Write-Host "  $($svc.Name) (port $($svc.Port)): FAILED" -ForegroundColor Red
        $allOk = $false
    }
}

# Summary
Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Service URLs:" -ForegroundColor White
Write-Host "  Frontend:     http://localhost"
Write-Host "  Marketdata:   http://localhost:8001"
Write-Host "  Orchestrator: http://localhost:8002"
Write-Host "  Results API:  http://localhost:8003"
Write-Host "  Portfolio:    http://localhost:8005"
Write-Host "  Risk:         http://localhost:8006"
Write-Host "  Regulatory:   http://localhost:8007"
Write-Host "  Ingestion:    http://localhost:8008"
Write-Host "  PostgreSQL:   localhost:5432 (postgres/postgres)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Load market data:  python scripts/seed-market-data.py --fred-key YOUR_KEY"
Write-Host "  2. Run smoke tests:   python scripts/smoke-test.py"
Write-Host "  3. Open frontend:     http://localhost"

if (-not $allOk) {
    Write-Host "`nWARNING: Some services failed health checks. Check logs with:" -ForegroundColor Yellow
    Write-Host "  docker compose -f docker/docker-compose.yml logs <service-name>" -ForegroundColor Yellow
    exit 1
}
