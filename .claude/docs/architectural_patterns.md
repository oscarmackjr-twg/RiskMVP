# Architectural Patterns

## Distributed Task Processing

The system uses a lease-based task queue pattern for distributed computation:
- Tasks are claimed with `FOR UPDATE SKIP LOCKED` preventing double-processing (`compute/worker/worker.py:39-58`)
- Lease timeout enables automatic recovery of stalled tasks (`run_task.leased_until` column)
- Failed tasks are requeued up to `max_attempts` before marked `DEAD`
- Sharding: Tasks fan out by `(product_type, hash_bucket)` for parallelization

## Immutable Snapshots

Market data and positions are stored as immutable snapshots:
- `marketdata_snapshot` and `position_snapshot` tables contain full `payload_json` JSONB
- Each snapshot has a `payload_hash` (SHA-256) for deduplication and audit
- Snapshots are referenced by ID from runs/tasks, never modified after creation
- See `sql/001_mvp_core.sql:31-55` for schema

## Content-Addressable Hashing

SHA-256 hashing is used throughout for idempotency and audit:
- `sha256_json()` pattern: `json.dumps(obj, sort_keys=True, separators=(",", ":"))` + hash
- Used in: `compute/worker/worker.py:24-26`, `services/run_orchestrator/app/main.py:13-15`
- Valuation results store `input_hash` for reproducibility verification

## Pricer Strategy Pattern

Pricers are selected dynamically based on `product_type`:
- Dispatch logic in `compute/worker/worker.py:171-190`
- Each pricer module has uniform signature: `price_*(position, instrument, market_snapshot, measures, scenario_id)`
- Supported: `FX_FWD`, `AMORT_LOAN`, `FIXED_BOND`
- Pricers located in `compute/pricers/`

## Scenario Application

Market scenarios are applied via copy-and-modify:
- `apply_scenario()` deep-copies snapshot and applies bumps (`compute/quantlib/scenarios.py:5-31`)
- Predefined scenarios: `BASE`, `RATES_PARALLEL_1BP`, `SPREAD_25BP`, `FX_SPOT_1PCT`
- Scenario bumps modify curve nodes or FX spots in-place on the copy

## UPSERT Idempotency

All write operations use `ON CONFLICT ... DO UPDATE` for idempotency:
- Run creation: `ON CONFLICT (run_id) DO NOTHING`
- Position snapshots: `ON CONFLICT (position_snapshot_id) DO UPDATE`
- Valuation results: `ON CONFLICT (run_id, position_id, scenario_id) DO UPDATE`
- Enables safe retries without duplicates

## Database Transaction Pattern

Services use a shared context manager for transaction handling:
- `db_conn()` context manager in `services/common/db.py:9-18`
- Auto-commit=False, explicit commit on success, rollback on exception
- All services use `psycopg` with `dict_row` factory for dict-based row access

## Frontend API Proxy

The React frontend proxies API calls to avoid CORS:
- Vite dev server rewrites paths: `/mkt/*`, `/orch/*`, `/results/*`
- Maps to backend ports 8001, 8002, 8003 respectively
- Configuration in `frontend/vite.config.ts:11-28`

## Data Contract Versioning

JSON schemas define strict contracts with versioning rules:
- Schemas in `contracts/domains/` with `additionalProperties: false`
- Additive changes only; no field removal or type changes
- Fixtures for testing in `contracts/fixtures/`
- See `contracts/README.md` for rules

## Instrument Embedding

For MVP, instruments are embedded within position payloads:
- `position.attributes.instrument` contains full instrument JSON
- Avoids separate lookup during valuation
- Pattern noted in `compute/worker/worker.py:168-169`

## Measure-Based Valuation

Pricers compute only requested measures:
- Measures passed as list: `["PV", "DV01", "FX_DELTA", "ACCRUED_INTEREST"]`
- Each pricer checks which measures are requested before computing
- Sensitivity measures (DV01) apply bumped scenarios internally
- See `compute/pricers/fx_fwd.py:42-51` for pattern
