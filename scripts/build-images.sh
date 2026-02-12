#!/usr/bin/env bash
# build-images.sh — Build all IPRS Docker images with commit SHA tags
# Usage: ./scripts/build-images.sh [--tag TAG]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG=""

for arg in "$@"; do
    case "$arg" in
        --tag=*) TAG="${arg#*=}" ;;
    esac
done

if [ -z "$TAG" ]; then
    TAG=$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo "latest")
fi

echo "=== Building IPRS Docker Images (tag: $TAG) ==="

declare -A images=(
    ["iprs-marketdata"]="docker/Dockerfile.marketdata"
    ["iprs-orchestrator"]="docker/Dockerfile.orchestrator"
    ["iprs-results"]="docker/Dockerfile.results"
    ["iprs-worker"]="docker/Dockerfile.worker"
    ["iprs-portfolio"]="docker/Dockerfile.portfolio"
    ["iprs-risk"]="docker/Dockerfile.risk"
    ["iprs-regulatory"]="docker/Dockerfile.regulatory"
    ["iprs-ingestion"]="docker/Dockerfile.ingestion"
    ["iprs-frontend"]="docker/Dockerfile.frontend"
)

failed=0
for name in "${!images[@]}"; do
    dockerfile="${images[$name]}"
    echo -e "\nBuilding ${name}..."
    if docker build -t "${name}:${TAG}" -t "${name}:latest" -f "$ROOT/${dockerfile}" "$ROOT"; then
        echo "  ${name}: OK"
    else
        echo "  ${name}: FAILED"
        failed=$((failed + 1))
    fi
done

echo -e "\n=== Build Summary ==="
if [ $failed -gt 0 ]; then
    echo "${failed} image(s) failed to build."
    exit 1
fi
echo "All ${#images[@]} images built successfully."
