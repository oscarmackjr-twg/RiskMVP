# push-ecr.ps1 — Tag and push all IPRS Docker images to AWS ECR
# Usage: .\scripts\push-ecr.ps1 -AccountId 123456789012 [-Region us-east-1] [-Tag latest]
param(
    [Parameter(Mandatory)][string]$AccountId,
    [string]$Region = "us-east-1",
    [string]$Tag = "latest",
    [string]$Project = "iprs"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Pushing IPRS Images to ECR ===" -ForegroundColor Cyan
$ECR_BASE = "$AccountId.dkr.ecr.$Region.amazonaws.com"

# 1. Authenticate to ECR
Write-Host "`n[1/3] Authenticating to ECR..." -ForegroundColor Yellow
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECR_BASE
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: ECR authentication failed. Check AWS credentials." -ForegroundColor Red
    exit 1
}
Write-Host "  ECR auth: OK" -ForegroundColor Green

# 2. Tag and push
Write-Host "`n[2/3] Tagging and pushing images..." -ForegroundColor Yellow
$services = @("marketdata", "orchestrator", "results", "worker", "portfolio", "risk", "regulatory", "ingestion", "frontend")
$results = @()

foreach ($svc in $services) {
    $localTag = "iprs-${svc}:${Tag}"
    $ecrTag = "${ECR_BASE}/${Project}-${svc}:${Tag}"

    Write-Host "  Pushing $svc..." -ForegroundColor Gray
    docker tag $localTag $ecrTag
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    Tag failed for $svc (image 'iprs-${svc}:${Tag}' not found?)" -ForegroundColor Red
        $results += @{ Name = $svc; Status = "TAG_FAILED" }
        continue
    }

    docker push $ecrTag
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    $svc : OK" -ForegroundColor Green
        $results += @{ Name = $svc; Status = "OK" }
    } else {
        Write-Host "    $svc : PUSH_FAILED" -ForegroundColor Red
        $results += @{ Name = $svc; Status = "PUSH_FAILED" }
    }
}

# 3. Summary
Write-Host "`n[3/3] Push Summary" -ForegroundColor Yellow
foreach ($r in $results) {
    $color = if ($r.Status -eq "OK") { "Green" } else { "Red" }
    Write-Host "  $($r.Name): $($r.Status)" -ForegroundColor $color
}

$failed = ($results | Where-Object { $_.Status -ne "OK" }).Count
if ($failed -gt 0) {
    Write-Host "`n$failed image(s) failed to push." -ForegroundColor Red
    exit 1
}
Write-Host "`nAll images pushed to $ECR_BASE" -ForegroundColor Green
