# Architecture

**Analysis Date:** 2026-02-11

## Pattern Overview

**Overall:** Distributed compute with fanout task queue pattern.

**Key Characteristics:**
- Multi-service microservice architecture with independent REST APIs
- Asynchronous work distribution via database-backed task queue
- Product-type and hash-bucket sharding for parallel processing
- JSONB-heavy PostgreSQL for flexible payloads and audit trails
- Pluggable pricer system for instrument valuation

## Layers

**API Layer (HTTP):**
- Purpose: REST entry points for run creation, market data, and results queries
- Location: `services/marketdata_svc/app/main.py`, `services/run_orchestrator/app/main.py`, `services/results_api/app/main.py`
- Contains: FastAPI route handlers, Pydantic request/response models
- Depends on: Database layer (via `services/common/db.py`)
- Used by: Frontend (React), external systems

**Orchestration Layer:**
- Purpose: Run lifecycle management and task fanout strategy
- Location: `services/run_orchestrator/app/main.py` (lines 226-314)
- Contains: Run creation logic, position snapshot loading, task generation by product_type and hash bucket
- Depends on: Position snapshots, market data snapshots
- Used by: Task workers, results queries

**Worker/Compute Layer:**
- Purpose: Claims and executes pricing tasks from queue
- Location: `compute/worker/worker.py`
- Contains: Task claiming with lease-based locking, instrument pricing, result persistence
- Depends on: Pricer implementations, quantlib, database
- Used by: Orchestrator (via queue)

**Pricer Layer:**
- Purpose: Instrument-specific valuation logic
- Location: `compute/pricers/` (base class in `base.py`, implementations: `bond.py`, `fx_fwd.py`, `loan.py`)
- Contains: Product-specific pricing algorithms, measure computation (PV, DV01, FX_DELTA)
- Depends on: Quantlib (curves, scenarios, calendar)
- Used by: Worker dispatch (lines 184-190 of worker.py)

**Quantlib/Math Layer:**
- Purpose: Market data manipulation and financial mathematics
- Location: `compute/quantlib/`
- Contains: Zero curve interpolation, discount factor calculation, scenario application, FX conversions, day count conventions
- Depends on: None (leaf dependency)
- Used by: All pricers

**Database Layer:**
- Purpose: ACID persistence for runs, tasks, results, market data, positions
- Location: `services/common/db.py` (connection factory)
- Contains: PostgreSQL connection management via psycopg3, dict_row factory
- Depends on: PostgreSQL database at DATABASE_URL env var
- Used by: All services and worker

**Frontend Layer:**
- Purpose: User-facing UI for run submission and result visualization
- Location: `frontend/src/` (React 18 + TypeScript)
- Contains: Page components (RunLauncherPage, RunResultsPage, RunCubePage), API client
- Depends on: Orchestrator and Results APIs (via `frontend/src/api.ts`)
- Used by: End users

## Data Flow

**Run Creation & Task Fanout:**

1. Frontend calls `/api/v1/runs` on orchestrator (RunLauncherPage -> api.ts -> POST /api/v1/runs)
2. Orchestrator loads position snapshot by ID or uses default (lines 240-256 of main.py)
3. Orchestrator extracts product_types from positions, determines hash_mod buckets
4. Orchestrator inserts run record with QUEUED status
5. Orchestrator inserts position snapshot (upserted for idempotency)
6. Orchestrator creates tasks: one per (product_type, hash_bucket) combination (lines 299-312 of main.py)
7. Tasks inserted into run_task table with QUEUED status

**Worker Task Processing:**

1. Worker polls run_task table for QUEUED or expired RUNNING tasks (claim_task, worker.py:119-134)
2. Worker acquires task with SELECT...FOR UPDATE to prevent concurrent claims
3. Worker updates task status to RUNNING and sets lease_until timestamp
4. Worker loads: run context, market snapshot, position snapshot
5. Worker filters positions by task.product_type and hash_bucket (lines 231-235)
6. Worker iterates scenarios x positions, calling price_position dispatch (lines 237-251)
7. Pricer computes measures for (position, scenario) pair
8. Worker inserts valuation_result with computed measures as JSON (line 283)
9. Worker marks task SUCCEEDED on completion
10. On failure: Worker marks task FAILED or DEAD (based on attempt count), may requeue

**Results Retrieval:**

1. Frontend polls Results API `/api/v1/results/{runId}/summary` (RunResultsPage, lines 20-30)
2. Results API queries valuation_result table grouped by scenario, sums PV and counts
3. User clicks "Drill Down" to view `/api/v1/results/{runId}/cube?by=product_type&scenario_id=BASE`
4. Results API groups measures by product_type or portfolio_node_id, returns drill-down view

**State Management:**

- **Run State:** In `run` table (QUEUED → RUNNING → COMPLETED/FAILED/PUBLISHED)
- **Task State:** In `run_task` table (QUEUED → RUNNING → SUCCEEDED/FAILED/DEAD)
- **Position State:** Snapshots in `position_snapshot` table (immutable, content-addressed by hash)
- **Market State:** Snapshots in `marketdata_snapshot` table (immutable, vendor-timestamped)
- **Results State:** In `valuation_result` table (append-only, deduped by run_id + position_id + scenario_id via ON CONFLICT)

## Key Abstractions

**Task:**
- Purpose: Atomic unit of work (product_type + hash_bucket for a run)
- Examples: `TASK-RUN-2026-01-23-FX_FWD-0`, `TASK-RUN-2026-01-23-FIXED_BOND-0`
- Pattern: Dataclass defined worker.py:28-37, identifies shard of positions to price

**Pricer:**
- Purpose: Product-type-specific pricing algorithm
- Examples: `compute.pricers.bond.price_bond()`, `compute.pricers.fx_fwd.price_fx_fwd()`, `compute.pricers.loan.price_loan()`
- Pattern: Free functions with signature (position, instrument, market_snapshot, measures, scenario_id) -> Dict[str, float]
- Base class: `compute.pricers.base.AbstractPricer` (defines interface, not enforced in MVP)

**Scenario:**
- Purpose: Market perturbation for sensitivity analysis
- Examples: "BASE" (baseline), "RATES_PARALLEL_1BP" (parallel rates shock), "SPREAD_25BP" (spread shock), "FX_SPOT_1PCT"
- Pattern: Apply via `compute.quantlib.scenarios.apply_scenario(snapshot, scenario_id)` which deepcopies and bumps rates/spots

**Snapshot (Position & Market Data):**
- Purpose: Immutable, versioned state for reproducibility
- Examples: Position snapshot at as_of_time with positions array, Market data snapshot with curves and FX spots
- Pattern: Content-addressed by SHA256 hash, stored as JSONB in PostgreSQL for flexible schema

**Measure:**
- Purpose: Computed output of pricing (e.g., PV, DV01, FX_DELTA, ACCRUED_INTEREST)
- Pattern: String identifier, computed per (position, scenario), stored as JSON in valuation_result.measures_json

## Entry Points

**Marketdata Service (`services/marketdata_svc/app/main.py`):**
- Location: `services/marketdata_svc/app/main.py:11`
- Triggers: `uvicorn services.marketdata_svc.app.main:app --reload --port 8001`
- Responsibilities: Create/retrieve market data snapshots (curves, FX spots), validate data quality

**Run Orchestrator (`services/run_orchestrator/app/main.py`):**
- Location: `services/run_orchestrator/app/main.py:81`
- Triggers: `uvicorn services.run_orchestrator.app.main:app --reload --port 8002`
- Responsibilities: Create runs, fanout tasks by product type and hash bucket, track run/task lifecycle

**Results API (`services/results_api/app/main.py`):**
- Location: `services/results_api/app/main.py:7`
- Triggers: `uvicorn services.results_api.app.main:app --reload --port 8003`
- Responsibilities: Query and aggregate valuation results by scenario, support drill-down analysis (by product_type or portfolio_node_id)

**Worker (`compute/worker/worker.py`):**
- Location: `compute/worker/worker.py:192` (worker_main function)
- Triggers: `python -m compute.worker.worker` (calls worker_main() at line 309)
- Responsibilities: Claim tasks from queue, load snapshots, dispatch to pricers, persist results, handle retries with configurable lease times

**Frontend (`frontend/src/main.tsx`):**
- Location: `frontend/src/main.tsx:17`
- Triggers: `npm run dev` or `npm run build`
- Responsibilities: React application root, establishes React Query client, routing, UI for run submission and results

## Error Handling

**Strategy:** Pragmatic error recovery via task retry with exponential backoff (simple: attempt count check).

**Patterns:**

- **Transient Failures:** Task marked FAILED, can be manually requeued via database update
- **Persistent Failures:** Task marked DEAD after max_attempts exceeded (default 3)
- **Worker Lease Expiry:** Tasks with expired leased_until timestamps are eligible for reclaim
- **Database Errors:** Caught at service layer, returned as HTTP 500 with error detail
- **Pricer Exceptions:** Caught in worker main loop (line 294), task marked FAILED with error text truncated to 5000 chars

## Cross-Cutting Concerns

**Logging:** Console prints via Python print() at key workflow points (worker.py lines 193, 210, 292, 296). Frontend uses browser console. No centralized log aggregation in MVP.

**Validation:**

- Pydantic models enforce request schema (RunRequestedV1, MarketDataSnapshotV1, PositionSnapshotIn)
- Worker validates position array presence and product_type presence (main.py lines 260-266)
- Pricer-specific validation: Bond pricer requires explicit cashflows (bond.py line 28)

**Authentication:** Not implemented in MVP. All services assume trusted internal calls (tenant_id hardcoded to 'INTERNAL').

**Deterministic Hashing:** SHA256 hashing used throughout for idempotency:
- Position snapshot payload hash for deduplication (marketdata_svc line 63-65)
- Input hash for result deduplication (worker.py lines 263-269)
- Product type + position_id hash for sharding into buckets (worker.py line 164)

---

*Architecture analysis: 2026-02-11*
