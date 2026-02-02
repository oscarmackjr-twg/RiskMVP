# CLAUDE.md - Risk MVP (IPRS)

## Project Overview

A distributed financial risk computation engine for instrument valuation. Core workflow:
1. Create market data snapshot (curves, FX spots)
2. Submit run request with portfolio scope and measures
3. Orchestrator fans out tasks by product type and hash bucket
4. Workers claim tasks, price positions, write results
5. Results API aggregates for drill-down analysis

## Tech Stack

**Backend (Python 3.11+)**
- FastAPI for REST services
- psycopg (v3) for PostgreSQL
- pytest for testing

**Frontend**
- React 18 + TypeScript
- React Query for data fetching
- Vite for dev/build

**Database**
- PostgreSQL with JSONB for flexible payloads

## Directory Structure

```
compute/              # Pricing engine & worker
  pricers/            # FX_FWD, AMORT_LOAN, FIXED_BOND pricers
  quantlib/           # Curve interpolation, scenario application
  worker/             # Distributed task processor
  tests/              # Golden tests with expected values

services/             # FastAPI microservices
  marketdata_svc/     # Port 8001 - snapshot upload/retrieval
  run_orchestrator/   # Port 8002 - run creation, task fanout
  results_api/        # Port 8003 - result queries
  common/             # Shared DB utilities

frontend/             # React UI
  src/pages/          # RunLauncher, RunResults, RunCube views

contracts/            # JSON schemas and fixtures
  domains/            # Data contracts (strict schemas)
  fixtures/           # Test data

sql/                  # PostgreSQL DDL
demo/                 # Sample data for demos
```

## Essential Commands

### Backend Setup
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -e .
pip install fastapi uvicorn
```

### Run Tests
```bash
pytest -q
pytest compute/tests/
```

### Start Services (PowerShell)
```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iprs"
uvicorn services.marketdata_svc.app.main:app --reload --port 8001
uvicorn services.run_orchestrator.app.main:app --reload --port 8002
uvicorn services.results_api.app.main:app --reload --port 8003
```

### Start Worker
```bash
python -m compute.worker.worker
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Dev server with API proxy
npm run build    # Production build
```

### Database
Initialize with: `sql/001_mvp_core.sql`

## Key Entry Points

| Component | File | Entry |
|-----------|------|-------|
| Marketdata Service | `services/marketdata_svc/app/main.py` | `app` |
| Run Orchestrator | `services/run_orchestrator/app/main.py` | `app` |
| Results API | `services/results_api/app/main.py` | `app` |
| Worker | `compute/worker/worker.py:192` | `worker_main()` |
| Frontend | `frontend/src/main.tsx` | React root |

## Core Concepts

**Run**: A batch valuation request specifying market snapshot, positions, measures, and scenarios.

**Task**: A unit of work for the worker (product_type + hash_bucket slice of positions).

**Measures**: Computed values like `PV`, `DV01`, `FX_DELTA`, `ACCRUED_INTEREST`.

**Scenarios**: Market perturbations (`BASE`, `RATES_PARALLEL_1BP`, `SPREAD_25BP`, `FX_SPOT_1PCT`).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/iprs` | PostgreSQL connection |
| `WORKER_ID` | `worker-1` | Worker instance identifier |
| `WORKER_LEASE_SECONDS` | `60` | Task lease duration |
| `RUN_TASK_HASH_MOD` | `1` | Number of hash buckets |
| `POSITIONS_SNAPSHOT_PATH` | `demo/inputs/positions.json` | Default positions file |

## Additional Documentation

When working on specific areas, consult:

| Topic | File |
|-------|------|
| Architectural patterns | `.claude/docs/architectural_patterns.md` |
| Data contracts | `contracts/README.md` |
| Services overview | `services/README_SERVICES.md` |
| Frontend setup | `frontend/README.md` |

## Quick Reference

- Add new pricer: Create module in `compute/pricers/`, add dispatch in `compute/worker/worker.py:184-190`
- Add new scenario: Extend `compute/quantlib/scenarios.py:5-31`
- Add new measure: Update pricer to compute it, add to run request `measures[]`
- Database changes: Add migration to `sql/` directory
