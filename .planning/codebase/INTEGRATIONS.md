# External Integrations

**Analysis Date:** 2026-02-11

## APIs & External Services

**None Detected**

The MVP contains no external third-party APIs (Stripe, Supabase, AWS SDK, etc.). All data and operations are self-contained within the distributed system.

## Data Storage

**Databases:**
- PostgreSQL 12+ (inferred from JSONB column support)
  - Connection: Via `DATABASE_URL` environment variable (default: `postgresql://postgres:postgres@localhost:5432/iprs`)
  - Client: psycopg 3.1.18+ (binary-enabled)
  - Pattern: Synchronous connection pooling using contextmanager in `services/common/db.py`
  - Row factory: `psycopg.rows.dict_row` for dict-based row access
  - JSONB support: Used for flexible payload storage via `psycopg.types.json.Json` wrapper

**Schema:**
- Initialized from `sql/001_mvp_core.sql`
- Core tables:
  - `instrument`, `instrument_version` - Instrument definitions and versioning
  - `marketdata_snapshot` - Market data time series (curves, FX spots with quality flags)
  - `position_snapshot` - Portfolio snapshots with position payloads
  - `run` - Batch valuation run metadata
  - `run_task` - Task queue entries (product_type × hash_bucket distribution)
  - `valuation_result` - Result storage (run_id, position_id, measures_json, scenario_id)

**File Storage:**
- Local filesystem only
- Demo data: `demo/inputs/positions.json` (loaded via `POSITIONS_SNAPSHOT_PATH`)
- No cloud storage integration (S3, GCS, etc.)

**Caching:**
- Frontend: TanStack React Query (5.59.16) with built-in memory cache
  - Default retry: 1 attempt
  - Window focus refetch disabled
- Backend: None detected (in-process execution, no Redis/Memcached)

## Authentication & Identity

**Auth Provider:**
- Custom/None - No auth system in MVP

**Implementation:**
- No JWT, OAuth, or OIDC
- No API key validation in service endpoints
- Health checks use simple `/health` endpoints returning `{"ok": true}`
- SQL layer directly accessed via psycopg with connection string in env var

## Monitoring & Observability

**Error Tracking:**
- None detected - No Sentry, DataDog, or similar integration

**Logs:**
- Console/stdout only
- No structured logging framework configured
- Stack traces propagated to FastAPI error responses

**Health Checks:**
- Built-in `/health` endpoints on all three services:
  - `services/marketdata_svc/app/main.py:40`
  - `services/run_orchestrator/app/main.py:98, 222`
  - `services/results_api/app/main.py:9`
- Frontend health verification: `frontend/src/api.ts` has `healthMarket()`, `healthOrch()`, `healthResults()` functions
- Used by RunLauncherPage to display service connectivity status

## CI/CD & Deployment

**Hosting:**
- Not configured in MVP - Assumed local development or manual deployment

**CI Pipeline:**
- None detected - No GitHub Actions, GitLab CI, Jenkins, etc.

**Local Execution:**
- PowerShell demo runner: `scripts/demo_runner.ps1` (mentioned in `frontend/README.md`)
- Manual service startup via `uvicorn` CLI

## Environment Configuration

**Required Environment Variables:**

For Backend Services:
- `DATABASE_URL` - PostgreSQL connection (no default assumed for production)
- `WORKER_ID` - Worker identifier for distributed task claiming
- `POSITIONS_SNAPSHOT_PATH` - Path to demo positions file

For Frontend:
- None required (uses Vite proxy configuration)

**Secrets Location:**
- Environment variables only (no separate secrets management)
- `.env` file not included in repo (inferred from .gitignore practices)
- Sensitive data: DATABASE_URL with credentials must be set per deployment

## Webhooks & Callbacks

**Incoming:**
- None detected - Services only respond to HTTP GET/POST requests

**Outgoing:**
- None detected - No external webhook calls from services

## Service-to-Service Communication

**Pattern:**
- HTTP REST via Vite proxy (frontend)
- JSON request/response bodies
- No gRPC, message queues, or event buses

**Frontend → Backend:**
- Axios client (`frontend/src/api.ts`) to backend services
- Endpoints:
  - Market Data: POST `/api/v1/marketdata/snapshots`, GET `/api/v1/marketdata/snapshots/{id}`
  - Run Orchestrator: POST `/api/v1/runs`, GET `/api/v1/position-snapshots/{id}`
  - Results API: GET `/api/v1/results/{runId}/summary`, GET `/api/v1/results/{runId}/cube`

**Backend → Database:**
- Direct psycopg connections (no ORM like SQLAlchemy)
- SQL with parameterized queries

**Worker → Database:**
- Distributed task claiming via `compute/worker/worker.py`
- SQL-based task queue in `run_task` table
- RUNNING state with lease_until timestamp for distributed coordination

## Task Distribution

**Pattern:**
- Database-backed task queue (pessimistic locking via `FOR UPDATE SKIP LOCKED`)
- Tasks created per product_type × hash_bucket
- Hash mod controlled by `RUN_TASK_HASH_MOD` env var (default: 1 bucket)
- Workers lease tasks for `WORKER_LEASE_SECONDS` and update attempt count
- Retry logic: Marks DEAD after `RUN_TASK_MAX_ATTEMPTS` (default: 3)
- No external job queue system (Celery, RQ, etc.)

---

*Integration audit: 2026-02-11*
