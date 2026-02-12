#!/usr/bin/env bash
# verify-deployment.sh — Post-deployment verification for IPRS
# Usage: ./scripts/verify-deployment.sh [--alb-dns my-alb.elb.amazonaws.com] [--region us-east-1]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ALB_DNS="localhost"
REGION="us-east-1"
ENVIRONMENT="dev"

for arg in "$@"; do
    case "$arg" in
        --alb-dns=*)     ALB_DNS="${arg#*=}" ;;
        --region=*)      REGION="${arg#*=}" ;;
        --environment=*) ENVIRONMENT="${arg#*=}" ;;
    esac
done

CLUSTER="iprs-cluster-$ENVIRONMENT"
passed=0
failed=0

check() {
    local name="$1" ok="$2" detail="${3:-}"
    if [ "$ok" = "true" ]; then
        echo "  PASS: $name"
        passed=$((passed + 1))
    else
        echo "  FAIL: $name${detail:+ - $detail}"
        failed=$((failed + 1))
    fi
}

echo "=== IPRS Deployment Verification ==="
echo "  Target: $ALB_DNS"
echo "  Region: $REGION"

# 1. Health checks
echo -e "\n[1/5] Service Health Checks"
declare -A svc_ports=( ["marketdata"]=8001 ["orchestrator"]=8002 ["results"]=8003
    ["portfolio"]=8005 ["risk"]=8006 ["regulatory"]=8007 ["ingestion"]=8008 )

for svc in marketdata orchestrator results portfolio risk regulatory ingestion; do
    port=${svc_ports[$svc]}
    if [ "$ALB_DNS" = "localhost" ]; then
        url="http://localhost:${port}/health"
    else
        prefix="${svc:0:3}"
        url="http://${ALB_DNS}/${prefix}/health"
    fi
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        check "$svc health" "true"
    else
        check "$svc health" "false" "unreachable"
    fi
done

# 2. Smoke test
echo -e "\n[2/5] Running Smoke Test"
if python "$ROOT/scripts/smoke-test.py" --base-url "http://$ALB_DNS" --skip-run > /dev/null 2>&1; then
    check "Smoke test" "true"
else
    check "Smoke test" "false"
fi

# 3-5. AWS-specific checks
if [ "$ALB_DNS" != "localhost" ]; then
    echo -e "\n[3/5] ECS Service Status"
    for svc in marketdata orchestrator results worker portfolio risk regulatory ingestion; do
        svc_name="iprs-${svc}-${ENVIRONMENT}"
        desc=$(aws ecs describe-services --cluster "$CLUSTER" --services "$svc_name" --region "$REGION" --output json 2>/dev/null)
        if [ $? -eq 0 ]; then
            running=$(echo "$desc" | python -c "import sys,json; print(json.load(sys.stdin)['services'][0]['runningCount'])" 2>/dev/null || echo 0)
            desired=$(echo "$desc" | python -c "import sys,json; print(json.load(sys.stdin)['services'][0]['desiredCount'])" 2>/dev/null || echo 0)
            ok="false"
            [ "$running" = "$desired" ] && [ "$desired" -gt 0 ] && ok="true"
            check "$svc ECS ($running/$desired)" "$ok"
        else
            check "$svc ECS" "false" "could not describe service"
        fi
    done

    echo -e "\n[4/5] RDS Connectivity"
    rds_endpoint=$(cd "$ROOT/terraform" && terraform output -raw rds_proxy_endpoint 2>/dev/null || echo "")
    if [ -n "$rds_endpoint" ]; then
        check "RDS endpoint" "true" "$rds_endpoint"
    else
        check "RDS endpoint" "false" "could not read terraform output"
    fi

    echo -e "\n[5/5] CloudWatch Error Check (last 15 min)"
    log_group="/ecs/iprs-$ENVIRONMENT"
    start_time=$(python -c "import time; print(int((time.time()-900)*1000))" 2>/dev/null || echo 0)
    error_count=$(aws logs filter-log-events --log-group-name "$log_group" --filter-pattern "ERROR" --start-time "$start_time" --limit 5 --region "$REGION" --output json 2>/dev/null | python -c "import sys,json; print(len(json.load(sys.stdin).get('events',[])))" 2>/dev/null || echo "?")
    if [ "$error_count" = "0" ]; then
        check "No recent errors" "true"
    else
        check "Recent errors" "false" "$error_count error(s)"
    fi
else
    echo -e "\n[3/5] Skipping ECS checks (local)"
    echo "[4/5] Skipping RDS checks (local)"
    echo "[5/5] Skipping CloudWatch checks (local)"
fi

# Summary
total=$((passed + failed))
echo ""
echo "=================================================="
echo "Verification: $passed/$total passed, $failed failed"

[ $failed -gt 0 ] && exit 1
exit 0
