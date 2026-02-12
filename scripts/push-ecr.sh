#!/usr/bin/env bash
# push-ecr.sh — Tag and push all IPRS Docker images to AWS ECR
# Usage: ./scripts/push-ecr.sh --account-id 123456789012 [--region us-east-1] [--tag latest]
set -euo pipefail

ACCOUNT_ID=""
REGION="us-east-1"
TAG="latest"
PROJECT="iprs"

for arg in "$@"; do
    case "$arg" in
        --account-id=*) ACCOUNT_ID="${arg#*=}" ;;
        --region=*)     REGION="${arg#*=}" ;;
        --tag=*)        TAG="${arg#*=}" ;;
        --project=*)    PROJECT="${arg#*=}" ;;
    esac
done

if [ -z "$ACCOUNT_ID" ]; then
    echo "ERROR: --account-id is required"
    echo "Usage: ./scripts/push-ecr.sh --account-id=123456789012"
    exit 1
fi

ECR_BASE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
echo "=== Pushing IPRS Images to ECR ==="

# 1. Authenticate
echo -e "\n[1/3] Authenticating to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_BASE"
echo "  ECR auth: OK"

# 2. Tag and push
echo -e "\n[2/3] Tagging and pushing images..."
services=(marketdata orchestrator results worker portfolio risk regulatory ingestion frontend)
failed=0

for svc in "${services[@]}"; do
    local_tag="iprs-${svc}:${TAG}"
    ecr_tag="${ECR_BASE}/${PROJECT}-${svc}:${TAG}"

    echo "  Pushing ${svc}..."
    if docker tag "$local_tag" "$ecr_tag" && docker push "$ecr_tag"; then
        echo "    ${svc}: OK"
    else
        echo "    ${svc}: FAILED"
        failed=$((failed + 1))
    fi
done

# 3. Summary
echo -e "\n[3/3] Push Summary"
if [ $failed -gt 0 ]; then
    echo "${failed} image(s) failed to push."
    exit 1
fi
echo "All images pushed to ${ECR_BASE}"
