# STATE: IPRS Portfolio Analytics Platform

**Project:** IPRS Institutional Portfolio Risk & Analytics System
**Created:** 2026-02-11
**Last Updated:** 2026-02-11T22:16:19Z

---

## Project Reference

**Core Value:** The risk team can run end-to-end portfolio analytics on their loan portfolio with institutional-grade reproducibility and audit trails.

**Current Status:** Phase 1 Complete - Ready for Phase 2

**Team:** Solo developer + Claude (orchestrator mode)

---

## Current Position

| Metric | Status |
|--------|--------|
| **Active Phase** | Phase 4: Regulatory Analytics & Reporting (IN PROGRESS) |
| **Current Plan** | 04-01 COMPLETE ✓ — Regulatory analytics schema extension |
| **Overall Progress** | Phase 4: 1/6 plans (Phase 1 complete, Phase 2 complete, Phase 3 5/9) |
| **Requirements Coverage** | 49/49 mapped (100%) |
| **Blockers** | None |

### Progress Bar

```
Foundation [########] Core Compute [########] Portfolio [#####...] Regulatory [#.......]
    100%                    100%                    ~56%                  ~17%
```

---

## Roadmap Summary

**Phases:** 4 (Quick depth mode)

| Phase | Goal | Requirements | ETA |
|-------|------|--------------|-----|
| **1** ✓ | Foundation & Infrastructure | PLAT-01 through PLAT-06 | COMPLETE 2026-02-11 |
| **2** | Core Compute Engines | PRICE-01 through SCEN-04 | Week 8-9 |
| **3** | Portfolio & Data Services | PORT-01 through DATA-04 | Week 12-13 |
| **4** | Regulatory Analytics & Reporting | REG-01 through RPT-04 | Week 15-16 |

**Total Estimated Duration:** 12-14 weeks (with parallelization of Phases 2 and 3 after Phase 1)

---

## Performance Metrics

### Roadmap Quality

| Metric | Target | Status |
|--------|--------|--------|
| Requirement coverage | 100% | ✓ 49/49 mapped |
| Requirement duplicates | 0 | ✓ None found |
| Success criteria per phase | 2-5 | ✓ Phase 1: 6, Phase 2: 8, Phase 3: 6, Phase 4: 9 |
| Success criteria verifiability | Observable user behavior | ✓ All criteria are user-facing |
| Dependency clarity | Clear ordering | ✓ Linear with parallelization points |
| Phase 01 P01 | 303 | 3 tasks | 7 files |
| Phase 01 P02 | 130 | 2 tasks | 3 files |
| Phase 01 P05 | 140 | 3 tasks | 3 files |
| Phase 02 P01 | 282 | 3 tasks | 5 files |
| Phase 02 P05 | 374 | 3 tasks | 6 files |
| Phase 02 P06 | 330 | 3 tasks | 2 files |
| Phase 02 P05 | 374 | 3 tasks | 6 files |
| Phase 02 P03 | 630 | 4 tasks | 4 files |
| Phase 02 P07 | 441 | 4 tasks | 6 files |
| Phase 02 P08 | 737 | 4 tasks | 9 files |
| Phase 02 P09 | 296 | 3 tasks | 4 files |
| Phase 03 P01 | 304 | 3 tasks | 4 files |
| Phase 03 P03 | 233 | 3 tasks | 4 files |
| Phase 03 P04 | 241 | 3 tasks | 4 files |
| Phase 03 P05 | 227 | 3 tasks | 4 files |
| Phase 04 P01 | 175 | 3 tasks | 3 files |

### Execution Readiness

| Activity | Status | Notes |
|----------|--------|-------|
| Requirements extracted | ✓ Complete | 49 v1 requirements identified |
| Research synthesis read | ✓ Complete | Architecture and phase ordering confirmed |
| Phases derived | ✓ Complete | 4 phases, dependency graph validated |
| Success criteria derived | ✓ Complete | 29 total criteria across 4 phases |
| Coverage validated | ✓ Complete | No orphans, no duplicates |
| Files written | ✓ Complete | ROADMAP.md, STATE.md, REQUIREMENTS.md updated |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale | Owner |
|----------|-----------|-------|
| 4-phase structure (quick depth) | 49 requirements naturally group into Foundation → Compute → Portfolio → Regulatory, with Phase 2 and 3 parallelizable | GSD Roadmapper |
| Phase 1 includes registry refactor | Compute engine needs extensible architecture before adding 6 new pricers (critical for Phase 2 success) | Research findings |
| Core compute in Phase 2, not Phase 1 | Research flag: "don't build services before compute is done". Phase 2 focuses on institutional-grade pricers + risk + scenario. | Research findings |
| Services built in Phase 3, not Phase 2 | Services are query layers only; compute produces all results. Building services before compute results are available adds rework. | Research findings |
| Regulatory in Phase 4 (not Phase 3) | Regulatory calculations depend on all compute (pricing, risk, cashflow). Phase 4 builds after Phase 2 complete. | Dependency graph |
| Auto-bootstrap registry on import | Eliminates manual registration, ensures all pricers registered automatically | Phase 1 Plan 02 |
| Function-based pricer registry | No base class required, backward-compatible with existing pricers | Phase 1 Plan 02 |
| OIDC authentication for GitHub Actions | More secure than long-lived credentials, no rotation needed, follows AWS best practices | Phase 1 Plan 05 |
| Matrix deployment strategy for ECS | Parallel deployment to all services, faster and more consistent than sequential | Phase 1 Plan 05 |
| Commit SHA image tagging | Enables rollback to specific versions, combined with "latest" for dev environments | Phase 1 Plan 05 |
| QuantLib PiecewiseLogCubicDiscount for curves | Industry standard with 20+ years development; no hand-rolled bootstrapping | Phase 2 Plan 01 |
| Multi-curve framework from start | Modern fixed income requires separate OIS discount and SOFR/LIBOR projection curves | Phase 2 Plan 01 |
| Return QuantLib objects directly | No custom wrappers; downstream pricers use QuantLib YieldTermStructure natively | Phase 2 Plan 01 |
| Factory pattern for day count/calendar | String-based factories (get_day_counter, get_calendar) provide convenient API over QuantLib | Phase 2 Plan 01 |
| Vanilla swaps only (defer swaptions/caps/floors) | Start simple per research; swaptions and caps/floors deferred to future phase | Phase 2 Plan 05 |
| Generic waterfall (not deal-specific) | Generic priority-of-payments handles simple CLO/CDO structures; complex deals require customization | Phase 2 Plan 05 |
| Historical fixing via forward curve | QuantLib requires historical fixings for floating legs; use forward curve to derive fixing rate | Phase 2 Plan 05 |
| Fallback simplified pricing for structured products | If collateral cashflows unavailable, prorate PV by subordination (graceful degradation) | Phase 2 Plan 05 |
| QuantLib Schedule for date generation | Use QuantLib's battle-tested calendar logic; skip issue date in payment schedules | Phase 2 Plan 06 |
| Fixed Hull-White parameters (a=0.03, sigma=0.12) | Market-standard USD parameters for callable/putable bonds; defer swaption vol calibration to future enhancement | Phase 2 Plan 02 |
| Tree grid points=40 for embedded options | Balance accuracy and performance for callable/putable bond pricing; industry standard for tree-based valuation | Phase 2 Plan 02 |
| Filter future cashflows at generation | pay_date > as_of_date filtering enables mid-life valuation and partial periods | Phase 2 Plan 06 |
| BlackIborCouponPricer with 20% flat volatility | Caps/floors require Black model for embedded caplet/floorlet valuation; 20% vol typical for SOFR | Phase 2 Plan 03 |
| Multi-curve framework for floating-rate pricer | Separate OIS discount and SOFR projection curves; post-2008 industry standard for basis spread modeling | Phase 2 Plan 03 |
| Infer historical fixings from flat rate | QuantLib requires index fixings for past coupon periods; use flat rate for test scenarios | Phase 2 Plan 03 |
| Historical PD lookup table from Moody's data | Use Moody's/S&P cumulative default rates instead of econometric models (Merton, CreditMetrics); lookup table sufficient for Phase 2 | Phase 2 Plan 08 |
| Euler discretization for Monte Carlo | Use Euler scheme instead of QuantLib GaussianPathGenerator due to API complexity; simpler and extensible to other models | Phase 2 Plan 08 |
| ES >= VaR coherence validation | Validate Expected Shortfall coherent risk measure property in all tests; regulatory requirement (Basel III) | Phase 2 Plan 08 |
| Scenario application for structured pricer | Added _apply_scenario function to structured product pricer to handle PARALLEL_SHIFT scenarios; matches pattern from putable_bond pricer | Phase 2 Plan 09 |
| No connection pooling for Phase 3 MVP | psycopg3 sync connection-per-request sufficient for <10K positions and <100 concurrent requests; can add psycopg_pool if load testing shows need | Phase 3 Plan 01 |
| Content-addressable portfolio snapshots | Use SHA-256 payload_hash with UNIQUE constraint for automatic snapshot deduplication | Phase 3 Plan 01 |
| PostgreSQL recursive CTEs for portfolio hierarchy | Use native recursive WITH queries instead of Python loops; DB-optimized tree traversal | Phase 3 Plan 01 |
| JSONB for flexible metadata | Store tags_json, metadata_json in JSONB to support evolving attributes without schema changes | Phase 3 Plan 01 |
| LEFT JOIN for NULL-safe reference data | Use LEFT JOIN instead of INNER JOIN to handle positions with NULL issuer_id; COALESCE to 'Unknown' bucket | Phase 3 Plan 03 |
| Window function for weight percentages | Calculate concentration percentages in SQL using SUM() OVER () instead of application layer for efficiency | Phase 3 Plan 03 |
| Multi-currency conversion at query time | FX conversion happens in SQL query (not materialized) using CASE WHEN base_ccy = 'USD' pattern | Phase 3 Plan 03 |
| DISTINCT ON for latest rating | Use PostgreSQL DISTINCT ON (agency) with ORDER BY as_of_date DESC to get latest rating per agency efficiently | Phase 3 Plan 03 |
| Weighted averages for portfolio metrics | Portfolio yield and WAM calculated as SUM(metric × PV) / SUM(PV) for proper weighting | Phase 3 Plan 03 |
| Content-addressable snapshot deduplication | SHA-256 hash of payload JSON with UNIQUE constraint on (portfolio_node_id, payload_hash) prevents duplicate snapshots | Phase 3 Plan 05 |
| Herfindahl index for concentration risk | H = Σ(wi²) industry-standard metric; H=1 max concentration, H→0 diversified; diversification ratio = 1/sqrt(H) | Phase 3 Plan 05 |
| FX conversion scoped to market snapshot | fx_spot JOIN filtered by snapshot_id from run.market_snapshot_id ensures consistent FX rates across all queries in same run | Phase 3 Plan 05 |
| S&P rating scale for migration notches | 22-point numeric scale (AAA=21 to D=0) enables migration distance calculation and direction classification | Phase 3 Plan 05 |
| Trigger-based audit trail immutability | PostgreSQL trigger prevent_audit_modification() blocks all UPDATE/DELETE on audit_trail to ensure regulatory compliance | Phase 4 Plan 01 |
| Temporal regulatory reference data | (ref_type, entity_key, effective_date DESC) index pattern enables point-in-time lookups for risk weights, PD curves, LGD tables | Phase 4 Plan 01 |
| UPSERT idempotency for regulatory metrics | UNIQUE constraint on (portfolio_node_id, metric_type, as_of_date) enables ON CONFLICT DO UPDATE for regulatory_metrics caching | Phase 4 Plan 01 |

### Architectural Constraints

| Constraint | Impact | Status |
|-----------|--------|--------|
| Shared PostgreSQL (no DB per service) | All services query same DB; eventual consistency model | Noted in Phase 1 database schema |
| Shared compute results = no service RPC in worker | Services read results from DB; worker never calls services | Enforced in Phase 2 success criteria |
| Lease-based task queue (FOR UPDATE SKIP LOCKED) | Simpler than SQS; works to 10K tasks/sec | Phase 1 infrastructure |
| UPSERT idempotency for all writes | Every write is idempotent; enables retry safety | Phase 1 and throughout |
| Content-addressable snapshots (SHA-256) | Market data and positions are immutable, versioned | MVP pattern, continued in Phase 1+ |

### Research Flags for Later

| Phase | Flag | Action |
|-------|------|--------|
| Phase 1 | Aurora write performance at 1M rows/run | Load test INSERT 10M rows in <10s; consider partitioning |
| Phase 2 | Structured product pricer complexity | May need Monte Carlo; schedule quant team spike (2 weeks) |
| Phase 2 | ABS/MBS prepayment model calibration | CPR/SMM validation against historical data; compliance input |
| Phase 2 | Regulatory stress scenarios (CCAR/DFAST) | Requires compliance team input; stress curves TBD |
| Phase 3 | Risk aggregation correctness | Cross-validate portfolio DV01 with Bloomberg PORT |
| Phase 3 | Multi-currency aggregation rules | Currency conversion placement (worker or query service) TBD |
| Phase 4 | Caching invalidation policy | TTL for intra-day runs TBD (1h vs 4h) |

### Potential Blockers

| Blocker | Severity | Mitigation |
|---------|----------|-----------|
| Quant team input on structured products | Medium | Schedule 2-week spike before Phase 1 commitment; confirm effort estimate |
| Regulatory compliance documentation (CCAR/DFAST) | Medium | Engage compliance team early Phase 2; define stress curves |
| Historical prepayment data availability | Low-Medium | Phase 2; may use proxy models (CPR lookup tables) if unavailable |
| Aurora performance at scale (1M+ positions) | Low | Phase 2 load testing; partition strategy ready if needed |

---

## Session Continuity

### What Was Done in This Session

**Phase 04 Plan 01: Regulatory Analytics Schema Extension**

1. **6 regulatory tables created** - audit_trail, regulatory_reference, model_governance, alert_config, alert_log, regulatory_metrics
2. **Immutability enforcement** - PostgreSQL trigger prevents UPDATE/DELETE on audit_trail
3. **Temporal indexes** - Point-in-time queries for regulatory reference data with effective_date DESC
4. **Verification tooling** - SQL queries and Python script with 5 automated verification checks

**Tables implemented:**
- audit_trail: Immutable log for GAAP, IFRS, CECL, Basel calculations
- regulatory_reference: Risk weights, PD curves, LGD tables with versioning
- model_governance: Model version tracking with backtesting results
- alert_config/alert_log: Threshold-based monitoring infrastructure
- regulatory_metrics: Cached regulatory calculations with UPSERT idempotency

**Commits:**
- aa134e2: feat(04-01): create regulatory analytics schema with 6 tables
- 2c91151: feat(04-01): add schema verification tools for regulatory analytics

**Duration:** 175 seconds (2 min 55 sec)

---

**Phase 4 Plan 01 COMPLETE!** Regulatory analytics schema ready for CECL, Basel, and alerting services.

### Next Session Starting Point

**Phase 4 Plan 01 COMPLETE!** Regulatory analytics schema extension ready.

**Next:** Phase 4 Plan 02 (CECL Calculations) or Phase 3 remaining plans

**Files to reference:**
- `.planning/phases/04-regulatory-analytics-reporting/04-01-SUMMARY.md` — Regulatory schema extension summary
- `sql/003_regulatory_analytics.sql` — 6 regulatory tables with indexes and triggers
- `sql/verify_003_schema.sql` — Manual verification queries
- `sql/apply_and_verify_003.py` — Automated migration and verification

**To apply schema:**
```bash
# Set DATABASE_URL environment variable
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iprs"

# Run automated application and verification
python sql/apply_and_verify_003.py

# Expected output: All 5 verification checks pass
```

**Git status:**
- Main branch active
- Phase 4: 1/6 plans complete
- Phase 4 Plan 01: REG-01 (audit trail), REG-05 (model governance), RPT-04 (alerting) schema delivered

---

## Notes for Next Session

1. **Phase 1 is the critical path.** Foundation must be solid before Phase 2. High risk if shared library, Docker, Terraform, or registry pattern is incomplete.

2. **Phase 2 and 3 can overlap after Phase 1 Week 2.** Compute engines can be built in parallel with portfolio services once shared libs are stable.

3. **Structured products may need specialist input.** Flag this early in Phase 2. If pricers become complex, may need to extend Phase 2 timeline or bring in quant team.

4. **Database schema must support all analytics.** Phase 1 extends schema for: portfolio_node, position, cashflow_schedule, risk_metrics, regulatory_metrics, scenario. Don't defer schema work.

5. **Regulatory Phase 4 depends on all prior compute.** CECL, Basel, GAAP calculations only meaningful once pricers, risk calculators, and data are production-ready in Phases 2-3.

6. **Export quality is audit-critical.** Phase 4 reporting must be verifiable and timestamped. Don't defer audit trail work.

---

*STATE.md created 2026-02-11 during roadmap phase*

---

## Phase 03 Plan 04 Execution Complete

**Plan:** Data Ingestion Service
**Completed:** 2026-02-11T22:13:40Z
**Duration:** 241 seconds (4 min 1 sec)

### Decisions Made
- FX spots as first-class endpoints tied to snapshot_id for multi-currency aggregation
- UPSERT idempotency with content-addressable hashing for market feed deduplication
- Foreign key validation before batch insert to fail fast on invalid references

### Files Created
- services/data_ingestion_svc/app/routes/market_feeds.py (433 lines)
- services/data_ingestion_svc/app/routes/loan_servicing.py (247 lines)
- services/data_ingestion_svc/app/routes/lineage.py (313 lines)
- services/data_ingestion_svc/app/models.py (FX, lineage, batch models)

### Commits
- 4eff10f: market data feed ingestion with FX spots and lineage
- a047922: loan servicing batch ingestion with validation
- ac539fb: data lineage query endpoints

---

## Phase 03 Plan 05 Execution Complete

**Plan:** Portfolio Snapshots & Concentration Monitoring
**Completed:** 2026-02-12T02:43:02Z
**Duration:** 227 seconds (3 min 47 sec)

### Decisions Made
- Content-addressable snapshot deduplication with SHA-256 payload hash
- Recursive CTE for hierarchical portfolio snapshot aggregation
- Herfindahl index for concentration measurement (H = Σ(wi²))
- S&P rating scale for migration notch calculation (AAA=21 to D=0)
- FX conversion at query time with snapshot-scoped fx_spot JOIN

### Files Created
- services/portfolio_svc/app/models.py (270 lines: SnapshotCreate, SnapshotOut, ConcentrationReport, RatingMigrationReport)
- services/portfolio_svc/app/routes/snapshots.py (374 lines: snapshot CRUD, comparison, time-series)

### Files Modified
- services/common/portfolio_queries.py (added get_fx_snapshot_for_run helper)
- services/portfolio_svc/app/routes/aggregation.py (added concentration and rating-migration endpoints)

### Commits
- fb16f77: snapshot creation with deduplication
- 4c07052: concentration monitoring and FX conversion integration

### Requirements Completed
- PORT-07: Multi-currency aggregation with snapshot-scoped FX conversion
- PORT-08: Portfolio snapshots with content-addressable deduplication
- RISK-06: Concentration monitoring (issuer, sector, geography, single-name) with Herfindahl index and rating migration tracking

**Phase 3 Status:** 5/9 plans complete (PORT-01 through PORT-08, DATA-01 through DATA-04, RISK-06 all delivered)

---

## Phase 04 Plan 01 Execution Complete

**Plan:** Regulatory Analytics Schema Extension
**Completed:** 2026-02-12T02:57:54Z
**Duration:** 175 seconds (2 min 55 sec)

### Decisions Made
- Trigger-based immutability: prevent_audit_modification() blocks UPDATE/DELETE on audit_trail
- Temporal regulatory reference data: (ref_type, entity_key, effective_date DESC) index pattern
- UPSERT idempotency: UNIQUE constraint on (portfolio_node_id, metric_type, as_of_date) for regulatory_metrics
- CHECK constraints for enum validation at database layer

### Files Created
- sql/003_regulatory_analytics.sql (161 lines: 6 tables, 10 indexes, 1 trigger)
- sql/verify_003_schema.sql (220 lines: manual verification queries)
- sql/apply_and_verify_003.py (387 lines: automated verification)

### Commits
- aa134e2: feat(04-01): create regulatory analytics schema with 6 tables
- 2c91151: feat(04-01): add schema verification tools for regulatory analytics

### Requirements Completed
- REG-01 (partial): Audit trail schema ready for CECL/Basel calculations
- REG-05 (partial): Model governance schema ready for version tracking
- RPT-04 (partial): Alert config and log schema ready for threshold monitoring

**Phase 4 Status:** 1/6 plans complete (regulatory schema foundation delivered)
