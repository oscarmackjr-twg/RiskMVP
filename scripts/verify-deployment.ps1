# verify-deployment.ps1 — Post-deployment verification for IPRS
# Usage: .\scripts\verify-deployment.ps1 [-AlbDns my-alb.elb.amazonaws.com] [-Region us-east-1]
param(
    [string]$AlbDns = "localhost",
    [string]$Region = "us-east-1",
    [string]$Environment = "dev",
    [string]$Cluster = ""
)

$ErrorActionPreference = "Continue"

if (-not $Cluster) { $Cluster = "iprs-cluster-$Environment" }

Write-Host "=== IPRS Deployment Verification ===" -ForegroundColor Cyan
Write-Host "  Target: $AlbDns"
Write-Host "  Region: $Region"
Write-Host "  Cluster: $Cluster"

$passed = 0
$failed = 0

function Test-Check {
    param([string]$Name, [bool]$Ok, [string]$Detail = "")
    if ($Ok) {
        Write-Host "  PASS: $Name" -ForegroundColor Green
        $script:passed++
    } else {
        $msg = "  FAIL: $Name"
        if ($Detail) { $msg += " - $Detail" }
        Write-Host $msg -ForegroundColor Red
        $script:failed++
    }
}

# 1. Health endpoints
Write-Host "`n[1/5] Service Health Checks" -ForegroundColor Yellow
$services = @(
    @{ Name = "marketdata";   Port = 8001 },
    @{ Name = "orchestrator"; Port = 8002 },
    @{ Name = "results";      Port = 8003 },
    @{ Name = "portfolio";    Port = 8005 },
    @{ Name = "risk";         Port = 8006 },
    @{ Name = "regulatory";   Port = 8007 },
    @{ Name = "ingestion";    Port = 8008 }
)

foreach ($svc in $services) {
    $url = if ($AlbDns -eq "localhost") {
        "http://localhost:$($svc.Port)/health"
    } else {
        "http://${AlbDns}/$($svc.Name.Substring(0, [Math]::Min(3, $svc.Name.Length)))/health"
    }
    try {
        $resp = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Test-Check "$($svc.Name) health" ($resp.StatusCode -eq 200)
    } catch {
        Test-Check "$($svc.Name) health" $false $_.Exception.Message
    }
}

# 2. Smoke test
Write-Host "`n[2/5] Running Smoke Test" -ForegroundColor Yellow
$smokeResult = python "$PSScriptRoot\smoke-test.py" --base-url "http://$AlbDns" --skip-run 2>&1
$smokeOk = $LASTEXITCODE -eq 0
Test-Check "Smoke test" $smokeOk

# 3. ECS service status (if AWS)
if ($AlbDns -ne "localhost") {
    Write-Host "`n[3/5] ECS Service Status" -ForegroundColor Yellow
    $ecsServices = @("marketdata", "orchestrator", "results", "worker", "portfolio", "risk", "regulatory", "ingestion")
    foreach ($svc in $ecsServices) {
        $svcName = "iprs-${svc}-${Environment}"
        try {
            $desc = aws ecs describe-services --cluster $Cluster --services $svcName --region $Region --output json 2>$null | ConvertFrom-Json
            $esSvc = $desc.services[0]
            $running = $esSvc.runningCount
            $desired = $esSvc.desiredCount
            $ok = $running -eq $desired -and $desired -gt 0
            Test-Check "$svc ECS ($running/$desired)" $ok
        } catch {
            Test-Check "$svc ECS" $false "could not describe service"
        }
    }

    # 4. RDS connectivity
    Write-Host "`n[4/5] RDS Connectivity" -ForegroundColor Yellow
    try {
        $rdsEndpoint = terraform -chdir="$PSScriptRoot\..\terraform" output -raw rds_proxy_endpoint 2>$null
        Test-Check "RDS endpoint" ($null -ne $rdsEndpoint -and $rdsEndpoint.Length -gt 0) $rdsEndpoint
    } catch {
        Test-Check "RDS endpoint" $false "could not read terraform output"
    }

    # 5. CloudWatch recent errors
    Write-Host "`n[5/5] CloudWatch Error Check (last 15 min)" -ForegroundColor Yellow
    try {
        $logGroup = "/ecs/iprs-$Environment"
        $startTime = [long]((Get-Date).AddMinutes(-15).ToUniversalTime() - [datetime]"1970-01-01T00:00:00Z").TotalMilliseconds
        $errors = aws logs filter-log-events --log-group-name $logGroup --filter-pattern "ERROR" --start-time $startTime --limit 5 --region $Region --output json 2>$null | ConvertFrom-Json
        $errorCount = ($errors.events | Measure-Object).Count
        if ($errorCount -eq 0) {
            Test-Check "No recent errors" $true
        } else {
            Test-Check "Recent errors found" $false "$errorCount error(s) in last 15 min"
            foreach ($evt in $errors.events) {
                Write-Host "    $($evt.message.Substring(0, [Math]::Min(120, $evt.message.Length)))" -ForegroundColor Gray
            }
        }
    } catch {
        Test-Check "CloudWatch check" $false "could not query logs"
    }
} else {
    Write-Host "`n[3/5] Skipping ECS checks (local deployment)" -ForegroundColor Yellow
    Write-Host "[4/5] Skipping RDS checks (local deployment)" -ForegroundColor Yellow
    Write-Host "[5/5] Skipping CloudWatch checks (local deployment)" -ForegroundColor Yellow
}

# Summary
$total = $passed + $failed
Write-Host "`n$('='*50)" -ForegroundColor Cyan
Write-Host "Verification: $passed/$total passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Red" })

if ($failed -gt 0) { exit 1 }
