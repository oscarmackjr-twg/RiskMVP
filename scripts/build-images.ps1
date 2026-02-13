# build-images.ps1 — Build all IPRS Docker images with commit SHA tags
# Usage: .\scripts\build-images.ps1
param(
    [string]$Tag = "",
    [switch]$ForAws
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# Determine tag: commit SHA or user-supplied
if (-not $Tag) {
    $Tag = (git -C $ROOT rev-parse --short HEAD 2>$null)
    if (-not $Tag) { $Tag = "latest" }
}

Write-Host "=== Building IPRS Docker Images (tag: $Tag) ===" -ForegroundColor Cyan

$images = @(
    @{ Name = "iprs-marketdata";   Dockerfile = "docker/Dockerfile.marketdata" },
    @{ Name = "iprs-orchestrator"; Dockerfile = "docker/Dockerfile.orchestrator" },
    @{ Name = "iprs-results";      Dockerfile = "docker/Dockerfile.results" },
    @{ Name = "iprs-worker";       Dockerfile = "docker/Dockerfile.worker" },
    @{ Name = "iprs-portfolio";    Dockerfile = "docker/Dockerfile.portfolio" },
    @{ Name = "iprs-risk";         Dockerfile = "docker/Dockerfile.risk" },
    @{ Name = "iprs-regulatory";   Dockerfile = "docker/Dockerfile.regulatory" },
    @{ Name = "iprs-ingestion";    Dockerfile = "docker/Dockerfile.ingestion" },
    @{ Name = "iprs-frontend";     Dockerfile = "docker/Dockerfile.frontend" }
)

$results = @()

foreach ($img in $images) {
    Write-Host "`nBuilding $($img.Name)..." -ForegroundColor Yellow
    $buildArgs = @()
    if ($ForAws -and $img.Name -eq "iprs-frontend") {
        $buildArgs = @("--build-arg", "NGINX_CONF=docker/nginx-aws.conf")
    }
    docker build @buildArgs -t "$($img.Name):$Tag" -t "$($img.Name):latest" -f "$ROOT\$($img.Dockerfile)" $ROOT
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  $($img.Name): OK" -ForegroundColor Green
        $results += @{ Name = $img.Name; Status = "OK" }
    } else {
        Write-Host "  $($img.Name): FAILED" -ForegroundColor Red
        $results += @{ Name = $img.Name; Status = "FAILED" }
    }
}

# Summary
Write-Host "`n=== Build Summary ===" -ForegroundColor Cyan
foreach ($r in $results) {
    $color = if ($r.Status -eq "OK") { "Green" } else { "Red" }
    Write-Host "  $($r.Name): $($r.Status)" -ForegroundColor $color
}

$failed = ($results | Where-Object { $_.Status -ne "OK" }).Count
if ($failed -gt 0) {
    Write-Host "`n$failed image(s) failed to build." -ForegroundColor Red
    exit 1
}
Write-Host "`nAll $($images.Count) images built successfully." -ForegroundColor Green
