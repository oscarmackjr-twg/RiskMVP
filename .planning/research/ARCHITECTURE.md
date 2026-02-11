# Architecture Patterns: Institutional Portfolio Analytics Platform

**Domain:** Institutional fixed-income portfolio analytics (loan-heavy, distributed compute)
**Researched:** 2026-02-11
**Confidence:** HIGH (based on existing MVP patterns + domain standards)

## Executive Summary

The Risk MVP has established a battle-tested foundation: distributed task queue via PostgreSQL with lease-based claiming, immutable snapshots for auditability, and content-addressable hashing for idempotency. Scaling to 7 new services (instrument, portfolio, risk, cashflow, scenario, regulatory, data_ingestion) requires extending this pattern while adding analytics aggregation layers.

**Key insight:** The worker isn't just for pricing—it's the compute spine for ALL analytical engines (cashflow generation, risk calculations, regulatory aggregation). New services consume that worker output as analysis feeds. This creates a data pipeline architecture: worker→database→query services→UI, where each service specializes in query patterns and aggregations for a distinct analytical domain.

The recommended approach: Keep the distributed worker pattern unchanged, add 7 FastAPI query services at the edge, establish strict component boundaries, and implement analytics as multi-stage pipelines feeding from shared compute results.

## Recommended Architecture

### High-Level System Diagram

```
FRONTEND (React 18 + TypeScript, Vite)
    ↓
EDGE SERVICES (7x FastAPI, fast queries)
    ├─ marketdata_svc (8001) - Data snapshots
    ├─ run_orchestrator (8002) - Run lifecycle
    ├─ results_api (8003) - Pricing results
    ├─ portfolio_svc (8005) - Positions, aggregation
    ├─ risk_svc (8006) - Risk analytics
    ├─ cashflow_svc (8007) - Payment schedule queries
    ├─ regulatory_svc (8008) - Regulatory aggregates
    ├─ scenario_svc (8009) - Scenario management
    └─ data_ingestion_svc (8010) - ETL/import

    ↓ (async writes to DB after compute)

DISTRIBUTED COMPUTE (Worker pool, ECS Fargate)
    ├─ Claim tasks via FOR UPDATE SKIP LOCKED
    ├─ Run pricers (FX_FWD, AMORT_LOAN, FIXED_BOND, ...)
    ├─ Generate cashflows (loan amortization, prepayment)
    ├─ Calculate risk (DV01, spread duration, credit metrics)
    ├─ Aggregate regulatory (Basel, CECL, stress testing)
    └─ Write results to DB (upsert with idempotency)

    ↓ (all analytics data persisted)

SHARED DATA LAYER (PostgreSQL Aurora, SSD-backed)
    ├─ Snapshots (immutable): marketdata_snapshot, position_snapshot
    ├─ Control: run, run_task, portfolio
    ├─ Compute Output: valuation_result, cashflow_schedule, risk_metrics
    ├─ Reference: instrument, counterparty, pricing_model
    └─ Audit: published_run, run_break

    ↓ (served by query services)

CACHE LAYER (Optional: ElastiCache Redis for aggregates)
    └─ Pre-computed risk vectors, portfolio summaries, drill-down indices
```

### Component Boundaries

| Component | Responsibility | Communicates With | Data Ownership | Pattern |
|-----------|----------------|-------------------|-----------------|---------|
| **marketdata_svc** | Upload/retrieve market snapshots (curves, FX spots, spreads) | Frontend, run_orchestrator, workers | marketdata_snapshot table | CRUD + query |
| **run_orchestrator** | Run creation, task fanout, lifecycle management | Frontend, all workers, results_api | run, run_task tables | Batch controller |
| **results_api** | Query valuation results by run/position/scenario | Frontend, risk_svc, regulatory_svc | valuation_result table (read-only) | Query aggregator |
| **portfolio_svc** | Positions, aggregation levels, tagging, snapshots | Frontend, data_ingestion_svc | portfolio, position tables | Dimensional model |
| **risk_svc** | Risk vectors (DV01, spread duration, concentration, VaR), drill-down | Frontend, results_api (reads PVs) | risk_metrics table | Analytics aggregator |
| **cashflow_svc** | Payment schedules, maturity ladders, prepayment models | Frontend, risk_svc (for duration calc) | cashflow_schedule table | Schedule manager |
| **regulatory_svc** | Basel capital, CECL allowance, stress capital, RWA aggregation | Frontend, results_api (reads PVs) | regulatory_metrics table | Compliance aggregator |
| **scenario_svc** | Scenario definitions, bumps, market perturbations, scenario sets | Frontend, workers (appliers), run_orchestrator | scenario, scenario_set tables | Configuration server |
| **data_ingestion_svc** | Import positions, market data, counterparty, instrument definitions | ETL/batch jobs | instrument, position (via portfolio_svc) | ETL router |
| **Worker (compute)** | Pricer dispatch, cashflow generation, risk calculation, regulatory aggregation | Only database (PostgreSQL) | Intermediate: valuation_result, cashflow_schedule, risk_metrics | Task processor |

### Data Flow: End-to-End Run Execution

```
1. USER SUBMITS RUN
   run_orchestrator POST /api/v1/runs
   └─ Validates: market snapshot exists, positions loaded
   └─ Creates: run record (status=QUEUED)
   └─ Fans out tasks: (product_type, hash_bucket) shards
   └─ Task status: QUEUED

2. WORKER CLAIMS TASK
   Worker.claim_task() → FOR UPDATE SKIP LOCKED
   └─ Atomically: status → RUNNING, lease_until = now() + 60s
   └─ If lease expired, requeue automatically

3. WORKER PROCESSES POSITION
   For each position in assigned hash bucket:
     a) price_position() dispatch (FX_FWD, LOAN, BOND, ...)
     b) For each scenario (BASE, RATES_PARALLEL_1BP, ...):
        - Apply scenario bumps to market snapshot copy
        - Compute measures requested (PV, DV01, FX_DELTA, ...)
        - Write valuation_result (idempotent upsert)
     c) generate_cashflow_schedule() for loan/bond
        - Write cashflow_schedule (segment by period, amortization path)
     d) calculate_risk_metrics() for each measure
        - DV01, spread_duration, credit_metrics
        - Write risk_metrics

4. TASK COMPLETION
   mark_task_succeeded() → ON CONFLICT DO NOTHING
   └─ Status → SUCCEEDED, lease_until = NULL

5. RESULTS AGGREGATION (Query-time)
   risk_svc GET /api/v1/risk/{run_id}/market?agg=portfolio
   └─ Query results_api: SELECT * FROM valuation_result WHERE run_id = ?
   └─ Query risk_svc: SELECT * FROM risk_metrics WHERE run_id = ?
   └─ GROUP BY portfolio_node, AGGREGATE (SUM DV01, WEIGHTED DURATION, ...)
   └─ Optional Redis cache for repeated aggregations

6. PUBLISH/ARCHIVE
   run_orchestrator POST /api/v1/runs/{run_id}/publish
   └─ INSERT published_run (immutable archive)
   └─ Hash all inputs for audit trail
```

### Compute Pipeline: Multi-Stage Analytics

The worker processes positions in this order:

```
POSITION SNAPSHOT → [STAGE 1: PRICING]
                     ├─ FX_FWD: spot * forward rate
                     ├─ AMORT_LOAN: DCF(cashflows, ois+spread)
                     └─ FIXED_BOND: clean price + accrued

                   [STAGE 2: SCENARIO BUMPS]
                     ├─ BASE scenario (as-is)
                     ├─ RATES_PARALLEL_1BP (all curves +1bp)
                     ├─ SPREAD_25BP (spread curves +25bp)
                     └─ FX_SPOT_1PCT (FX spot ±1%)

                   [STAGE 3: CASHFLOW GENERATION]
                     ├─ generate_schedule(instrument, as_of_date)
                     ├─ Apply amortization model (fully amort, io, po)
                     └─ Store with prepayment assumptions (SMM, CPR)

                   [STAGE 4: RISK METRICS]
                     ├─ DV01 = PV(bumped) - PV(base)
                     ├─ Spread_Duration = (PV(spread+25bp) - PV(spread-25bp)) / 50bp
                     ├─ Credit metrics from cashflow scenarios
                     └─ FX delta, key-rate durations

                   → valuation_result, cashflow_schedule, risk_metrics (DB writes)
```

### Deployment Architecture (AWS ECS Fargate + RDS Aurora)

```
AWS ACCOUNT
├─ ECS CLUSTER (risk-cluster)
│  ├─ Fargate Task (marketdata_svc:8001) x2 (HA)
│  ├─ Fargate Task (run_orchestrator:8002) x2 (HA)
│  ├─ Fargate Task (results_api:8003) x4 (read-heavy)
│  ├─ Fargate Task (portfolio_svc:8005) x2 (HA)
│  ├─ Fargate Task (risk_svc:8006) x4 (aggregation-heavy)
│  ├─ Fargate Task (cashflow_svc:8007) x2 (on-demand)
│  ├─ Fargate Task (regulatory_svc:8008) x3 (compliance)
│  ├─ Fargate Task (scenario_svc:8009) x1 (light)
│  ├─ Fargate Task (data_ingestion_svc:8010) x1 (batch)
│  └─ Fargate Task (compute-worker) x10-50 (auto-scaling)
│
├─ RDS AURORA (PostgreSQL 15+, read replicas)
│  ├─ Writer: r6i.2xlarge (compute-heavy positions)
│  ├─ Readers (3x): r6i.xlarge (for analytics queries)
│  ├─ Automated backup: 30 days
│  ├─ Connection pooling: Amazon RDS Proxy
│  └─ Monitoring: Enhanced monitoring + slow query log
│
├─ ElastiCache Redis (Optional, for aggregates)
│  ├─ 2-node cache.r6g.large (failover mode)
│  ├─ TTL: 4 hours (aggregates, scenario cache)
│  └─ Eviction: allkeys-lru
│
├─ ALB (Application Load Balancer)
│  └─ Routes /mkt/* → marketdata_svc
│              /orch/* → run_orchestrator
│              /results/* → results_api
│              /portfolio/* → portfolio_svc
│              /risk/* → risk_svc
│              /cashflow/* → cashflow_svc
│              /regulatory/* → regulatory_svc
│              /scenario/* → scenario_svc
│
├─ CloudWatch Logs (centralized)
│  ├─ Application logs: /ecs/risk-platform/{service-name}
│  ├─ Task logs: duration, queue depth, worker utilization
│  └─ Alarms: error_rate > 5%, run_time > 1h, task_timeout
│
└─ S3 (audit & archive)
   ├─ published_runs/ (immutable run archives)
   ├─ position_snapshots/ (historical daily)
   └─ marketdata_snapshots/ (reference data backups)
```

### Service-to-Service Communication

**Synchronous (HTTP REST):**
- Frontend → All edge services (reads/queries)
- run_orchestrator → marketdata_svc (verify snapshot exists)
- results_api → database (read-only, no inter-service calls)
- risk_svc → results_api (fetch valuation_result) **optional if co-located in query**
- scenario_svc → database (ref data, not compute-time)

**Asynchronous (Database-driven):**
- Worker → PostgreSQL (claim tasks, write results)
- All services → PostgreSQL (shared schema, eventual consistency)

**NO cross-service RPC calls during compute.** Workers only read/write database. Edge services compose from database tables independently.

### Database Schema Evolution (Beyond MVP)

Additional tables required for 7-service expansion:

```sql
-- Dimension tables (reusable across services)
CREATE TABLE portfolio (
  portfolio_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  node_type TEXT CHECK (node_type IN ('FUND','SUB_FUND','DESK','BOOK')),
  parent_portfolio_id TEXT REFERENCES portfolio(portfolio_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE position (
  position_id TEXT NOT NULL,
  portfolio_id TEXT NOT NULL REFERENCES portfolio(portfolio_id),
  instrument_id TEXT NOT NULL REFERENCES instrument(instrument_id),
  quantity NUMERIC NOT NULL,
  currency TEXT NOT NULL,
  acquisition_date DATE,
  position_snapshot_id TEXT NOT NULL REFERENCES position_snapshot(position_snapshot_id),
  PRIMARY KEY (position_id, position_snapshot_id)
);

CREATE TABLE counterparty (
  counterparty_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  internal_id TEXT,
  credit_rating TEXT,
  sector TEXT,
  country TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Compute output tables (written by worker)
CREATE TABLE valuation_result (
  run_id TEXT NOT NULL REFERENCES run(run_id),
  position_id TEXT NOT NULL,
  scenario_id TEXT NOT NULL DEFAULT 'BASE',
  measures_json JSONB NOT NULL,  -- {pv, accrued, clean_price, fx_delta, ...}
  compute_meta_json JSONB,       -- {pricing_model, model_version, ...}
  input_hash TEXT NOT NULL,      -- SHA256 for audit
  PRIMARY KEY (run_id, position_id, scenario_id)
);

CREATE TABLE cashflow_schedule (
  run_id TEXT NOT NULL REFERENCES run(run_id),
  position_id TEXT NOT NULL,
  period_number INT NOT NULL,
  pay_date DATE NOT NULL,
  principal NUMERIC NOT NULL,
  interest NUMERIC NOT NULL,
  total_payment NUMERIC NOT NULL,
  balance NUMERIC,
  prepayment_assumption TEXT,    -- CPR%, SMM, fixed
  PRIMARY KEY (run_id, position_id, period_number)
);

CREATE TABLE risk_metrics (
  run_id TEXT NOT NULL REFERENCES run(run_id),
  position_id TEXT NOT NULL,
  metric_type TEXT NOT NULL,     -- 'DV01', 'SPREAD_DURATION', 'CREDIT_SPREAD', 'FX_DELTA'
  base_value NUMERIC,
  bumped_value NUMERIC,
  metric_value NUMERIC NOT NULL,
  scenario_id TEXT DEFAULT 'BASE',
  PRIMARY KEY (run_id, position_id, metric_type, scenario_id)
);

CREATE TABLE regulatory_metrics (
  run_id TEXT NOT NULL REFERENCES run(run_id),
  counterparty_id TEXT REFERENCES counterparty(counterparty_id),
  metric_type TEXT NOT NULL,     -- 'BASEL_RWA', 'CECL_ALLOWANCE', 'STRESS_CAPITAL'
  value NUMERIC NOT NULL,
  threshold NUMERIC,
  regulatory_framework TEXT,     -- 'BASEL3', 'CCAR', 'CECL'
  PRIMARY KEY (run_id, metric_type, regulatory_framework)
);

CREATE TABLE scenario (
  scenario_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  bumps_json JSONB NOT NULL,     -- {rates: {usd_ois: 0.0001}, fx: {eurusd: 0.01}, spreads: ...}
  created_by TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE scenario_set (
  scenario_set_id TEXT PRIMARY KEY,
  scenarios TEXT[] NOT NULL,     -- references scenario(scenario_id)
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Indexes for query performance:**
```sql
CREATE INDEX valuation_result_run_idx ON valuation_result(run_id);
CREATE INDEX valuation_result_run_scenario_idx ON valuation_result(run_id, scenario_id);
CREATE INDEX valuation_result_position_idx ON valuation_result(run_id, position_id);

CREATE INDEX cashflow_schedule_run_position_idx ON cashflow_schedule(run_id, position_id);
CREATE INDEX cashflow_schedule_pay_date_idx ON cashflow_schedule(pay_date);

CREATE INDEX risk_metrics_run_idx ON risk_metrics(run_id);
CREATE INDEX risk_metrics_metric_type_idx ON risk_metrics(metric_type);

CREATE INDEX regulatory_metrics_run_idx ON regulatory_metrics(run_id);
```

## Patterns to Follow

### Pattern 1: Immutable Snapshots with Content Hashing

**What:** Market data and positions are stored as full JSON blobs with SHA-256 hashes. No updates; new snapshots create new records.

**When:** Any time you need auditability, reproducibility, or scenario replay. This is the primary pattern for this system.

**Why:**
- Enables instant rollback/replay of any historical run
- Proves determinism: same inputs → same outputs
- Audit trail is built-in (who uploaded what snapshot when)
- Workers can process in parallel without locking concerns

**Example:**
```python
def sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

# Upload snapshot
payload_hash = sha256_json(market_data)
INSERT INTO marketdata_snapshot (snapshot_id, payload_json, payload_hash, ...)
VALUES (...)
ON CONFLICT (snapshot_id) DO NOTHING;  # Idempotent
```

### Pattern 2: Lease-Based Task Queue (FOR UPDATE SKIP LOCKED)

**What:** Workers claim tasks via PostgreSQL row-level locking with automatic timeout-based requeue.

**When:** You need distributed task processing without external queue (SQS, Kafka, RabbitMQ). Avoids operational complexity of message brokers.

**Why:**
- PostgreSQL is already required (data store)
- Single source of truth: database is authoritative on task state
- Automatic recovery: expired leases auto-requeue
- No distributed consensus needed

**Example:**
```python
CLAIM_SQL = """
WITH candidate AS (
  SELECT task_id FROM run_task
  WHERE (status = 'QUEUED')
     OR (status = 'RUNNING' AND leased_until < now())
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE run_task t
SET status = 'RUNNING',
    leased_until = now() + (60 || ' seconds')::interval
FROM candidate
WHERE t.task_id = candidate.task_id
RETURNING t.*;
```

**Consequences:**
- At 1000+ concurrent workers, consider SQS migration (different queue mechanism, same semantics)
- Lease_seconds must balance between: too short (thrashing), too long (delayed requeue)
- For long-running tasks, consider heartbeat updates instead of single lease

### Pattern 3: Measure-Based Computation (Request-Time Filtering)

**What:** Pricers compute only requested measures; measures list is passed to each pricer.

**When:** You have many possible outputs (PV, DV01, Greeks, spreads, credit metrics) but most runs request only a subset.

**Why:**
- Avoids wasteful computation of unused measures
- Explicit contract: API caller declares what they need
- Easy to add new measures without breaking existing code

**Example:**
```python
def price_loan(position, instrument, market_snapshot, measures, scenario_id):
    pv_base = compute_pv(...)
    results = {"PV": pv_base}

    if "DV01" in measures:
        pv_bumped = compute_pv(..., bump_rates=True)
        results["DV01"] = pv_bumped - pv_base

    if "ACCRUED_INTEREST" in measures:
        results["ACCRUED_INTEREST"] = compute_accrued(...)

    return results
```

### Pattern 4: Scenario Application via Copy-and-Modify

**What:** Scenarios are applied to a copy of the market snapshot, never in-place.

**When:** You need to compute sensitivities (rates ±1bp, spreads ±25bp) without mutation concerns.

**Why:**
- Avoids bugs from shared mutable state
- Clean separation: BASE scenario is pristine, derived scenarios are clean derivations
- Functional programming approach reduces state management bugs

**Example:**
```python
def apply_scenario(market_snapshot, scenario_id):
    import copy
    bumped = copy.deepcopy(market_snapshot)

    if scenario_id == "RATES_PARALLEL_1BP":
        for key in bumped["curves"]:
            for node in bumped["curves"][key]["nodes"]:
                node["rate"] += 0.0001  # +1bp
    elif scenario_id == "SPREAD_25BP":
        for key in bumped["curves"]:
            if "spread" in key.lower():
                for node in bumped["curves"][key]["nodes"]:
                    node["rate"] += 0.0025  # +25bp

    return bumped
```

### Pattern 5: UPSERT for Idempotency

**What:** All writes use `ON CONFLICT ... DO UPDATE SET`, enabling safe retries.

**When:** You have retryable jobs (workers, services) that might run multiple times.

**Why:**
- Eliminates duplicates from retry storms
- Audit trail shows all attempts, not just last success
- Greatly simplifies error recovery (just retry, DB handles idempotency)

**Example:**
```python
INSERT INTO valuation_result (run_id, position_id, scenario_id, measures_json, input_hash)
VALUES (...)
ON CONFLICT (run_id, position_id, scenario_id) DO UPDATE SET
  measures_json = EXCLUDED.measures_json,
  input_hash = EXCLUDED.input_hash,
  created_at = now();
```

### Pattern 6: Service as Query Layer (Async Composition)

**What:** Each edge service queries the shared database independently. No service-to-service RPC during compute. Composition happens in query time or frontend.

**When:** You have independent analytical domains (risk, portfolio, regulatory, cashflow) that operate on shared compute results.

**Why:**
- Avoids coupling between services
- Enables independent scaling (risk_svc can have 10 instances, scenario_svc has 1)
- Reduces latency: services don't wait for each other
- Easier debugging: each service has isolated DB queries

**Example:**
```python
# risk_svc does its own queries, doesn't call portfolio_svc
@risk_router.get("/api/v1/risk/{run_id}/portfolio")
def aggregate_portfolio_risk(run_id: str):
    with db_conn() as conn:
        # Direct query, no RPC
        rows = conn.execute("""
            SELECT position_id, SUM(metric_value) as dv01
            FROM risk_metrics
            WHERE run_id = %s AND metric_type = 'DV01'
            GROUP BY position_id
        """, (run_id,)).fetchall()
    return {"portfolio_dv01": sum(r["dv01"] for r in rows)}
```

### Pattern 7: Hash-Bucket Sharding for Parallelization

**What:** Positions are sharded by hash(position_id) % hash_mod into buckets. Each bucket becomes a separate task.

**When:** You have thousands of positions and want to parallelize pricing across workers.

**Why:**
- Deterministic: same position always goes to same bucket
- Flexible: increase hash_mod to split buckets further
- Independent: buckets have no cross-position dependencies

**Example:**
```python
hash_mod = 10  # Split into 10 buckets
for product_type in ["FX_FWD", "AMORT_LOAN", "FIXED_BOND"]:
    for bucket in range(hash_mod):
        task_id = f"TASK-{run_id}-{product_type}-{bucket}"
        INSERT INTO run_task (task_id, product_type, hash_mod, hash_bucket)

# Worker filters positions
def in_bucket(position_id, hash_mod, hash_bucket):
    h = int(hashlib.sha256(position_id.encode()).hexdigest(), 16)
    return (h % hash_mod) == hash_bucket
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Mutable Snapshots

**What:** Storing snapshots but allowing updates (UPDATE marketdata_snapshot SET ... WHERE snapshot_id = ...).

**Why bad:**
- Cannot replay historical runs (snapshot changes)
- Audit trail is lost (who changed what)
- Concurrent access causes races (worker reads stale data mid-computation)
- Reproducibility impossible (same run_id gives different results on retry)

**Instead:** Always INSERT new snapshots, never UPDATE. Use `payload_hash` to detect duplicates, INSERT ... ON CONFLICT DO NOTHING.

### Anti-Pattern 2: Long-Lived Worker Transactions

**What:** Worker holds a database connection/transaction for entire position batch (hours).

**Why bad:**
- Blocks other transactions (vacuum, index creation)
- Connection pool exhaustion
- Network interruption loses entire batch
- Lease timeout doesn't trigger while transaction is open

**Instead:** Claim task, process quickly (seconds), write results in one transaction, release. If processing takes >60s, refactor into sub-tasks.

### Anti-Pattern 3: Cross-Service RPC During Compute

**What:** Worker calls risk_svc HTTP API to compute metrics, which calls results_api for valuations.

**Why bad:**
- Network latency (10ms × 1000 positions = 10s per worker)
- Cascading failures (one service down halts all workers)
- Hard to reason about consistency (partial responses)
- No transactional guarantee across services

**Instead:** All workers write results to database. Query services read from database. Composition at query time (not compute time).

### Anti-Pattern 4: Scenario Mutations Inside Compute

**What:** Applying scenario bumps by mutating the same market_snapshot object passed to multiple pricers.

**Why bad:**
- Race conditions (pricer A bumps rates, pricer B sees bumped rates for BASE scenario)
- Non-deterministic results (order of processing changes outputs)
- Audit trail impossible (which snapshot was actually used?)

**Instead:** Use `copy.deepcopy()` or immutable data structures. Each scenario gets its own copy of the snapshot.

### Anti-Pattern 5: No Task Status Tracking

**What:** Workers process tasks but don't update status (QUEUED, RUNNING, SUCCEEDED, FAILED, DEAD).

**Why bad:**
- Cannot distinguish: stuck/slow workers from completed work
- No automatic requeue (tasks hang forever)
- Impossible to retry dead tasks
- No metrics on job success rate

**Instead:** Always update status. Use lease-based timeout for automatic requeue. Mark as DEAD only after max_attempts.

### Anti-Pattern 6: Single Service Instance in Production

**What:** Running portfolio_svc, risk_svc, etc. with 1 Fargate task (no redundancy).

**Why bad:**
- Single point of failure (rolling update = downtime)
- Cannot handle spikes (one instance maxed = requests timeout)
- No zero-downtime deployments

**Instead:** Minimum 2 instances per service (HA), 4+ for query-heavy services (results_api, risk_svc). Use ALB health checks to remove failing instances.

### Anti-Pattern 7: Unbounded Query Results

**What:** Results API returns all valuation_results for a run without pagination.

**Why bad:**
- Frontend hangs (50K positions × 10 scenarios = 500K rows)
- Database memory exhaustion (sorting huge result sets)
- Network timeout

**Instead:** Implement pagination (limit=1000, offset=0). Add efficient pagination in database (keyset pagination preferred for large result sets).

### Anti-Pattern 8: No Idempotency in Worker Writes

**What:** Worker does INSERT (not UPSERT) when writing valuation_result.

**Why bad:**
- Duplicate key violation on retry
- Task marked failed even though result was stored
- Downstream aggregations count duplicates

**Instead:** Use UPSERT: `INSERT ... ON CONFLICT (run_id, position_id, scenario_id) DO UPDATE SET ...`

## Scalability Considerations

| Concern | At 100 Positions | At 10K Positions | At 1M Positions |
|---------|------------------|------------------|------------------|
| **Worker Count** | 1 (dev) | 5-10 | 50-100+ (with hash_mod=100) |
| **Task Queue Depth** | <10 | <1000 (Fargate scales up) | <10K (consider Kafka if > 100K/sec task creation) |
| **Database Connection Pool** | 5 | 50 (1-2x workers) | 200+ (RDS Proxy recommended) |
| **Pricing Latency** | <1s per position | 5-10 min total | 30-60 min (with 100 workers, 100 scenarios) |
| **Query Latency** | <100ms (full table scan ok) | <500ms (indexes required) | <2s (with aggregation caching) |
| **Storage (per run)** | ~5MB (snapshots + results) | ~500MB | ~50GB (consider S3 archival for old runs) |

**Scaling strategy by phase:**
- Phase 1 (100 positions): 1 worker, 1 database instance (dev/test OK)
- Phase 2 (10K positions): 5-10 workers on Fargate, Aurora writer + 1-2 readers
- Phase 3 (100K+ positions): 50+ workers, Aurora with read replicas, RDS Proxy, Redis aggregation cache, SQS task queue (instead of FOR UPDATE)

## Component Build Order & Dependencies

**Recommended build sequence for minimal rework:**

1. **Data Layer (Week 1-2)** — Run these first, all services depend on it
   - Extend DDL: portfolio, position, counterparty, scenario, cashflow_schedule, risk_metrics, regulatory_metrics tables
   - Deploy database migrations (sql/002_analytics_tables.sql, sql/003_indexes.sql)
   - Requires: Database access, Terraform for Aurora setup

2. **marketdata_svc (Week 2)** — Already exists, minor updates
   - Add endpoints for scenario retrieval (GET /api/v1/scenarios/{scenario_id})
   - Requires: Scenario table in database

3. **scenario_svc (Week 2-3)** — Lightweight config server
   - Manages scenario definitions (BASE, RATES_1BP, etc.)
   - Does not call other services
   - Requires: scenario, scenario_set tables

4. **compute/ enhancements (Week 3-4)** — Core pricer logic
   - Add pricers for new product types (STRUCTURED, CALLABLE_BOND, ABS_MBS, DERIVATIVES)
   - Implement cashflow generators (loan amortization, prepayment)
   - Implement risk calculators (DV01, duration, credit metrics)
   - Implement regulatory aggregators (Basel, CECL)
   - Requires: Existing worker.py, existing pricers as reference

5. **portfolio_svc (Week 4-5)** — Portfolio hierarchy & aggregation
   - Portfolio CRUD (create/list/get)
   - Position ingestion (POST /api/v1/positions from snapshots)
   - Portfolio tagging (desk, strategy, counterparty)
   - Does not call other services (pure DB queries)
   - Requires: portfolio, position, counterparty tables; can start with mock data

6. **results_api (Week 5)** — Query layer for pricing results
   - Already exists, extend with new result types
   - GET /api/v1/results/{run_id} (returns valuation_result + cashflow_schedule + risk_metrics)
   - Support drill-down by position_id, scenario_id, product_type
   - Requires: valuation_result, cashflow_schedule, risk_metrics tables populated by worker

7. **risk_svc (Week 5-6)** — Risk analytics aggregation
   - Portfolio risk aggregation (SUM DV01, WEIGHTED DURATION, CONCENTRATION)
   - Market risk queries (sensitivities, key-rate durations)
   - Credit risk queries (spread exposure, PD aggregates)
   - Queries results_api for base PVs (read-only composition)
   - Requires: risk_metrics table; results_api working

8. **cashflow_svc (Week 6)** — Cashflow schedule queries
   - GET /api/v1/cashflows/{run_id}/{position_id} (payment schedule)
   - Maturity ladder aggregation
   - Duration bridge (principal decay, interest accrual)
   - Requires: cashflow_schedule table populated by worker

9. **regulatory_svc (Week 6-7)** — Compliance reporting
   - GET /api/v1/regulatory/{run_id}/capital (RWA, VaR, stress capital)
   - CECL allowance by counterparty
   - Regulatory stress scenarios (CCAR, DFAST)
   - Requires: regulatory_metrics table; results_api for PVs

10. **data_ingestion_svc (Week 7-8)** — ETL/batch import
    - POST /api/v1/import/positions (bulk load from CSV/JSON)
    - POST /api/v1/import/instruments (instrument master data)
    - POST /api/v1/import/marketdata (market data snapshots)
    - Validates against contracts before insert
    - Requires: All dimension tables (portfolio, position, instrument, counterparty)

11. **Frontend enhancements (Week 8-9)** — UI for new services
    - RunLauncher: Add scenario selection, measure filtering
    - RunResults: Add risk aggregation views, cashflow ladder, regulatory summary
    - RunCube: Drill-down by position, scenario, risk factor
    - Requires: All backend services functional with sample data

12. **Testing & QA (Week 9-10)**
    - Golden tests for new pricers (fixture-based, expected PVs)
    - Integration tests (end-to-end runs through all services)
    - Load tests (500 positions × 10 workers, target <10min runtime)
    - Performance tests (query latency <500ms at 100K positions)

**Critical path:** Data layer → compute enhancements → results_api → risk_svc (dependencies: results_api). Can parallelize portfolio_svc, scenario_svc (independent).

**Gotchas:**
- Don't start frontend until results_api + at least one service (risk_svc) has sample data
- Compute enhancements must be tested in isolation (golden tests) before adding workers
- data_ingestion_svc depends on portfolio_svc (position validation), but can mock until portfolio_svc ready

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Existing MVP patterns** | HIGH | Worker lease queue, snapshots, UPSERT, scenario application are proven in codebase |
| **Distributed worker scaling** | HIGH | FOR UPDATE SKIP LOCKED is production-grade; scaled to 1000s of workers in financial systems |
| **Component boundaries** | MEDIUM-HIGH | Clear split between compute (worker) and query (services), but may need iteration on inter-service coupling (risk_svc → results_api) |
| **AWS ECS Fargate patterns** | HIGH | Standard setup; financial firms use this for compute workloads regularly |
| **Database scalability to 1M positions** | MEDIUM | PostgreSQL + Aurora handles this, but requires RDS Proxy connection pooling + read replicas; query optimization needed |
| **Multi-stage compute pipeline** | HIGH | Cashflow → risk → regulatory aggregation is standard financial architecture |
| **Idempotency via UPSERT** | HIGH | Well-established pattern, no ambiguity |
| **Service-as-query-layer (no RPC in compute)** | HIGH | Clean separation, proven in financial risk systems |

## Gaps to Address in Phase-Specific Research

- **Phase 2 (Compute Enhancements):** Need detailed research on structured product pricers (CMS swaps, exotic bonds, ABS/MBS prepayment models). Monte Carlo engine complexity not yet scoped.
- **Phase 3 (Regulatory):** CCAR/DFAST stress scenario definitions, CECL reserve methodology. Compliance team input required.
- **Phase 4 (Data Ingestion):** CSV/JSON schema validation, reconciliation against upstream systems (Bloomberg, FactSet). Data quality rules TBD.
- **Performance & Caching:** Redis aggregation strategy, query result caching policy (4h TTL?), materialized view vs. on-demand aggregation trade-off not yet determined.

---

## Quick Reference: Service Ports & Responsibilities

| Port | Service | Responsibilities |
|------|---------|------------------|
| 8001 | marketdata_svc | Upload/retrieve market snapshots; scenario ref data |
| 8002 | run_orchestrator | Run creation, task fanout, lifecycle |
| 8003 | results_api | Query pricing results (valuation_result table) |
| 8005 | portfolio_svc | Portfolio hierarchy, positions, tagging, aggregation |
| 8006 | risk_svc | Risk analytics (DV01, duration, concentration, VaR) |
| 8007 | cashflow_svc | Payment schedules, maturity ladders |
| 8008 | regulatory_svc | Basel capital, CECL, stress testing |
| 8009 | scenario_svc | Scenario definitions and management |
| 8010 | data_ingestion_svc | Bulk import (positions, instruments, market data) |
| — | compute-worker | Distributed pricing, cashflow generation, risk calc, regulatory agg |

---

## Sources

- **Existing codebase:** `.claude/docs/architectural_patterns.md`, `CLAUDE.md`, `sql/001_mvp_core.sql`
- **PostgreSQL patterns:** FOR UPDATE SKIP LOCKED (row-level locking with timeout), ON CONFLICT UPSERT (idempotency)
- **AWS reference:** ECS Fargate task auto-scaling, RDS Aurora with read replicas, RDS Proxy connection pooling
- **Financial domain:** Distributed risk computation is standard in institutional fixed-income platforms (Bloomberg PORT, Numerix, SunGard Risk)
- **Content-addressable storage:** SHA-256 hashing for snapshots is industry-standard for audit trails in regulated finance

