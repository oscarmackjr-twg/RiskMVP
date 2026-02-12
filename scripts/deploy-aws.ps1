# deploy-aws.ps1 — Full AWS deployment orchestrator for IPRS
# Usage: .\scripts\deploy-aws.ps1 [-Region us-east-1] [-Environment dev] [-AutoApprove]
param(
    [string]$Region = "us-east-1",
    [string]$Environment = "dev",
    [string]$DbPassword = "",
    [switch]$AutoApprove,
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$TF_DIR = Join-Path $ROOT "terraform"

Write-Host "=== IPRS AWS Deployment ===" -ForegroundColor Cyan
Write-Host "  Region:      $Region"
Write-Host "  Environment: $Environment"

# 1. Check prerequisites
Write-Host "`n[1/8] Checking prerequisites..." -ForegroundColor Yellow
$missing = @()
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) { $missing += "aws" }
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) { $missing += "terraform" }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { $missing += "docker" }
if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}

# Verify AWS identity
$identity = aws sts get-caller-identity --output json 2>$null | ConvertFrom-Json
if (-not $identity) {
    Write-Host "ERROR: AWS credentials not configured. Run 'aws configure'." -ForegroundColor Red
    exit 1
}
$AccountId = $identity.Account
Write-Host "  AWS Account: $AccountId" -ForegroundColor Green
Write-Host "  AWS User:    $($identity.Arn)" -ForegroundColor Green

# Prompt for DB password if not provided
if (-not $DbPassword) {
    $DbPassword = Read-Host -Prompt "Enter database master password" -AsSecureString
    $DbPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($DbPassword))
}

# 2. Terraform init + plan
Write-Host "`n[2/8] Running Terraform init..." -ForegroundColor Yellow
Push-Location $TF_DIR
try {
    terraform init -input=false
    if ($LASTEXITCODE -ne 0) { throw "terraform init failed" }

    Write-Host "`n[3/8] Running Terraform plan..." -ForegroundColor Yellow
    terraform plan `
        -var="aws_region=$Region" `
        -var="environment=$Environment" `
        -var="db_master_password=$DbPassword" `
        -out=tfplan
    if ($LASTEXITCODE -ne 0) { throw "terraform plan failed" }

    # 3. Confirm and apply
    if (-not $AutoApprove) {
        $confirm = Read-Host "`nApply this plan? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Host "Deployment cancelled." -ForegroundColor Yellow
            exit 0
        }
    }

    Write-Host "`n[4/8] Running Terraform apply..." -ForegroundColor Yellow
    terraform apply tfplan
    if ($LASTEXITCODE -ne 0) { throw "terraform apply failed" }

    # 4. Extract outputs
    Write-Host "`n[5/8] Extracting Terraform outputs..." -ForegroundColor Yellow
    $ALB_DNS = (terraform output -raw alb_dns_name)
    $RDS_ENDPOINT = (terraform output -raw rds_proxy_endpoint)
    Write-Host "  ALB DNS:      $ALB_DNS" -ForegroundColor Green
    Write-Host "  RDS Endpoint: $RDS_ENDPOINT" -ForegroundColor Green
} finally {
    Pop-Location
}

# 5. Build and push images
if (-not $SkipBuild) {
    Write-Host "`n[6/8] Building and pushing Docker images..." -ForegroundColor Yellow
    & "$ROOT\scripts\build-images.ps1"
    & "$ROOT\scripts\push-ecr.ps1" -AccountId $AccountId -Region $Region
} else {
    Write-Host "`n[6/8] Skipping build (--SkipBuild)" -ForegroundColor Yellow
}

# 6. Apply migrations
Write-Host "`n[7/8] Applying SQL migrations..." -ForegroundColor Yellow
$DB_URL = "postgresql://postgres:${DbPassword}@${RDS_ENDPOINT}:5432/iprs"
& "$ROOT\scripts\apply-migrations.ps1" -DatabaseUrl $DB_URL

# 7. Force new ECS deployments
Write-Host "`n[8/8] Forcing new ECS deployments..." -ForegroundColor Yellow
$CLUSTER = "iprs-cluster-$Environment"
$ECS_SERVICES = @(
    "iprs-marketdata-$Environment",
    "iprs-orchestrator-$Environment",
    "iprs-results-$Environment",
    "iprs-worker-$Environment",
    "iprs-portfolio-$Environment",
    "iprs-risk-$Environment",
    "iprs-regulatory-$Environment",
    "iprs-ingestion-$Environment"
)

foreach ($svc in $ECS_SERVICES) {
    Write-Host "  Deploying $svc..." -ForegroundColor Gray
    aws ecs update-service --cluster $CLUSTER --service $svc --force-new-deployment --region $Region --output text > $null 2>&1
}

# Wait for stabilization
Write-Host "`n  Waiting for services to stabilize (up to 5 min)..." -ForegroundColor Yellow
aws ecs wait services-stable --cluster $CLUSTER --services $ECS_SERVICES --region $Region 2>$null

# Summary
Write-Host "`n=== Deployment Complete ===" -ForegroundColor Cyan
Write-Host "  ALB URL:  http://$ALB_DNS" -ForegroundColor Green
Write-Host "  Database: $RDS_ENDPOINT" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run smoke test:  python scripts/smoke-test.py --base-url http://$ALB_DNS"
Write-Host "  2. Seed market data: python scripts/seed-market-data.py --fred-key KEY --base-url http://$ALB_DNS"
Write-Host "  3. Verify:          .\scripts\verify-deployment.ps1 -AlbDns $ALB_DNS -Region $Region"
