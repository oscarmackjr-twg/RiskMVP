#!/usr/bin/env bash
# setup-local.sh — Bootstrap IPRS locally via Docker Compose
# Usage: ./scripts/setup-local.sh [--skip-build]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_BUILD=false
TIMEOUT=120

for arg in "$@"; do
    case "$arg" in
        --skip-build) SKIP_BUILD=true ;;
        --timeout=*) TIMEOUT="${arg#*=}" ;;
    esac
done

echo "=== IPRS Local Setup ==="

# 1. Check prerequisites
echo -e "\n[1/5] Checking prerequisites..."
missing=()
command -v docker &>/dev/null || missing+=("docker")
(docker compose version &>/dev/null || command -v docker-compose &>/dev/null) || missing+=("docker compose")
if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: Missing prerequisites: ${missing[*]}"
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo "  Docker: OK"

# 2. Build images
if [ "$SKIP_BUILD" = false ]; then
    echo -e "\n[2/5] Building Docker images (this may take a few minutes)..."
    docker compose -f "$ROOT/docker/docker-compose.yml" build
    echo "  Build: OK"
else
    echo -e "\n[2/5] Skipping build (--skip-build)"
fi

# 3. Start all services
echo -e "\n[3/5] Starting services..."
docker compose -f "$ROOT/docker/docker-compose.yml" up -d

# 4. Wait for database health
echo -e "\n[4/5] Waiting for database to be ready..."
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    health=$(docker inspect --format='{{.State.Health.Status}}' iprs-db 2>/dev/null || echo "unknown")
    if [ "$health" = "healthy" ]; then
        echo "  Database: healthy"
        break
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "  Waiting... (${elapsed}s)"
done
if [ $elapsed -ge $TIMEOUT ]; then
    echo "ERROR: Database did not become healthy within ${TIMEOUT}s"
    exit 1
fi

# 5. Verify all services
echo -e "\n[5/5] Verifying services..."
sleep 5

declare -A svc_ports=(
    ["marketdata"]=8001
    ["orchestrator"]=8002
    ["results"]=8003
    ["portfolio"]=8005
    ["risk"]=8006
    ["regulatory"]=8007
    ["ingestion"]=8008
    ["frontend"]=80
)

all_ok=true
for svc in marketdata orchestrator results portfolio risk regulatory ingestion frontend; do
    port=${svc_ports[$svc]}
    url="http://localhost:${port}/health"
    [ "$svc" = "frontend" ] && url="http://localhost:${port}/"
    if curl -sf --max-time 5 "$url" > /dev/null 2>&1; then
        echo "  ${svc} (port ${port}): OK"
    else
        echo "  ${svc} (port ${port}): FAILED"
        all_ok=false
    fi
done

# Summary
echo -e "\n=== Setup Complete ==="
echo "Service URLs:"
echo "  Frontend:     http://localhost"
echo "  Marketdata:   http://localhost:8001"
echo "  Orchestrator: http://localhost:8002"
echo "  Results API:  http://localhost:8003"
echo "  Portfolio:    http://localhost:8005"
echo "  Risk:         http://localhost:8006"
echo "  Regulatory:   http://localhost:8007"
echo "  Ingestion:    http://localhost:8008"
echo "  PostgreSQL:   localhost:5432 (postgres/postgres)"
echo ""
echo "Next steps:"
echo "  1. Load market data:  python scripts/seed-market-data.py --fred-key YOUR_KEY"
echo "  2. Run smoke tests:   python scripts/smoke-test.py"
echo "  3. Open frontend:     http://localhost"

if [ "$all_ok" = false ]; then
    echo ""
    echo "WARNING: Some services failed health checks. Check logs with:"
    echo "  docker compose -f docker/docker-compose.yml logs <service-name>"
    exit 1
fi
