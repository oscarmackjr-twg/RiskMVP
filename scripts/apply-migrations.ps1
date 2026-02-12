# apply-migrations.ps1 — Apply SQL migrations to PostgreSQL
# Usage: .\scripts\apply-migrations.ps1 [-DatabaseUrl "postgresql://..."]
param(
    [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

if (-not $DatabaseUrl) {
    $DatabaseUrl = "postgresql://postgres:postgres@localhost:5432/iprs"
    Write-Host "Using default DATABASE_URL: $DatabaseUrl" -ForegroundColor Yellow
}

Write-Host "=== Applying IPRS SQL Migrations ===" -ForegroundColor Cyan

# Check for psql
if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: psql not found. Install PostgreSQL client tools." -ForegroundColor Red
    Write-Host "  Windows: https://www.postgresql.org/download/windows/" -ForegroundColor Yellow
    Write-Host "  Or use Docker: docker exec -i iprs-db psql ..." -ForegroundColor Yellow
    exit 1
}

$migrations = @(
    @{ File = "001_mvp_core.sql";                Description = "Core schema (runs, tasks, results, market data)" },
    @{ File = "002_portfolio_data_services.sql";  Description = "Portfolio, positions, instruments, reference data" },
    @{ File = "003_regulatory_analytics.sql";     Description = "CECL, Basel, audit trail, regulatory reports" }
)

foreach ($mig in $migrations) {
    $path = Join-Path $ROOT "sql" $mig.File
    if (-not (Test-Path $path)) {
        Write-Host "  SKIP: $($mig.File) (not found)" -ForegroundColor Yellow
        continue
    }

    Write-Host "`nApplying $($mig.File)..." -ForegroundColor Yellow
    Write-Host "  $($mig.Description)" -ForegroundColor Gray

    psql $DatabaseUrl -f $path -v ON_ERROR_STOP=1 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED: $($mig.File)" -ForegroundColor Red
        Write-Host "  (This may be OK if the migration was already applied)" -ForegroundColor Yellow
    } else {
        Write-Host "  OK: $($mig.File)" -ForegroundColor Green
    }
}

# Verify tables exist
Write-Host "`nVerifying schema..." -ForegroundColor Yellow
$tableCount = psql $DatabaseUrl -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>$null
$tableCount = $tableCount.Trim()
Write-Host "  Tables in public schema: $tableCount" -ForegroundColor Green

Write-Host "`n=== Migrations Complete ===" -ForegroundColor Cyan
