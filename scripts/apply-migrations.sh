#!/usr/bin/env bash
# apply-migrations.sh — Apply SQL migrations to PostgreSQL
# Usage: ./scripts/apply-migrations.sh [--database-url "postgresql://..."]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@localhost:5432/iprs}"

for arg in "$@"; do
    case "$arg" in
        --database-url=*) DATABASE_URL="${arg#*=}" ;;
    esac
done

echo "=== Applying IPRS SQL Migrations ==="

# Check for psql
if ! command -v psql &>/dev/null; then
    echo "ERROR: psql not found. Install PostgreSQL client tools."
    echo "  macOS: brew install libpq"
    echo "  Ubuntu: sudo apt install postgresql-client"
    echo "  Or use Docker: docker exec -i iprs-db psql ..."
    exit 1
fi

migrations=(
    "001_mvp_core.sql|Core schema (runs, tasks, results, market data)"
    "002_portfolio_data_services.sql|Portfolio, positions, instruments, reference data"
    "003_regulatory_analytics.sql|CECL, Basel, audit trail, regulatory reports"
)

for entry in "${migrations[@]}"; do
    file="${entry%%|*}"
    desc="${entry#*|}"
    path="$ROOT/sql/$file"

    if [ ! -f "$path" ]; then
        echo "  SKIP: $file (not found)"
        continue
    fi

    echo -e "\nApplying $file..."
    echo "  $desc"

    if psql "$DATABASE_URL" -f "$path" -v ON_ERROR_STOP=1 > /dev/null 2>&1; then
        echo "  OK: $file"
    else
        echo "  FAILED: $file (may be OK if already applied)"
    fi
done

# Verify
echo -e "\nVerifying schema..."
table_count=$(psql "$DATABASE_URL" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null | tr -d ' ')
echo "  Tables in public schema: $table_count"

echo -e "\n=== Migrations Complete ==="
