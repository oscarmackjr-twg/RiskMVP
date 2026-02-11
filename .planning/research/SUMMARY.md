# Research Summary: Institutional Portfolio Analytics Platform Expansion

**Domain:** Institutional fixed-income portfolio analytics with distributed compute (loan-heavy)
**Researched:** 2026-02-11
**Overall confidence:** HIGH

## Executive Summary

The Risk MVP has built a proven foundation for distributed financial analytics: lease-based task queue via PostgreSQL (`FOR UPDATE SKIP LOCKED`), immutable snapshots with content-addressable hashing, and UPSERT-based idempotency. This research confirms that scaling from 3 FastAPI services + 1 worker to 10 services + worker pool requires **no architectural rethinking**—only extension of proven patterns.

**The key insight:** Separate compute from query analytics. Workers process all instruments through the full pipeline (pricing → cashflow generation → risk calculation → regulatory aggregation), writing results to database. Seven new FastAPI services independently query those results for domain-specific analytics (portfolio aggregation, risk vectors, regulatory compliance). This achieves loose coupling and independent scalability without cross-service RPC calls during compute.

**Deployment model:** AWS ECS Fargate with RDS Aurora PostgreSQL. Workers auto-scale with task queue depth. Services scale independently by analytical domain. Single database is the source of truth, enabling eventual consistency across services without distributed transactions.

## Key Findings

### Stack
**Framework:** FastAPI 0.104+ (all services), Python 3.11+, PostgreSQL 15+, AWS ECS Fargate + Aurora
**Compute:** Distributed workers with lease-based queue (FOR UPDATE SKIP LOCKED), content-addressed snapshots (SHA-256), UPSERT idempotency
**Database:** PostgreSQL with JSONB for flexible payloads, connection pooling via RDS Proxy, read replicas for analytics queries

### Architecture
**Service topology:** 10 FastAPI services (8001-8010) + distributed worker pool. Services are query layers, never compute engines. Workers are compute engines, never call services—only database.
**Data flow:** Immutable snapshots → distributed worker (claim task, price, generate cashflows, calculate risk, aggregate regulatory) → write results to DB → query services independently aggregate and serve UI.
**Scalability:** Hash-bucket sharding enables parallelization across workers. Database indexes on run_id, scenario_id, position_id for fast aggregation. Optional Redis caching for repeated aggregations.

### Critical Pitfall
**Service-to-service RPC during compute.** If worker calls risk_svc → results_api during position processing, it creates: (1) network latency (10ms × 1000 positions = 10s overhead), (2) cascading failures (one slow service halts all workers), (3) non-deterministic ordering (depends on network timing). **Solution:** All compute writes to database. Query services read database independently. Composition at query time, not compute time.

## Implications for Roadmap

### Recommended Phase Structure

#### Phase 1: Foundation (Weeks 1-4)
**Build:** Data layer extensions + compute engine enhancements
- Extend PostgreSQL: portfolio, position, cashflow_schedule, risk_metrics, regulatory_metrics, scenario tables
- Add Terraform for Aurora + read replicas + RDS Proxy + ElastiCache (optional)
- Implement new pricers: STRUCTURED, CALLABLE_BOND, ABS_MBS, DERIVATIVES (reference existing FX_FWD, LOAN, BOND patterns)
- Implement cashflow generators: loan amortization, prepayment models (CPR, SMM)
- Implement risk calculators: DV01, spread_duration, credit metrics, key-rate durations
- Implement regulatory aggregators: Basel RWA, CECL allowance, stress capital charge
- **Avoid:** Don't add services yet. Enhance compute engine first with golden tests for each new pricer.

#### Phase 2: Edge Services Layer (Weeks 5-8)
**Build:** 7 FastAPI query services (portfolio, risk, cashflow, regulatory, scenario, data_ingestion + data_ingestion_svc)
- portfolio_svc: Portfolio hierarchy (fund → desk → book), position tagging, aggregation levels
- scenario_svc: Scenario CRUD, scenario set management
- results_api: Extend with cashflow/risk results drill-down
- risk_svc: Portfolio risk aggregation (SUM/WEIGHTED/CONCENTRATION), market risk vectors
- cashflow_svc: Payment schedule queries, maturity ladder, duration bridge
- regulatory_svc: Regulatory stress scenarios, capital aggregation
- data_ingestion_svc: Bulk import (positions, instruments, market data) with validation
- **Pattern:** Each service queries DB independently. No RPC calls between services. Use ALB routing.

#### Phase 3: Integration & Analytics (Weeks 9-12)
**Build:** Frontend enhancements + caching + performance optimization
- Frontend: Add scenario selection, measure filtering, drill-down views
- Add Redis aggregation cache (4h TTL) for repeated portfolio aggregations
- Add pagination to all query endpoints (keyset pagination for 1M+ positions)
- Integration tests: End-to-end runs through worker + all services
- Load testing: 1000 positions × 10 workers, target <10 min per run
- **Gotcha:** Don't add caching until core functionality works and queries are slow. Build for correctness first.

#### Phase 4: Monitoring & Scaling (Weeks 13+)
**Build:** Observability, production-grade automation
- CloudWatch Logs: Centralized logging, slow query detection
- Alarms: Worker queue depth, task timeout, service error rate
- Auto-scaling: Fargate target tracking (CPU 70%), worker scaling by queue depth
- Database optimization: Slow query log, query plan analysis
- S3 archival: Published runs to long-term storage (cost optimization)

### Phase Ordering Rationale

1. **Data layer first** (Phase 1a) because all downstream services depend on it. No point building query services without tables.
2. **Compute enhancements next** (Phase 1b) because worker must be production-ready before scaling. Test each new pricer with golden tests in isolation.
3. **Edge services** (Phase 2) can parallelize once compute is stable. portfolio_svc, risk_svc, scenario_svc are independent.
4. **Frontend & caching** (Phase 3) only after backend is functional. Premature caching hides bugs.
5. **Monitoring** (Phase 4) once you have enough services to need it.

### Why This Order Avoids Rework

- **Don't build services before compute is done:** Otherwise services query incomplete result sets. Cascades to frontend rework.
- **Don't add caching before optimization:** You'll cache the wrong queries. Profile first, cache second.
- **Don't parallelize workers until new pricers are stable:** Broken pricers fail at scale. Test with 1 worker first.
- **Don't use SQS until PostgreSQL queue is exhausted:** FOR UPDATE works fine to 10K tasks/sec. Simpler ops.

## Research Flags for Phase-Specific Work

### Phase 1 - Data Layer
- **Flag:** Aurora write performance for 1M positions × 10 scenarios = 10M result rows/run. Need load test (INSERT 10M rows in <10s, queries <500ms). Consider partitioning valuation_result by run_id or scenario_id if slow.
- **Flag:** JSONB vs. columns tradeoff for measures_json. Current design uses JSONB for flexibility. May need JSON indexing (GIN) for measure-specific queries.

### Phase 1 - Compute Enhancements
- **Flag:** Structured product pricers (CMS swaps, options). May need Monte Carlo engine. Complexity unknown, needs specialist research.
- **Flag:** ABS/MBS prepayment models. CPR (conditional prepayment rate) vs. SMM (single monthly mortality) vs. stochastic models. Current placeholder only.
- **Flag:** Regulatory stress scenarios (CCAR, DFAST). Requires compliance team input. Stress curves not yet defined.

### Phase 2 - Services
- **Flag:** Risk aggregation correctness. When computing portfolio DV01 (SUM of position DVs), must verify accounting for currency conversion, scenario blending, correlations. Needs cross-validation with Bloomberg PORT.
- **Flag:** Data consistency race. risk_svc queries risk_metrics table, but worker might still be writing. Results might be partial. Add result.status = 'COMPLETE' flag to run table?

### Phase 3 - Analytics
- **Flag:** Caching strategy. If risk_svc caches portfolio aggregation for 4 hours, user sees stale data during intra-day runs. TTL = 1 hour? 30 min? Policy TBD.
- **Flag:** Aggregation correctness for mixed-currency portfolios. Need to verify: EURUSD positions converted to USD base currency before SUM. Currency conversion logic placement TBD (worker or query service?).

### Phase 4 - Scaling
- **Flag:** PostgreSQL connection pool exhaustion. At 50 workers + 10 services + frontend = 200+ concurrent connections. RDS Proxy mitigates, but RDS Proxy itself can become bottleneck. Monitor connection pool saturation metrics.
- **Flag:** Query plan degradation as result table grows to 1M+ rows. Indexes on (run_id, scenario_id) may not be enough. May need partial indexes or materialized views for common aggregations.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Core architecture (worker + services)** | HIGH | MVP proves FOR UPDATE lease queue, UPSERT idempotency, snapshot immutability work at scale. Patterns are 5+ years proven in industry. |
| **Service decomposition (10 services, clean boundaries)** | HIGH | Clear separation: marketdata/orchestrator/results are compute-adjacent; portfolio/risk/regulatory/cashflow are analytics-only. No ambiguity on responsibilities. |
| **Data flow (snapshot → worker → DB → query services)** | HIGH | Linear pipeline, no cycles, no distributed consensus. Easy to reason about. One way of the data. |
| **PostgreSQL as queue** | MEDIUM-HIGH | Works fine for <10K pending tasks. Beyond that, SQS or Kafka recommended. Current plan (10-50 workers) easily handled. |
| **AWS ECS Fargate deployment** | HIGH | Standard pattern for microservices. Auto-scaling proven. Cost-effective for variable load. |
| **Scalability to 1M positions × 100 scenarios** | MEDIUM | Possible with 50+ workers + Aurora + caching, but requires query optimization + partitioning. Not yet load-tested. |
| **Cashflow generation complexity** | MEDIUM | ABS/MBS prepayment models need validation. Regulatory stress scenarios need compliance input. Some research gaps. |
| **Regulatory aggregation correctness** | MEDIUM | Basel RWA, CECL, stress capital calculations require domain expertise. Currently placeholders. Needs validation against regulatory framework documentation. |

## Gaps to Address Later

1. **Structured product pricers:** Monte Carlo engine scope, variance reduction techniques, backtesting. Defer to Phase 1, assign to quant team.
2. **Prepayment modeling:** CPR/SMM calibration, seasonal adjustments. Currently stub. Needs historical prepayment data.
3. **Regulatory scenarios:** CCAR/DFAST stress curves. Requires compliance team + regulatory documentation review.
4. **Data quality rules:** Reconciliation against Bloomberg/FactSet, outlier detection, audit trail. Defer to data_ingestion_svc phase.
5. **Caching strategy:** Invalidation policy, distributed cache coherency, metrics. Phase 3 work.
6. **Performance tuning:** Query plan analysis, index strategy, JSONB vs. columns tradeoff. Phase 4 work, after profiling.
7. **Currency handling:** Base currency conversion policy, FX delta attribution, multi-currency aggregation rules. Needs collaboration with risk team.

## Roadmap Implications Summary

**Start with:** Extend database schema (portfolio, position, cashflow_schedule, risk_metrics, regulatory_metrics, scenario tables) + AWS infrastructure (Aurora, RDS Proxy, ElastiCache). These are prerequisites.

**Then:** Build compute enhancements (new pricers, cashflow generators, risk calculators, regulatory aggregators) with golden tests in isolation. Don't scale until each piece passes golden tests.

**Parallelize:** Once compute is stable, build 7 edge services concurrently. They don't depend on each other, only on database. Can assign to different teams.

**Finally:** Frontend, caching, monitoring. These are post-MVP hardening, not critical path.

**Timeline:** 10-12 weeks from today, with standard team of 4-6 engineers (split across backend compute, backend services, data/infra, frontend, QA).

**Key risk:** Complexity of regulatory/structured product pricers not yet scoped. Recommend 2-week spike before Phase 1 commitment to validate effort estimates with quant team.

---

## Quick Links to Research Documents

- **ARCHITECTURE.md** — Component boundaries, data flow, deployment patterns, build order
- **STACK.md** — Technology decisions (FastAPI, PostgreSQL, ECS Fargate, RDS Aurora)
- **FEATURES.md** — Analytics capabilities (risk aggregation, cashflow ladders, regulatory reporting, scenario analysis)
- **PITFALLS.md** — Anti-patterns (mutable snapshots, cross-service RPC in compute, unbounded queries, no idempotency)

