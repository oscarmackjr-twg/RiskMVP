# Phase 1: Foundation & Infrastructure - Research

**Researched:** 2026-02-11
**Domain:** FastAPI microservices, shared libraries, Docker containerization, Terraform IaC, CI/CD pipelines, pricer registry pattern
**Confidence:** HIGH

## Summary

Phase 1 establishes the platform foundation needed for institutional-scale risk analytics. Research confirms that all six requirements (PLAT-01 through PLAT-06) align with proven FastAPI microservices patterns, and the codebase already has most components partially implemented. Key findings: (1) Shared Pydantic models, events, and config infrastructure already exists in `/shared` directory and is importable by services; (2) Service factory pattern (`ServiceBase`) is in place with health checks and error handlers; (3) Pricer registry pattern is already implemented with decorator-based auto-bootstrapping; (4) Docker and Terraform infrastructure does not yet exist and must be built from standard AWS/Terraform modules.

**Primary recommendation:** Prioritize completing the service integration layer (PLAT-01 to PLAT-02) before building Docker and Terraform (PLAT-03 to PLAT-04). Services must consistently import and use shared libraries first. Registry pattern is ready to use immediately in worker refactoring (PLAT-06).

## Current State Assessment

**Implemented (ready to use):**
- Shared library structure: `shared/models/`, `shared/events/`, `shared/config/`, `shared/auth/` with Pydantic BaseModel exports
- Service factory: `services/common/service_base.py` with `create_service_app()` helper
- Health check endpoints: `/health` and `/health/deep` (DB connectivity check) patterns established
- Error handling: `ErrorResponse`, `NotFoundError`, `ConflictError` exception handlers defined
- Pricer registry: `compute/pricers/registry.py` with `register()`, `get_pricer()`, `registered_types()` already functional
- Pagination: `services/common/pagination.py` with `PaginationParams`, `PaginatedResponse`, `paginate()` helpers
- Database connection: `services/common/db.py` with psycopg3 context manager pattern
- Test database: Schema in `sql/001_mvp_core.sql` with proper indexes and JSONB support

**Partially implemented (needs refactoring):**
- Service initialization: Each service (marketdata_svc, run_orchestrator) creates FastAPI directly instead of using `create_service_app()`
- Shared models usage: Services define local models (e.g., `PositionSnapshotIn`, `PositionSnapshotOut`) instead of importing from `shared.models`
- Worker pricer dispatch: Still has if/elif chain in `compute/worker/worker.py:184-190` instead of using registry

**Not implemented (must build):**
- Dockerfiles: No container definitions for any service or worker
- Docker Compose: No local orchestration for all 4 services + worker
- Terraform: No AWS infrastructure as code (VPC, ECS, RDS, API Gateway, ECR)
- GitHub Actions: No CI/CD pipeline for lint, test, build, deploy
- Environment configuration: Services read `DATABASE_URL` but don't use shared config loader
- Auth middleware: `shared/auth/middleware.py` exists but not applied to any service endpoints

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | ^0.100 | REST API framework | Type-safe, async-native, auto docs (OpenAPI), industry standard for Python microservices |
| psycopg | ^3.1.18 | PostgreSQL adapter | Official, supports both sync and async, connection pooling, binary protocol for performance |
| Pydantic | ^2.0 | Data validation, serialization | 5-50x faster than v1 (Rust-backed), schema validation, JSON serialization, FastAPI native integration |
| Pytest | ^7.4.0 | Testing framework | Industry standard for Python, excellent fixture model, async support via pytest-asyncio |
| Python | 3.11+ | Runtime | Type hints maturity, async/await stability, match statements, security patches |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Starlette | (via FastAPI) | ASGI framework | Middleware, routing, WebSocket support (FastAPI depends on this) |
| Pydantic Settings | ^2.0 | Config management | Environment variable loading, type-safe settings, validation on init |
| uvicorn | ^0.23 | ASGI server | High-performance async server for running FastAPI apps |
| gunicorn | ^20.1 | Process manager | Multi-worker orchestration, graceful shutdown (use with uvicorn for production) |
| psycopg_pool | ^3.1 | Connection pooling | For async apps, `AsyncConnectionPool` manages persistent connections efficiently |
| python-dotenv | ^1.0 | Environment files | Local development (`.env` files) without env vars |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FastAPI | Django REST Framework | DRF is more mature but heavier, slower startup, more batteries-included (less modular) |
| psycopg3 | SQLAlchemy ORM | SQLAlchemy adds abstraction layer but introduces N+1 query problems; use psycopg3 directly with raw SQL for financial data (predictable, auditable) |
| Pydantic | Marshmallow | Marshmallow is lighter but Pydantic v2 is now faster and has better IDE support |
| PostgreSQL | Cloud data warehouse (Snowflake, BigQuery) | For MVP scope and cost, PostgreSQL is sufficient; can evolve to warehouse later |

**Installation (Backend Base):**
```bash
pip install fastapi uvicorn psycopg[binary] pydantic pydantic-settings pytest pytest-asyncio python-dotenv
```

**Installation (Worker):**
```bash
pip install -e .  # Installs the compute package from setup.py/pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure

```
.planning/phases/           # Planning docs (this phase's output)
compute/
  pricers/
    registry.py             # Registry pattern (READY TO USE)
    base.py                 # Abstract base class
    fx_fwd.py, loan.py, bond.py   # Existing pricers
  worker/
    worker.py               # Distributed task processor (needs registry refactor)
  quantlib/                 # Curve interpolation, scenario application
  tests/                    # Golden tests with expected values

services/
  common/
    service_base.py         # Factory: create_service_app() (READY TO USE)
    db.py                   # db_conn() context manager (READY TO USE)
    health.py               # add_health_endpoint() (READY TO USE)
    errors.py               # Standard error handlers (READY TO USE)
    pagination.py           # Pagination helpers (READY TO USE)
  marketdata_svc/
    app/
      main.py               # REFACTOR: use create_service_app()
  run_orchestrator/
    app/
      main.py               # REFACTOR: use create_service_app()
  results_api/
    app/
      main.py               # REFACTOR: use create_service_app()

shared/
  models/
    common.py               # Enums: Currency, DayCount, Tenor, Rating, Audit, Pagination
    instrument.py           # Instrument models
    position.py             # Position models
    market_data.py          # Market data models
    # ... other domain models
  events/
    base.py                 # BaseEvent (READY TO USE)
    run_events.py           # Run-related events
  config/
    settings.py             # BaseAppSettings (READY TO USE)
    aws.py                  # AWS-specific config
  auth/
    middleware.py           # Auth middleware (NOT YET APPLIED)
    permissions.py          # Permission checks
  observability/
    logging.py              # Structured logging
    metrics.py              # Prometheus metrics
    tracing.py              # Distributed tracing

sql/
  001_mvp_core.sql          # Schema (READY TO USE)
  # Migration pattern: 002_add_column.sql, etc.

frontend/                   # React 18 + TypeScript + Vite + TanStack Query

docker/                     # Dockerfiles (TO BUILD)
  Dockerfile.marketdata
  Dockerfile.orchestrator
  Dockerfile.results
  Dockerfile.worker
  docker-compose.yml        # Local dev orchestration (TO BUILD)

terraform/                  # IaC (TO BUILD)
  main.tf
  vpc.tf
  rds.tf
  ecs.tf
  ecr.tf
  api_gateway.tf
  variables.tf
  outputs.tf

.github/workflows/          # CI/CD (TO BUILD)
  ci.yml                    # lint, test, build, push to ECR
  deploy.yml                # Deploy to ECS Fargate
```

### Pattern 1: Service Factory

**What:** All services use the same initialization pattern via `create_service_app()` helper to ensure consistent middleware, health endpoints, and error handling.

**When to use:** Every new service (`main.py`).

**Example:**
```python
# Old (each service duplicates):
app = FastAPI(title="my-service", version="0.1.0")

# New (all services use factory):
from services.common.service_base import create_service_app
app = create_service_app(title="my-service", version="0.1.0")
```

**What the factory provides (source: `services/common/service_base.py`):**
- CORS middleware (allow all origins for dev, restrict in prod)
- Health endpoint at `GET /health` (returns `{"ok": True}`)
- Deep health at `GET /health/deep` (includes DB connectivity check)
- Standard error handlers for `NotFoundError`, `ConflictError` exceptions

### Pattern 2: Database Connection Context Manager

**What:** All DB access uses `with db_conn() as conn:` pattern for automatic transaction management (commit on success, rollback on exception).

**When to use:** Every database operation.

**Example:**
```python
from services.common.db import db_conn

with db_conn() as conn:
    conn.execute("INSERT INTO run (run_id, ...) VALUES (...)")
    # Commit happens automatically on exit
```

**Why:** Simplifies transaction logic, prevents connection leaks, ensures proper error handling.

### Pattern 3: Pricer Registry with Decorators

**What:** Instead of if/elif dispatch in the worker, pricers self-register on import via `register()` calls.

**When to use:** Whenever adding a new product type (BOND, ABS, derivatives, etc.).

**Example (current pattern in `compute/pricers/registry.py`):**
```python
from compute.pricers.registry import register, get_pricer

# In each pricer module:
def price_fx_fwd(...) -> Dict[str, float]:
    ...

# Auto-register on module import:
register("FX_FWD", price_fx_fwd)

# In worker:
pricer_fn = get_pricer(task.product_type)
measures = pricer_fn(position, instrument, market_snapshot, measures, scenario_id)
```

**Source:** `compute/pricers/registry.py` with three pricers (FX_FWD, AMORT_LOAN, FIXED_BOND) already registered.

### Pattern 4: Shared Pydantic Models

**What:** Common models (Currency, DayCount, Rating, Tenor, pagination) live in `shared/models/` and are imported by all services.

**When to use:** Any model needed by multiple services or that is part of the domain contract.

**Example:**
```python
# shared/models/common.py (source: verified via Read)
class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"

class PageRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)

# In services, import directly:
from shared.models.common import Currency, PageRequest
```

**Source:** `shared/models/common.py` already defines enums and pagination models.

### Pattern 5: Health Check Endpoints

**What:** Every service exposes `GET /health` (basic) and `GET /health/deep` (with DB check).

**When to use:** As part of service factory, tested by load balancers and Kubernetes.

**Example:**
```python
# Automatic from create_service_app():
GET /health          -> {"ok": True}
GET /health/deep     -> {"ok": True, "db": "connected"}  or  {"ok": False, "db": "error message"}
```

**Source:** `services/common/health.py` (verified via Read).

### Anti-Patterns to Avoid

- **Defining models in service main.py instead of shared/models:** Creates duplicate definitions, versioning chaos, hard to refactor. Solution: Always put Pydantic models in `shared/models/` if used by multiple services.

- **Hardcoding database credentials in code:** Services currently read `DATABASE_URL` env var (good), but should use `BaseAppSettings` from `shared/config/settings.py` for consistency. Solution: Use `from shared.config.settings import BaseAppSettings` in each service main.py.

- **Forgetting to apply auth middleware:** `shared/auth/middleware.py` exists but is not referenced in any service. Solution: Add `app.add_middleware(AuthMiddleware)` in `create_service_app()` factory once auth is implemented.

- **Catching generic Exception in routes:** Current code uses `except Exception as e:` which hides bugs. Solution: Use custom exceptions (`NotFoundError`, `ConflictError`) and let factory's error handlers convert to HTTP responses.

- **If/elif dispatch in worker for pricers:** Current code has dispatch chain; requires code modification to add product types. Solution: Use registry pattern (already implemented, just needs to replace if/elif calls).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Database transactions | Custom try/catch/commit logic | `db_conn()` context manager | Handles autocommit=False, proper rollback, connection cleanup automatically |
| Health checks | Manual `/health` endpoint in each service | `add_health_endpoint(app)` from shared | Consistency across all services, DB connectivity check included |
| Error responses | Custom exception classes with HTTP mapping | `NotFoundError`, `ConflictError` + handlers in factory | Standardized HTTP status codes (404, 409, 500), consistent JSON error shape |
| Pagination | Manual OFFSET/LIMIT SQL + response building | `PaginationParams`, `PaginatedResponse`, `paginate()` helpers | Prevents off-by-one bugs, standard shape for all paginated endpoints |
| Product type dispatch | If/elif chains in worker | Pricer registry with `register()`, `get_pricer()` | Allows new pricers without modifying worker.py, easier testing, plugin architecture |
| Environment config | Reading individual env vars | `BaseAppSettings` from `shared/config/settings.py` | Type validation on init, centralized defaults, easier to add new settings |
| Shared models | Defining Pydantic models locally in each service | Models in `shared/models/` imported by all services | Single source of truth, easier refactoring, contract clarity between services |
| API documentation | Manual docstrings | FastAPI + Pydantic auto-generates OpenAPI | Built-in at `GET /docs` and `GET/redoc`, always in sync with code |

**Key insight:** All of these patterns are already partially implemented in the codebase. Phase 1 is about standardizing their use across all services (refactoring), not building new infrastructure.

## Common Pitfalls

### Pitfall 1: Services Duplicating Shared Models

**What goes wrong:** Each service defines its own `PositionSnapshotIn`, `RunRequest` models instead of importing from `shared.models`. When schema changes (e.g., add a field), developer must update 3+ places. Version mismatch causes subtle bugs.

**Why it happens:** Developers copy-paste models locally for speed, don't know about shared library, or shared models don't exist yet.

**How to avoid:**
1. Define all domain models in `shared/models/` with clear docstrings
2. Document in CLAUDE.md and services/README_SERVICES.md which models are shared
3. Use linting rule or code review checklist: "Does this Pydantic model exist in shared/models already?"

**Warning signs:**
- Same model class name defined in multiple files
- `grep -r "class PositionSnapshot" returns multiple results
- Service imports differ from shared module pattern

**Verification step (in PLAN.md tasks):**
```bash
pytest compute/tests/  # Golden tests should pass
grep -r "class.*In\|class.*Out" services/ | grep -v shared | grep -v ".pyc"  # Should be few/none
```

### Pitfall 2: Forgetting to Migrate Services to Factory Pattern

**What goes wrong:** New service or refactored service bypasses `create_service_app()` and creates `FastAPI()` directly. Missing health check, error handlers, or CORS leads to "404 on /health" from load balancer, or requests from frontend blocked by CORS.

**Why it happens:** Developer unaware of factory, or factory was added after service existed.

**How to avoid:**
1. Update CLAUDE.md with entry point template:
   ```python
   from services.common.service_base import create_service_app
   app = create_service_app(title="my-service", version="0.1.0")
   ```
2. Code review checklist: "Does main.py import from services.common.service_base?"
3. Test: `curl http://localhost:8002/health` for each service during integration tests

**Warning signs:**
- Service starts but `/health` returns 404
- Frontend can't reach service (CORS issue)
- Developer adds error handler to individual service instead of using factory

**Verification step (in PLAN.md tasks):**
```bash
# All services should return 200 OK
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

### Pitfall 3: Registry Pattern Initialization Order Dependency

**What goes wrong:** Worker imports pricer modules but not in the right order, or worker imports registry before pricers are registered. `get_pricer("FX_FWD")` raises `ValueError: No pricer registered for product_type: FX_FWD`.

**Why it happens:** Python import system is implicit; if `from compute.pricers.fx_fwd import price_fx_fwd` is never called, `_bootstrap()` in registry.py doesn't run.

**How to avoid:**
1. Ensure registry bootstrap (auto-register pricers) is called in `registry.py:_bootstrap()` on module load
2. In worker.py, import registry AFTER importing pricers:
   ```python
   from compute.pricers import registry  # Triggers _bootstrap() which imports all pricers
   pricer_fn = registry.get_pricer(task.product_type)
   ```
3. Add test for every pricer: `test_pricer_registered_for_product_type()` in pytest

**Warning signs:**
- Worker fails at runtime: "No pricer registered for FX_FWD"
- Test passes locally but fails in CI (import order differs)
- Add new pricer but worker still doesn't see it

**Verification step (in PLAN.md tasks):**
```python
# In pytest fixture:
from compute.pricers.registry import registered_types
assert "FX_FWD" in registered_types()
assert "AMORT_LOAN" in registered_types()
assert "FIXED_BOND" in registered_types()
```

### Pitfall 4: Circular Imports Between Shared Models

**What goes wrong:** `shared/models/position.py` imports `Portfolio` from `shared/models/portfolio.py`, which imports `Position` from `shared/models/position.py`. Causes `ImportError: cannot import name 'Position'`.

**Why it happens:** Models have relationships (Position has-a Portfolio), and developer tries to make them bidirectional without using forward references.

**How to avoid:**
1. Use Pydantic forward references (strings) for types not yet defined:
   ```python
   # shared/models/position.py
   from typing import Optional

   class Position(BaseModel):
       position_id: str
       portfolio: Optional['Portfolio'] = None  # String reference
   ```
2. Call `Position.model_rebuild()` after all models are defined, or use `from __future__ import annotations` at the top of the file
3. Keep shared models in flat hierarchy (no parent->child in shared imports)

**Warning signs:**
- Import fails: `ImportError: cannot import name`
- `from shared.models import Position` works but `from shared.models.position import Position` doesn't
- Developer adds lazy import inside function to work around circular dependency

**Verification step (in PLAN.md tasks):**
```bash
python -c "from shared.models import *; print('imports OK')"
```

### Pitfall 5: Inconsistent Error Response Format Across Services

**What goes wrong:** Marketdata service returns `{"error": "...", "status_code": 400}`, run_orchestrator returns `{"detail": "...", "status_code": 400}`, and results_api returns `{"message": "...", "status_code": 400}`. Frontend can't parse errors consistently.

**Why it happens:** Each service defined error handling independently before factory pattern was in place.

**How to avoid:**
1. Enforce `create_service_app()` factory usage (includes `add_error_handlers()`)
2. Define all custom exceptions in `services/common/errors.py` with handlers
3. Test error responses in pytest:
   ```python
   response = client.get("/nonexistent")
   assert response.status_code == 404
   assert "error" in response.json()
   assert "status_code" in response.json()
   ```

**Warning signs:**
- Frontend logs different error key names (error vs detail vs message)
- Service returns `{"detail": "..."}` instead of `{"error": "...", "detail": "..."}`
- Developer manually converts HTTPException to JSONResponse in route handler

**Verification step (in PLAN.md tasks):**
```bash
# All services should have same error shape:
curl http://localhost:8002/api/v1/nonexistent 2>/dev/null | jq .
# Expected: {"error": "not_found", "detail": "...", "status_code": 404}
```

### Pitfall 6: Psycopg3 Connection Exhaustion in Async Context

**What goes wrong:** Worker or API service with heavy async load exhausts PostgreSQL connections. New requests hang waiting for a connection to become available. After ~30 seconds, "could not connect to server" errors.

**Why it happens:** `db_conn()` context manager opens new connection per request. With many concurrent requests, connections pile up. No connection pooling for async case.

**How to avoid:**
1. For FastAPI (async) services, use `AsyncConnectionPool` from psycopg_pool:
   ```python
   from psycopg_pool import AsyncConnectionPool

   pool = AsyncConnectionPool("postgresql://...")

   # On service startup:
   @app.on_event("startup")
   async def startup():
       await pool.open()

   @app.on_event("shutdown")
   async def shutdown():
       await pool.close()

   # In routes:
   async def my_route():
       async with pool.connection() as conn:
           result = await conn.execute("SELECT ...")
   ```
2. For worker (sync), current `db_conn()` pattern is fine (single worker, low concurrency)
3. Set pool size based on expected concurrency: `AsyncConnectionPool(..., min_size=5, max_size=20)`

**Warning signs:**
- Logs show "could not connect" errors after high load
- Response times increase dramatically at peak concurrency
- Database connection count grows during traffic spike

**Verification step (in PLAN.md tasks):**
```bash
# Check current connections:
psql -c "SELECT count(*) FROM pg_stat_activity WHERE usename = 'postgres';"
```

## Code Examples

Verified patterns from official sources and working code:

### Setting Up a Service with Factory Pattern

```python
# services/my_svc/app/main.py (source: services/common/service_base.py confirmed pattern)
from fastapi import FastAPI
from services.common.service_base import create_service_app
from shared.models.common import Currency, PageRequest

# Create app with standard middleware, health, errors
app = create_service_app(
    title="my-service",
    version="0.1.0",
    description="Service description"
)

# Define routes using shared models
@app.post("/api/v1/positions")
def create_position(req: PageRequest):
    return {"offset": req.offset, "limit": req.limit}

# Health checks automatic from factory:
# GET /health -> {"ok": True}
# GET /health/deep -> {"ok": True, "db": "connected"}
```

### Database Operations with Transaction Management

```python
# In any service route (source: services/common/db.py confirmed pattern)
from services.common.db import db_conn
from psycopg.types.json import Json

@app.post("/api/v1/runs")
def create_run(req: RunRequest):
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO run (run_id, status, market_snapshot_id, measures)
            VALUES (%(rid)s, 'QUEUED', %(msid)s, %(measures)s)
            ON CONFLICT (run_id) DO NOTHING
            """,
            {
                "rid": req.run_id,
                "msid": req.market_snapshot_id,
                "measures": req.measures,  # text[] column
            }
        )
        # Commit happens automatically on exit; rollback on exception
    return {"run_id": req.run_id, "status": "QUEUED"}
```

### Registering and Using Pricers

```python
# compute/pricers/my_pricer.py (source: registry.py confirmed pattern)
from compute.pricers.registry import register

def price_my_product(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: list,
    scenario_id: str,
) -> dict:
    """Return dict of measure_name -> value."""
    return {
        "PV": 100.0,
        "DV01": 0.5,
    }

# Auto-register on import:
register("MY_PRODUCT", price_my_product)

# In worker (source: worker.py needs refactor to use this)
from compute.pricers.registry import get_pricer

pricer_fn = get_pricer(task.product_type)  # Raises ValueError if not registered
measures = pricer_fn(position, instrument, market_snapshot, measures, scenario_id)
```

### Pagination Response

```python
# In service route (source: services/common/pagination.py confirmed pattern)
from services.common.pagination import PaginationParams, paginate

@app.get("/api/v1/runs")
def list_runs(params: PaginationParams = PaginationParams()):
    with db_conn() as conn:
        # Get total count
        total = conn.execute("SELECT count(*) FROM run").fetchone()[0]

        # Get paginated results
        rows = conn.execute(
            "SELECT * FROM run ORDER BY requested_at DESC OFFSET %(off)s LIMIT %(lim)s",
            {"off": params.offset, "lim": params.limit}
        ).fetchall()

    return paginate(rows, params.offset, params.limit, total)
    # Returns: {"data": [...], "offset": 0, "limit": 50, "total": 1000, "has_more": true}
```

### Shared Pydantic Models

```python
# shared/models/common.py (source: confirmed via Read)
from enum import Enum
from pydantic import BaseModel, Field

class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"

class PageRequest(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=1000)

# In any service:
from shared.models.common import Currency, PageRequest

class Position(BaseModel):
    position_id: str
    base_currency: Currency
```

### Error Handling

```python
# In route (source: services/common/errors.py pattern)
from services.common.errors import NotFoundError

@app.get("/api/v1/runs/{run_id}")
def get_run(run_id: str):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM run WHERE run_id = %(rid)s", {"rid": run_id}).fetchone()
        if not row:
            raise NotFoundError("run", run_id)  # Converted to 404 by error handler
        return row

# Error handler (automatic from factory) converts to:
# {"error": "not_found", "detail": "run not found: RUN-123", "status_code": 404}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| If/elif dispatch in worker.py | Registry pattern with decorators | 2022-2024 (Python ecosystem) | Enables plugin architecture, no code modification to add new pricers |
| Pydantic v1 (imperative validators) | Pydantic v2 (field validators, faster) | Pydantic v2 released May 2023 | 5-50x faster validation, cleaner validator syntax, Rust-backed |
| Individual service FastAPI setup | Service factory pattern (shared) | Established 2023+ (community practice) | Consistency across microservices, reduces duplication |
| SQL connection per request | Connection pooling (AsyncConnectionPool) | Psycopg3 (2021+) | Handles high concurrency, prevents connection exhaustion |
| Raw SQL everywhere | SQLAlchemy ORM or Psycopg3 with type safety | Ongoing (depends on use case) | For financial data: raw SQL preferred for auditability; ORM for CRUD |
| Manual pagination logic | Pagination helpers (offset/limit) | Common 2023+ | Standard shape, prevents off-by-one bugs |

**Deprecated/outdated:**
- **Pydantic v1 validators:** Use Pydantic v2's `field_validator` decorator instead; v1 required separate Validator classes
- **psycopg2:** Use psycopg3 (v3.1+); psycopg2 is single-threaded, no async support
- **Manual health checks:** Use `add_health_endpoint()` factory helper; manual endpoints duplicate code
- **If/elif dispatch:** Use registry pattern; if/elif chains don't scale to 10+ product types

## Open Questions

1. **Async API Services - Should we migrate FastAPI routes to async?**
   - What we know: Current services use sync routes. FastAPI recommends async for I/O-bound operations (DB queries). All pricers in worker are sync.
   - What's unclear: Is the overhead of async context manager pools worth it for MVP? Will worker stay sync or migrate to async?
   - Recommendation: Keep current sync routes for Phase 1 (simpler, works fine for MVP scale). Add async support in Phase 2 if performance testing shows contention on DB connections. Use sync `db_conn()` context manager for now; switch to `AsyncConnectionPool` only if needed.

2. **Docker Image Strategy - Multi-stage vs Single-stage?**
   - What we know: Multi-stage builds reduce image size from ~273MB to ~208MB (25% reduction). Tiangolo (FastAPI creator) publishes `uvicorn-gunicorn-fastapi-docker` as reference.
   - What's unclear: For MVP, is 65MB savings worth the build complexity? Should we use Tiangolo's image or build custom?
   - Recommendation: Use multi-stage build with separate builder and runtime stages. Base runtime on `python:3.11-slim` (120MB vs 900MB for full image). Example: builder stage installs dependencies, runtime stage copies installed packages and app code. Keep Dockerfile in `docker/` directory, share across services.

3. **Test Database - Should we use Docker for test DB in CI?**
   - What we know: GitHub Actions workflows can spin up PostgreSQL service container. Tests need isolated database snapshots.
   - What's unclear: Should CI use hosted PostgreSQL (e.g., AWS RDS) or container? Cost and performance implications?
   - Recommendation: Use PostgreSQL service container in GitHub Actions for CI (free, reliable, isolated). For local dev, use Docker Compose. Production uses managed Aurora.

4. **Terraform State Management - Remote state backend or local?**
   - What we know: Terraform state tracks deployed resources. Remote state (S3) prevents concurrent modification. Local state works for single developer.
   - What's unclear: Should we set up S3 backend for state, or is local state sufficient for MVP?
   - Recommendation: Start with local state in git (`.tfstate`). After Phase 1, migrate to S3 backend with DynamoDB lock before adding multiple developers. Document in terraform/README.md.

5. **Authentication - Is shared/auth/middleware.py used by services?**
   - What we know: `shared/auth/middleware.py` exists but is not imported by any service. No auth enforcement currently.
   - What's unclear: Should Phase 1 include auth middleware integration, or defer to Phase 2?
   - Recommendation: Defer auth to Phase 2 (phase-planning already defers "regulatory/audit/compliance" features). Phase 1 sets up the hooks but doesn't enforce auth. Placeholder: document in error response that `Authorization: Bearer <token>` is ignored for MVP.

## Sources

### Primary (HIGH confidence)

- **Code Review:** `services/common/service_base.py`, `services/common/db.py`, `services/common/health.py`, `services/common/errors.py`, `services/common/pagination.py` — Factory, DB connection, health, error, and pagination patterns already implemented and ready to use
- **Code Review:** `compute/pricers/registry.py`, `compute/pricers/base.py` — Registry pattern fully implemented with `_bootstrap()` auto-registration
- **Code Review:** `shared/models/common.py`, `shared/events/base.py`, `shared/config/settings.py` — Shared library structure with Pydantic models and BaseEvent already in place
- **Code Review:** `sql/001_mvp_core.sql` — Database schema with proper indexes and JSONB support verified
- **Official Documentation:** [Pydantic v2 Models](https://docs.pydantic.dev/latest/concepts/models/) — Validation and serialization patterns
- **Official Documentation:** [Psycopg 3 Documentation](https://www.psycopg.org/psycopg3/docs/) — Connection pool, async support, type system
- **Official Documentation:** [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/testing/) — Testing patterns, database testing, middleware

### Secondary (MEDIUM confidence)

- [FastAPI for Microservices: High-Performance Python API Design Patterns](https://talent500.com/blog/fastapi-microservices-python-api-design-patterns-2025/) — Microservices architecture patterns with middleware and shared utilities
- [Build Scalable Microservices with FastAPI: Architecture, Logging, and Config](https://medium.com/@azizmarzouki/build-scalable-microservices-with-fastapi-architecture-logging-and-config-made-simple-92e35552a707) — Service structure and configuration management
- [FastAPI Best Practices for Production: Complete 2026 Guide](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026) — Production patterns including error handling and middleware
- [Docker Multi-Stage Builds for Python Developers](https://collabnix.com/docker-multi-stage-builds-for-python-developers-a-complete-guide/) — Multi-stage Dockerfile strategy for reducing image size
- [Slimmer FastAPI Docker Images with Multi-Stage Builds](https://davidmuraya.com/blog/slimmer-fastapi-docker-images-multistage-builds/) — FastAPI-specific multi-stage Docker patterns
- [GitHub - Terraform AWS RDS Aurora Module](https://github.com/terraform-aws-modules/terraform-aws-rds-aurora) — Reference Terraform module for Aurora PostgreSQL provisioning
- [Terraform: Aurora RDS Cluster on AWS](https://medium.com/@nagarjun_nagesh/terraform-aurora-rds-cluster-on-aws-612e797d7471) — Aurora provisioning with Terraform examples
- [FastAPI with GitHub Actions and GHCR](https://pyimagesearch.com/2024/11/11/fastapi-with-github-actions-and-ghcr-continuous-delivery-made-simple/) — CI/CD pipeline for building and pushing container images
- [Deploying a FastAPI app with Kamal, AWS ECR, and Github Actions](https://dylancastillo.co/posts/deploy-a-fastapi-app-with-kamal-aws-ecr-and-github-actions.html) — GitHub Actions workflow for ECR deployment
- [Testing FastAPI Application with Pytest](https://medium.com/@gnetkov/testing-fastapi-application-with-pytest-57080960fd62) — Pytest fixtures and database testing strategies
- [Asynchronous Postgres with Python, FastAPI, and Psycopg 3](https://medium.com/@benshearlaw/asynchronous-postgres-with-python-fastapi-and-psycopg-3-fafa5faa2c08) — AsyncConnectionPool usage with FastAPI

### Tertiary (LOW confidence - marked for validation)

- [Registry Pattern - GeeksforGeeks](https://www.geeksforgeeks.org/system-design/registry-pattern/) — Design pattern explanation (general)
- [Implementing the Registry Pattern with Decorators in Python](https://medium.com/@tihomir.manushev/implementing-the-registry-pattern-with-decorators-in-python-de8daf4a452a) — Decorator-based registry pattern (confirmed by code review, no additional implementation needed)
- [Handling Circular Imports in Pydantic models with FastAPI](https://ciscore.co.uk/handling-circular-imports-in-pydantic-models-with-fastapi/) — Circular import mitigation (advice confirmed by Pydantic docs)
- [Pydantic Forward Declarations](https://www.getorchestra.io/guides/pydantic-forward-declarations-a-guide-for-fastapi-users) — Forward reference syntax for circular models

## Metadata

**Confidence breakdown:**
- **Standard stack (HIGH):** Verified by existing code (pyproject.toml), official docs (FastAPI, Pydantic, Psycopg), and codebase patterns
- **Architecture patterns (HIGH):** Implemented and verified in `services/common/` and `compute/pricers/registry.py`
- **Pitfalls (MEDIUM):** Based on common microservices issues + observed in codebase (e.g., duplicate models, registration timing)
- **Docker strategy (MEDIUM):** Multi-stage build is established best practice; Tiangolo's reference image confirms pattern
- **Terraform (MEDIUM):** Based on official Terraform modules and community examples; no custom code to verify against
- **CI/CD (MEDIUM):** GitHub Actions patterns established and verified by multiple sources; specifics depend on org setup

**Research date:** 2026-02-11
**Valid until:** 2026-03-12 (30 days from research date - FastAPI/Pydantic are stable, Terraform modules update quarterly)

**Assumptions used:**
1. All services continue to use PostgreSQL (no DB per service)
2. Lease-based task queue (FOR UPDATE SKIP LOCKED) continues in Phase 1 (no SQS introduction)
3. Shared library is importable by all services (Python path setup in docker/venv/CI)
4. Worker remains synchronous (no asyncio refactor in Phase 1)
5. Frontend remains separate React 18 app (no fastapi serving frontend in Phase 1)
