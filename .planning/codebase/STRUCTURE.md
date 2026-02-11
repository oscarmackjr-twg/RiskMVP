# Codebase Structure

**Analysis Date:** 2026-02-11

## Directory Layout

```
riskmvp/
├── compute/                    # Pricing engine, worker, quantlib
│   ├── __init__.py
│   ├── pricers/                # Instrument-specific valuations
│   │   ├── base.py             # AbstractPricer interface
│   │   ├── bond.py             # Fixed bond pricing
│   │   ├── fx_fwd.py           # FX forward pricing
│   │   ├── loan.py             # Amortizing loan pricing
│   │   ├── callable_bond.py    # Callable bond (future)
│   │   ├── putable_bond.py     # Putable bond (future)
│   │   ├── abs_mbs.py          # ABS/MBS (future)
│   │   ├── floating_rate.py    # Floating rate notes (future)
│   │   ├── derivatives.py      # Derivatives (future)
│   │   └── registry.py         # Pricer dispatch registry
│   ├── quantlib/               # Financial mathematics
│   │   ├── curve.py            # Zero curve with linear interpolation
│   │   ├── curve_builder.py    # Multi-curve bootstrapping (stub)
│   │   ├── scenarios.py        # Market shock application
│   │   ├── interpolation.py    # Interpolation methods
│   │   ├── day_count.py        # Day count conventions
│   │   ├── fx.py               # FX conversions and forwards
│   │   ├── calendar.py         # Business day adjustments
│   │   └── tenors.py           # Tenor parsing utilities
│   ├── cashflow/               # Cashflow generation (future)
│   ├── performance/            # Performance monitoring (future)
│   ├── regulatory/             # Regulatory metrics (future)
│   ├── risk/                   # Risk measures (future)
│   │   ├── credit/             # Credit risk
│   │   ├── liquidity/          # Liquidity risk
│   │   └── market/             # Market risk
│   ├── worker/                 # Distributed task processor
│   │   ├── __init__.py
│   │   └── worker.py           # Task claim, price, result persist
│   └── tests/                  # Golden tests with expected values
│       ├── golden/
│       │   ├── inputs/         # Test position/market data
│       │   └── expected/       # Reference outputs
│       └── test_*.py           # Golden test cases
│
├── services/                   # FastAPI microservices
│   ├── common/                 # Shared utilities
│   │   ├── db.py               # DB connection factory (context manager)
│   │   ├── hash.py             # SHA256 JSON hashing
│   │   ├── health.py           # Health check utilities
│   │   ├── errors.py           # Exception types
│   │   ├── pagination.py       # Pagination helpers
│   │   └── service_base.py     # Base service class
│   ├── marketdata_svc/         # Market data management (port 8001)
│   │   └── app/
│   │       └── main.py         # POST/GET market data snapshots
│   ├── run_orchestrator/       # Run creation and task fanout (port 8002)
│   │   └── app/
│   │       └── main.py         # POST runs, GET position snapshots
│   ├── results_api/            # Result queries and aggregation (port 8003)
│   │   └── app/
│   │       └── main.py         # GET results summary, drill-down cube
│   ├── data_ingestion_svc/     # Data ingestion (future)
│   │   └── app/
│   │       └── routes/
│   ├── portfolio_svc/          # Portfolio management (future)
│   │   └── app/
│   │       └── routes/
│   ├── instrument_svc/         # Instrument registry (future)
│   │   └── app/
│   │       └── routes/
│   ├── regulatory_svc/         # Regulatory reporting (future)
│   │   └── app/
│   │       └── routes/
│   ├── risk_svc/               # Risk analytics (future)
│   │   └── app/
│   │       └── routes/
│   └── README_SERVICES.md
│
├── frontend/                   # React UI
│   ├── public/
│   ├── src/
│   │   ├── main.tsx            # React root with QueryClient
│   │   ├── App.tsx             # Top-level router and nav
│   │   ├── api.ts              # API client for all services
│   │   ├── runHistory.ts       # Run history persistence
│   │   ├── pages/
│   │   │   ├── RunLauncherPage.tsx    # Run creation form
│   │   │   ├── RunResultsPage.tsx     # Results and drill-down
│   │   │   └── RunCubePage.tsx        # OLAP-style analysis
│   │   └── styles.css          # Tailwind + custom styles
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
│
├── contracts/                  # JSON schemas and test fixtures
│   ├── domains/                # Data contracts (strict schemas)
│   ├── envelope/               # Envelope schemas
│   ├── fixtures/               # Test data payloads
│   └── README.md
│
├── sql/                        # PostgreSQL DDL
│   └── 001_mvp_core.sql        # Full MVP schema: run, task, results, market data, positions
│
├── db/                         # Database utilities
│   └── migrations/             # Future: Migration runner
│
├── demo/                       # Demo data
│   ├── inputs/
│   │   └── positions.json      # Default positions snapshot
│   ├── fixtures/               # Additional demo datasets
│   └── logs/                   # Demo run logs
│
├── scripts/                    # Utility scripts
│
├── shared/                     # Shared Python modules (future)
│
├── .claude/                    # Claude documentation
│   ├── agents/                 # Agent state (git-ignored)
│   ├── docs/
│   │   └── architectural_patterns.md
│   └── settings.local.json     # Local Claude settings
│
├── .planning/                  # GSD planning documents
│   └── codebase/               # Codebase analysis (ARCHITECTURE.md, STRUCTURE.md, etc.)
│
├── CLAUDE.md                   # Project overview and quickstart
├── setup.py                    # Python package definition
├── requirements.txt            # Python dependencies
├── .gitignore
└── README.md
```

## Directory Purposes

**compute/ - Pricing and Worker:**
- Purpose: Core financial computation engine
- Contains: Instrument pricers, quantitative libraries, distributed worker
- Key files: `compute/worker/worker.py` (task processor), `compute/pricers/` (valuations), `compute/quantlib/` (math)

**compute/pricers/ - Pricer Implementations:**
- Purpose: Product-specific instrument pricing algorithms
- Contains: Free-function pricers for each product type, each with signature: (position, instrument, market_snapshot, measures, scenario_id) -> Dict[str, float]
- Key files: `bond.py` (fixed bonds), `fx_fwd.py` (FX forwards), `loan.py` (amortizing loans)
- Extensibility: Add new pricer, register in dispatch (worker.py:184-190)

**compute/quantlib/ - Financial Math Library:**
- Purpose: Reusable quantitative components for all pricers
- Contains: Zero curve interpolation, discount factor calculation, scenario application, FX utilities
- Key files: `curve.py` (ZeroCurve class), `scenarios.py` (shock application), `fx.py` (FX conversions)

**compute/worker/ - Distributed Task Processor:**
- Purpose: Claims tasks from queue, prices positions, persists results
- Key files: `worker.py` (main loop from line 192)
- Lifecycle: claim_task() → load_snapshots() → price_position() → mark_succeeded/failed()

**services/common/ - Shared Service Utilities:**
- Purpose: DB connection factory, hashing, error types used by all services
- Key files: `db.py` (context manager for connections), `hash.py` (SHA256 JSON)

**services/marketdata_svc/ - Market Data API (Port 8001):**
- Purpose: Snapshot creation and retrieval for curves, FX spots, quality checks
- Key files: `services/marketdata_svc/app/main.py`
- Endpoints: POST /api/v1/marketdata/snapshots (create), GET /api/v1/marketdata/snapshots/{snapshotId} (retrieve)

**services/run_orchestrator/ - Run Orchestration (Port 8002):**
- Purpose: Run lifecycle and task fanout
- Key files: `services/run_orchestrator/app/main.py`
- Endpoints: POST /api/v1/runs (create run + fanout), GET /api/v1/position-snapshots/{id} (retrieve)
- Fanout logic: Extract product_types from positions, create tasks for (product_type, hash_bucket) pairs

**services/results_api/ - Results Query API (Port 8003):**
- Purpose: Results aggregation and drill-down analysis
- Key files: `services/results_api/app/main.py`
- Endpoints: GET /api/v1/results/{runId}/summary (sum PV by scenario), GET /api/v1/results/{runId}/cube (group by product_type or portfolio_node_id)

**frontend/ - React UI:**
- Purpose: User interface for run submission and results visualization
- Key files: `frontend/src/App.tsx` (routing), `frontend/src/api.ts` (HTTP client)
- Pages: RunLauncherPage (submit run), RunResultsPage (view results), RunCubePage (drill-down)

**contracts/ - Data Contracts:**
- Purpose: JSON schemas defining API payloads, position/market data structure
- Contains: Domain schemas (run, position, instrument), envelope schemas, test fixtures

**sql/ - Database Schema:**
- Purpose: PostgreSQL DDL for all tables and indices
- Key files: `sql/001_mvp_core.sql` (complete MVP schema)
- Tables: run, run_task, position_snapshot, marketdata_snapshot, valuation_result, instrument, instrument_version

**demo/ - Demo Datasets:**
- Purpose: Sample positions and market data for testing
- Key files: `demo/inputs/positions.json` (default positions, loaded by worker if not specified)

## Key File Locations

**Entry Points:**
- Backend orchestrator: `services/run_orchestrator/app/main.py` (app FastAPI instance)
- Backend results: `services/results_api/app/main.py` (app FastAPI instance)
- Backend market data: `services/marketdata_svc/app/main.py` (app FastAPI instance)
- Worker: `compute/worker/worker.py` (worker_main() at line 192)
- Frontend: `frontend/src/main.tsx` (React root at line 17)

**Configuration:**
- Database: Set via DATABASE_URL env var, defaults to `postgresql://postgres:postgres@localhost:5432/iprs`
- Worker: WORKER_ID, WORKER_LEASE_SECONDS, WORKER_IDLE_SLEEP_SECONDS, RUN_TASK_HASH_MOD, POSITIONS_SNAPSHOT_PATH
- Frontend: API proxy configured in vite.config.ts (development), direct URLs in production

**Core Logic:**
- Pricer dispatch: `compute/worker/worker.py:184-190` (price_position function with product_type routing)
- Task claiming: `compute/worker/worker.py:119-134` (CLAIM_SQL with leasing logic)
- Scenario application: `compute/quantlib/scenarios.py` (apply_scenario function)
- Results aggregation: `services/results_api/app/main.py:27-39` (cube endpoint with GROUP BY)

**Testing:**
- Golden tests: `compute/tests/golden/` (expected outputs for known inputs)
- Test runner: pytest with fixtures in `compute/tests/golden/{inputs,expected}`

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `worker.py`, `curve_builder.py`)
- React components: `PascalCase.tsx` (e.g., `RunLauncherPage.tsx`, `App.tsx`)
- Test files: `test_*.py` or `*_test.py` (pytest discovery pattern)
- Database migrations: `NNN_description.sql` (e.g., `001_mvp_core.sql`)

**Directories:**
- Service directories: `snake_case` (e.g., `marketdata_svc`, `run_orchestrator`)
- Feature directories: `snake_case` (e.g., `compute/pricers`, `compute/quantlib`)
- URL paths: `/api/v1/{resource}/{action}` following REST conventions

**Classes:**
- Python classes: `PascalCase` (e.g., `ZeroCurve`, `Task`, `AbstractPricer`)
- Dataclasses: `PascalCase` (e.g., `Task` at worker.py:28)
- Pydantic models: `PascalCase` ending with "In" (request) or "Out" (response) (e.g., `RunRequestedV1`, `PositionSnapshotOut`)

**Functions:**
- Python functions: `snake_case` (e.g., `apply_scenario()`, `price_bond()`, `claim_task()`)
- React hooks: `use_*` convention (custom hooks in pages)
- API functions: `verb_noun` pattern (e.g., `create_snapshot()`, `get_snapshot()`)

**Database:**
- Tables: `snake_case` (e.g., `run_task`, `position_snapshot`, `marketdata_snapshot`, `valuation_result`)
- Columns: `snake_case` (e.g., `position_snapshot_id`, `as_of_time`, `portfolio_node_id`)
- Indices: `{table_name}_{column_name}_idx` (e.g., `run_task_run_idx`)

**IDs and Identifiers:**
- Run ID: `RUN-{timestamp}-{random}` format or caller-supplied (e.g., `RUN-2026-01-23-ABC`)
- Task ID: `TASK-{run_id}-{product_type}-{bucket}` (deterministic from run + product type)
- Position snapshot ID: `POS-{run_id}` or `PS-{portfolio_node_id}-{date}-{random}` (for deduplication)
- Market snapshot ID: Vendor-specific (e.g., `snap-2026-01-23-EOD`)
- Scenario ID: `BASE`, `RATES_PARALLEL_1BP`, `SPREAD_25BP`, `FX_SPOT_1PCT` (predefined set)

## Where to Add New Code

**New Pricer (e.g., floating rate notes):**
- Implementation: `compute/pricers/floating_rate.py` (create new file)
- Register dispatch: Update `compute/worker/worker.py:184-190` to add `if product_type == "FLOATING_RATE": return price_floating_rate(...)`
- Test: Add golden test case in `compute/tests/golden/` with inputs and expected outputs
- Update contracts: Add example position and instrument schema to `contracts/domains/`

**New Service (e.g., regulatory reporting):**
- Create: `services/regulatory_svc/app/main.py` (create directory and main.py)
- Follow pattern: Import `db_conn` from `services/common.db`, define Pydantic models, create FastAPI app
- Entry point: Expose FastAPI `app` instance
- Update CLAUDE.md: Add port and responsibilities to services table

**New Scenario (e.g., credit spread shock):**
- Add logic: `compute/quantlib/scenarios.py:31` (before raise ValueError)
- Example: Add elif block for `"CREDIT_SPREAD_1PCT"` to bump credit spread curves
- Test: Add scenario ID to RunRequestedV1 scenarios list in test data

**New API Endpoint (e.g., historical results):**
- Location: Add route to relevant service main.py (e.g., `services/results_api/app/main.py`)
- Pattern: Use `@app.get()` or `@app.post()`, query database with parameterized SQL, return Pydantic model or list
- Database: Add query SQL if needed, test with demo data

**New Utility (e.g., caching):**
- Location: `services/common/{feature_name}.py` (e.g., `services/common/cache.py`)
- Pattern: Create function or class, import in services that need it
- Document: Add comment in CLAUDE.md Quick Reference section

**Frontend Page (e.g., instrument management):**
- Component: `frontend/src/pages/InstrumentPage.tsx` (create new file)
- Routing: Add route in `frontend/src/App.tsx:130-135`
- API calls: Define in `frontend/src/api.ts` if calling new endpoint
- Styling: Follow Tailwind classes and border-3/shadow-brutal conventions from existing pages

## Special Directories

**.claude/ - Claude Documentation:**
- Purpose: Agent-managed documentation and settings
- Generated: Partially (agents/ directory with agent state)
- Committed: architectural_patterns.md and CLAUDE.md; agents/ is git-ignored

**.planning/codebase/ - GSD Codebase Analysis:**
- Purpose: Structured codebase documentation for `/gsd:` commands
- Generated: Via `/gsd:map-codebase` agent
- Committed: Yes (ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md)

**db/migrations/ - Database Migrations:**
- Purpose: Future versioned schema changes
- Generated: Manual (not yet implemented)
- Committed: Yes

**demo/ - Demo Data:**
- Purpose: Sample positions and market data for development and testing
- Generated: Manual
- Committed: Yes

**contracts/domains/ - Data Contracts:**
- Purpose: JSON Schema definitions for API payloads
- Generated: Manual (future: code generation from TypeScript types)
- Committed: Yes

**iprs_mvp.egg-info/ - Package Metadata:**
- Purpose: pip-generated package information
- Generated: Yes (by `pip install -e .`)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-02-11*
