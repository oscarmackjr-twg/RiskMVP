#!/usr/bin/env bash
# deploy-aws.sh — Full AWS deployment orchestrator for IPRS
# Usage: ./scripts/deploy-aws.sh [--region us-east-1] [--environment dev] [--auto-approve]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$ROOT/terraform"
REGION="us-east-1"
ENVIRONMENT="dev"
AUTO_APPROVE=false
SKIP_BUILD=false
DB_PASSWORD=""

for arg in "$@"; do
    case "$arg" in
        --region=*)      REGION="${arg#*=}" ;;
        --environment=*) ENVIRONMENT="${arg#*=}" ;;
        --db-password=*) DB_PASSWORD="${arg#*=}" ;;
        --auto-approve)  AUTO_APPROVE=true ;;
        --skip-build)    SKIP_BUILD=true ;;
    esac
done

echo "=== IPRS AWS Deployment ==="
echo "  Region:      $REGION"
echo "  Environment: $ENVIRONMENT"

# 1. Check prerequisites
echo -e "\n[1/8] Checking prerequisites..."
for cmd in aws terraform docker; do
    if ! command -v $cmd &>/dev/null; then
        echo "ERROR: '$cmd' not found. Install it first."
        exit 1
    fi
done

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  AWS Account: $ACCOUNT_ID"

if [ -z "$DB_PASSWORD" ]; then
    read -sp "Enter database master password: " DB_PASSWORD
    echo
fi

# 2-3. Terraform
echo -e "\n[2/8] Running Terraform init..."
cd "$TF_DIR"
terraform init -input=false

echo -e "\n[3/8] Running Terraform plan..."
terraform plan \
    -var="aws_region=$REGION" \
    -var="environment=$ENVIRONMENT" \
    -var="db_master_password=$DB_PASSWORD" \
    -out=tfplan

if [ "$AUTO_APPROVE" = false ]; then
    read -p "Apply this plan? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

echo -e "\n[4/8] Running Terraform apply..."
terraform apply tfplan

# 4. Extract outputs
echo -e "\n[5/8] Extracting Terraform outputs..."
ALB_DNS=$(terraform output -raw alb_dns_name)
RDS_ENDPOINT=$(terraform output -raw rds_proxy_endpoint)
echo "  ALB DNS:      $ALB_DNS"
echo "  RDS Endpoint: $RDS_ENDPOINT"
cd "$ROOT"

# 5. Build and push
if [ "$SKIP_BUILD" = false ]; then
    echo -e "\n[6/8] Building and pushing Docker images..."
    bash "$ROOT/scripts/build-images.sh"
    bash "$ROOT/scripts/push-ecr.sh" --account-id="$ACCOUNT_ID" --region="$REGION"
else
    echo -e "\n[6/8] Skipping build (--skip-build)"
fi

# 6. Migrations
echo -e "\n[7/8] Applying SQL migrations..."
DATABASE_URL="postgresql://postgres:${DB_PASSWORD}@${RDS_ENDPOINT}:5432/iprs" \
    bash "$ROOT/scripts/apply-migrations.sh"

# 7. Force new deployments
echo -e "\n[8/8] Forcing new ECS deployments..."
CLUSTER="iprs-cluster-$ENVIRONMENT"
SERVICES=(
    "iprs-marketdata-$ENVIRONMENT"
    "iprs-orchestrator-$ENVIRONMENT"
    "iprs-results-$ENVIRONMENT"
    "iprs-worker-$ENVIRONMENT"
    "iprs-portfolio-$ENVIRONMENT"
    "iprs-risk-$ENVIRONMENT"
    "iprs-regulatory-$ENVIRONMENT"
    "iprs-ingestion-$ENVIRONMENT"
)

for svc in "${SERVICES[@]}"; do
    echo "  Deploying $svc..."
    aws ecs update-service --cluster "$CLUSTER" --service "$svc" --force-new-deployment --region "$REGION" --output text > /dev/null 2>&1 || true
done

echo "  Waiting for services to stabilize..."
aws ecs wait services-stable --cluster "$CLUSTER" --services "${SERVICES[@]}" --region "$REGION" 2>/dev/null || true

echo -e "\n=== Deployment Complete ==="
echo "  ALB URL:  http://$ALB_DNS"
echo "  Database: $RDS_ENDPOINT"
echo ""
echo "Next steps:"
echo "  1. Smoke test:    python scripts/smoke-test.py --base-url http://$ALB_DNS"
echo "  2. Seed data:     python scripts/seed-market-data.py --fred-key KEY --base-url http://$ALB_DNS"
echo "  3. Verify:        ./scripts/verify-deployment.sh --alb-dns $ALB_DNS --region $REGION"
