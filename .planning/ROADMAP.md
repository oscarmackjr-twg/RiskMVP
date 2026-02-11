---
# ROADMAP: IPRS Institutional Portfolio Analytics Platform

**Version:** 1.0
**Created:** 2026-02-11
**Depth:** Quick (4 phases)
**Status:** Phase 1 Complete, Phase 2 Complete

---

## Overview

Expanding the Risk MVP from a working prototype into an institutional-grade portfolio analytics platform. The roadmap structures 49 v1 requirements into 4 coherent delivery phases that progressively add capability: foundation infrastructure → core compute engines → portfolio & data services → regulatory analytics & reporting. Each phase delivers observable value and unblocks the next.

---

## Phase Structure

| Phase | Goal | Requirements Mapped | Success Criteria |
|-------|------|-------------------|------------------|
| **1 - Foundation & Infrastructure** ✓ | Platform skeleton ready; compute engine refactored with registry pattern; database schema extended for full analytics pipeline | PLAT-01, PLAT-02, PLAT-03, PLAT-04, PLAT-05, PLAT-06 | 6/6 verified |
| **2 - Core Compute Engines** ✓ | Institutional-grade pricers, cashflow generation, risk analytics, and scenario execution; worker processes full pipeline end-to-end | PRICE-01 through PRICE-09, CF-01 through CF-06, RISK-01 through RISK-07, SCEN-01 through SCEN-04 | 8/8 verified |
| **3 - Portfolio & Data Services** | Portfolio hierarchy, position management, reference data; data ingestion pipelines; independent query services for aggregation | PORT-01 through PORT-08, DATA-01 through DATA-04 | 6 success criteria |
| **4 - Regulatory Analytics & Reporting** | Regulatory frameworks (GAAP/IFRS, Basel, CECL), audit trails, model governance; frontend expansion with domain-specific views and exports | REG-01 through REG-05, RPT-01 through RPT-04 | 5 success criteria |

---

## Phase 1: Foundation & Infrastructure

**Goal:** Platform infrastructure and compute engine foundation ready for institutional-scale analytics.

**Why First:** All downstream work depends on shared libraries, Docker, Terraform, database schema, and registry-pattern refactoring. Must be in place before scaling compute engines.

**Plans:** 5 plans in 4 waves

Plans:
- [x] 01-01-PLAN.md — Refactor services to use shared library + service factory (PLAT-01, PLAT-02) ✓ 2026-02-11
- [x] 01-02-PLAN.md — Refactor worker to use registry pattern (PLAT-06) ✓ 2026-02-11
- [x] 01-03-PLAN.md — Docker containerization for all services + worker (PLAT-03) ✓ 2026-02-11
- [x] 01-04-PLAN.md — Terraform AWS infrastructure (PLAT-04) ✓ 2026-02-11
- [x] 01-05-PLAN.md — GitHub Actions CI/CD pipeline (PLAT-05) ✓ 2026-02-11

### Requirements Mapped

- **PLAT-01**: Shared Pydantic models, events, auth middleware, and config across all services
- **PLAT-02**: Common service factory with health checks, pagination, and error handling
- **PLAT-03**: Docker containerization for all services and workers
- **PLAT-04**: Terraform AWS infrastructure (VPC, ECS Fargate, RDS Aurora, API Gateway, SQS, ECR)
- **PLAT-05**: GitHub Actions CI/CD pipelines (lint, test, build, deploy)
- **PLAT-06**: Pricer registry pattern replacing if/elif dispatch

### Dependencies

- None. This is the foundation phase.

### Success Criteria

1. **Shared library published and imported by all services** - All services import `shared.models`, `shared.events`, `shared.middleware`, `shared.config` without duplicate code. Auth middleware applies to all endpoints. Config is externalized to environment.

2. **Service factory pattern applied across all services** - All services inherit from `ServiceBase` with built-in health checks, pagination, and error handling. Health checks are verifiable at `GET /health`. Error responses are consistent (400/404/500 with standard format).

3. **All services and workers containerized** - Each service and worker builds to Docker image. Docker Compose runs all 4 services + 1 worker locally without manual setup. Images push to ECR.

4. **Terraform deploys complete AWS stack** - `terraform apply` creates VPC, ECS cluster, Fargate task definitions, Aurora PostgreSQL cluster, RDS Proxy, API Gateway with path-based routing to all services, and auto-scaling policies. Developers can destroy and recreate infrastructure in <5 minutes.

5. **CI/CD pipeline runs on every commit** - GitHub Actions workflow runs lint, pytest, builds Docker images, tags with commit hash, and deploys to AWS. Failures block merge to main.

6. **Pricer registry pattern working with 3 pricers** - Existing FX_FWD, LOAN, BOND pricers register in `compute.pricers.registry.PricerRegistry`. Worker claims task, looks up pricer by product_type, calls `pricer.price()` without if/elif chains. New pricers added via simple `@register_pricer` decorator.

### Acceptance Criteria

- All 6 requirements delivered
- Local development environment reproducible on Windows + macOS + Linux via Docker Compose
- Shared library > 80% type coverage (mypy strict mode passes)
- All services respond to `/health` with `{"status": "healthy"}` within 1 second
- Registry pattern supports adding new pricer without modifying worker.py
- First deploy to AWS succeeds with all services + worker running and responding

---

## Phase 2: Core Compute Engines

**Goal:** Institutional-grade valuation, cashflow modeling, risk analytics, and scenario execution. Worker processes full pipeline for all instruments.

**Why Here:** Phase 1 infrastructure is prerequisite. This phase builds the analytics engines that drive all downstream value. Research flags this as critical: "don't build services before compute is done."

**Plans:** 9 plans in 3 waves

Plans:
- [x] 02-01-PLAN.md — QuantLib foundation (curve construction, day count, calendar) ✓ 2026-02-11
- [x] 02-02-PLAN.md — Callable & putable bond pricers (TDD) ✓ 2026-02-11
- [x] 02-03-PLAN.md — Floating-rate instrument pricer (TDD) ✓ 2026-02-11
- [x] 02-04-PLAN.md — ABS/MBS pricer with prepayment modeling ✓ 2026-02-11
- [x] 02-05-PLAN.md — Derivatives & structured product pricers ✓ 2026-02-11
- [x] 02-06-PLAN.md — Cashflow modeling engine ✓ 2026-02-11
- [x] 02-07-PLAN.md — Market risk analytics (duration, DV01, convexity, key rate) ✓ 2026-02-11
- [x] 02-08-PLAN.md — Credit/liquidity risk, VaR/ES, Monte Carlo, scenario service ✓ 2026-02-11
- [x] 02-09-PLAN.md — Gap closure: Add missing golden tests (putable bond, derivatives, structured) ✓ 2026-02-11

### Requirements Mapped

**Pricing & Valuation (9 requirements):**
- **PRICE-01**: Floating-rate instrument pricer (Plan 02-03)
- **PRICE-02**: Callable bond pricer with OAS (Plan 02-02)
- **PRICE-03**: Putable bond pricer (Plan 02-02)
- **PRICE-04**: ABS/MBS pricer with prepayment models (Plan 02-04)
- **PRICE-05**: Structured product pricer (Plan 02-05)
- **PRICE-06**: Derivatives hedge pricer (Plan 02-05)
- **PRICE-07**: Full curve construction (multi-curve, bootstrap, interpolation methods) (Plan 02-01)
- **PRICE-08**: Day count conventions (ACT/360, ACT/365, 30/360) and business day calendar (Plan 02-01)
- **PRICE-09**: Measures: Clean/Dirty price, YTM, YTC/YTP, OAS, Z-spread, DM, Par spread (Plans 02-02, 02-03)

**Cash Flow Modeling (6 requirements):**
- **CF-01**: Payment schedule generation (level pay, bullet, custom amortization) (Plan 02-06)
- **CF-02**: Prepayment modeling (CPR, PSA speeds) (Plan 02-04)
- **CF-03**: Default and recovery modeling (LGD, EAD) (Plan 02-04)
- **CF-04**: Adjustable rate reset logic (Plan 02-03)
- **CF-05**: Scenario cash flow projection (Plan 02-08)
- **CF-06**: Waterfall modeling for structured products (Plan 02-05)

**Risk Analytics (7 requirements):**
- **RISK-01**: Duration calculations (Macaulay, Modified, Effective) (Plan 02-07)
- **RISK-02**: DV01/PV01 and Convexity (Plan 02-07)
- **RISK-03**: Key rate duration and Spread duration (Plan 02-07)
- **RISK-04**: VaR (Historical, Parametric) and Expected Shortfall (Plan 02-08)
- **RISK-05**: Credit risk: PD modeling, Expected loss, Unexpected loss (Plan 02-08)
- **RISK-06**: Rating migration tracking and Concentration monitoring (Deferred to Phase 3)
- **RISK-07**: Liquidity risk: Bid/ask spread analytics, Time-to-liquidate, LCR (Plan 02-08)

**Scenario & Forecasting (4 requirements):**
- **SCEN-01**: Scenario definition and management service (CRUD, scenario sets) (Plan 02-08)
- **SCEN-02**: Stress testing configuration (rate shocks, spread shocks, FX shocks) (Plan 02-08)
- **SCEN-03**: Monte Carlo simulation engine (interest rate paths, macro factors) (Plan 02-08)
- **SCEN-04**: What-if analysis and portfolio rebalancing simulation (Plan 02-08)

### Dependencies

- Phase 1: Shared library, registry pattern, Docker, Terraform, database schema extensions

### Success Criteria

1. **All 6 new pricers produce institutional-grade valuations** - FLOATING_RATE, CALLABLE_BOND, PUTABLE_BOND, ABS_MBS, STRUCTURED, DERIVATIVES pricers exist and pass golden tests comparing output to Bloomberg terminal references or academic formulas. Each pricer computes PV, YTM, and measure-specific metrics (e.g., OAS for callable bonds).

2. **Worker computes full cashflow schedule for each position** - For a loan with CPR prepayment model and default assumptions, worker generates monthly payment schedule including principal, interest, prepayments, defaults. Schedule is queryable for waterfall analysis and maturity ladders.

3. **Risk metrics computed for each position in each scenario** - Every position has DV01, duration (Macaulay, Modified, Effective), spread duration, key rate durations. Credit risk metrics (PD, expected loss) computed from ratings and recovery assumptions. Liquidity metrics (bid/ask spread, time-to-liquidate) computed from position size and market data. Metrics populated in database for all scenarios (BASE, rates ±100bp, spreads ±25bp, FX ±1%).

4. **Scenario execution end-to-end without manual intervention** - User submits run with market snapshot, portfolio, and scenario set. Worker claims tasks, applies scenarios (curve shifts, FX shocks), re-prices all positions, regenerates cashflows, recalculates risk metrics, and writes all results to database. No human intervention needed. All results queryable within 5 minutes for 1000-position portfolio on 10 workers.

5. **Monte Carlo engine generates market paths** - Scenario engine generates 1000+ interest rate paths using Vasicek or similar single-factor model, with correlations to macro factors (inflation, unemployment). Paths stored in database and reusable across runs.

6. **VaR and Expected Shortfall calculated across scenarios** - Portfolio VaR (95%, 99%) computed from historical scenario returns or Monte Carlo paths. Expected Shortfall computed as mean of worst-case scenarios. Results are verifiable against standard financial references.

7. **Stress test scenarios configured and executable** - Predefined stress scenarios (CCAR, DFAST, custom) apply simultaneous shocks to curves, spreads, FX, ratings. User can modify shock parameters and re-run. Results queryable for stress impact analysis.

8. **Golden tests validate all new pricers** - Each pricer has ≥3 golden tests (bond with embedded options, floating-rate loan with prepayment, structured product with waterfall). Tests compare to reference valuations and reference implementations. All tests pass.

### Acceptance Criteria

- All 26 requirements delivered (25 in Phase 2, 1 deferred to Phase 3: RISK-06)
- 6 new pricers implemented and integrated into registry
- Golden tests for each pricer pass (>80% code coverage for pricing module)
- Worker processes 1000 positions × 10 scenarios in <10 minutes on single worker
- Database contains full results (valuation, cashflow, risk) for all positions and scenarios
- No manual rework needed to integrate results into analytics services

---

## Phase 3: Portfolio & Data Services

**Goal:** Portfolio hierarchy, position management, reference data, and data ingestion pipelines. Independent query services for portfolio aggregation and analytics queries.

**Why Here:** Phase 2 delivers compute results. Phase 3 builds portfolio domain and data ingestion, enabling Phase 4 analytics and reporting.

### Requirements Mapped

**Portfolio Management (8 requirements):**
- **PORT-01**: Instrument master service with CRUD for loans, bonds, ABS/MBS, derivatives
- **PORT-02**: Reference data management (issuers, sectors, ratings, geography)
- **PORT-03**: Portfolio hierarchy and node management
- **PORT-04**: Position tracking and holdings aggregation (by issuer, sector, rating, geography)
- **PORT-05**: Portfolio segmentation and tagging
- **PORT-06**: Historical snapshots and time-series tracking
- **PORT-07**: Multi-currency support with FX conversion to base currency
- **PORT-08**: Portfolio metrics: Market value, Book value, Accrued interest, Unrealized/Realized P&L, Portfolio yield, WAM, WAL

**Data Integration (4 requirements):**
- **DATA-01**: Market data feed ingestion (yield curves, credit spreads, ratings feeds)
- **DATA-02**: Loan servicing data ingestion
- **DATA-03**: Historical data versioning
- **DATA-04**: Data lineage tracking

### Dependencies

- Phase 1: Shared library, service factory, database schema for portfolio and reference data
- Phase 2: Worker produces results; data ingestion consumes market data and positions

### Success Criteria

1. **Portfolio hierarchy fully modeled and queryable** - User creates fund → desk → book → position hierarchy. Arbitrary levels supported. Aggregations compute correctly at each level (sum market values, weighted durations, concentration metrics). Queries return portfolio node trees with metrics in <1 second for 10K-position portfolio.

2. **Position data ingested and linked to instruments** - Portfolio positions load from servicing files (CSV/JSON) with validation. Each position links to instrument master. Duplicate positions aggregate (sum quantities). Historical snapshots track position changes over time with audit trail.

3. **Instrument master fully populated** - Loans, bonds, ABS/MBS, derivatives can be created via API or bulk import. Each instrument has complete metadata (issuer, coupon, maturity, embedded options, prepayment assumptions, rating, etc.). Versions track instrument changes with approval workflows.

4. **Reference data available for all positions** - All positions have issuer, sector, geography, rating (with migration history), currency. Data sourced from market data feeds (Bloomberg, CUSIP databases) or manual input. Lookups are real-time (no batch lag).

5. **Multi-currency aggregation working** - Portfolio contains positions in USD, EUR, GBP, JPY. All metrics convert to base currency (USD) using latest FX spots. Aggregations sum across currencies correctly. FX exposure attributed per currency pair.

6. **Data ingestion pipeline produces audit trails** - When servicing data ingests 5000 positions or market data loads new curves, system logs: timestamp, source file, record count, validation errors, user, approval status. Lineage is queryable: "which feeds contributed to this position's valuation?"

### Acceptance Criteria

- All 12 requirements delivered
- Portfolio hierarchy CRUD endpoints functional with ≥95% uptime on staging
- Position ingestion supports ≥10K positions with validation and <5 minute load time
- Instrument master searchable by CUSIP, ticker, issuer, rating
- Currency aggregation validated for mixed-currency portfolios (>95% accuracy vs. manual calculation)
- Data lineage queryable for all ingested records

---

## Phase 4: Regulatory Analytics & Reporting

**Goal:** Regulatory frameworks (GAAP, IFRS, Basel, CECL), audit trails, model governance, and expanded frontend. Enables complete analytics and drill-down reporting.

**Why Last:** Phase 3 delivers portfolio and data services. This phase builds on top with regulatory aggregation and reporting. Completes the analytics stack.

### Requirements Mapped

**Regulatory & Accounting (5 requirements):**
- **REG-01**: GAAP/IFRS valuation support framework
- **REG-02**: Expected credit loss modeling (CECL-style)
- **REG-03**: Basel III capital analytics and RWA calculation
- **REG-04**: Audit trail and calculation explainability
- **REG-05**: Model governance (versioning, backtesting, calibration tracking)

**Reporting & Visualization (4 requirements):**
- **RPT-01**: Frontend pages for each analytics domain (instruments, portfolio, risk, cashflows, scenarios, regulatory)
- **RPT-02**: Drill-down analytics beyond current cube view (by issuer, sector, rating, geography)
- **RPT-03**: Export to CSV/Excel for downstream systems
- **RPT-04**: Alerting and threshold monitoring

### Dependencies

- Phase 1: Shared library, service factory, database
- Phase 2: Compute engines producing results
- Phase 3: Portfolio, reference data, data ingestion

### Success Criteria

1. **GAAP/IFRS valuation framework operational** - Portfolio can be valued under GAAP HTM (historical cost + impairment) or AFS (fair value), and IFRS (amortized cost + ECL). Valuation method selectable per position. Results show marked-to-market PV, accrued interest, and impairment allowances.

2. **CECL allowance calculated for loan portfolio** - System applies probability-of-default (PD) and loss-given-default (LGD) curves to loan population. Expected credit loss (ECL) allowance computed for each loan cohort (origination year, rating, geography). Portfolio allowance aggregates cohort allowances. Results validate against Basel standardized approach as lower bound.

3. **Basel III capital calculations working** - RWA calculated for all positions (standardized approach for loans/bonds, market risk capital charge for derivatives). Capital ratio (Tier 1 / RWA) computed at portfolio level. Stress tests show capital impact of adverse scenarios.

4. **Audit trail complete and immutable** - Every calculation (pricing, risk, regulatory) has immutable audit log: input data, model version, calculation timestamp, user, results. Logs are queryable and exportable. Explainability available: "why was this bond priced at $102?"

5. **Model governance framework in place** - Each pricer/risk calculator/regulatory model has version number, change log, backtesting results, calibration date. Models can be marked as "approved for production", "testing", or "deprecated". Calculation explainability linked to model version.

6. **Frontend pages cover all analytics domains** - React pages built for: instruments (search, view, amend), portfolio (hierarchy drill-down, position-level metrics), risk (risk dashboard with heatmaps, scenario analysis), cashflows (maturity ladders, payment schedules), scenarios (scenario CRUD, comparison), regulatory (capital ratios, stress results, CECL allowance). Navigation is intuitive; no more than 2 clicks to reach any metric.

7. **Drill-down analytics functional** - User views portfolio risk dashboard, clicks on a sector, sees all positions in that sector. Clicks on a position, sees: instrument details, valuation, cashflow schedule, risk sensitivity, regulatory capital allocation. All views are sub-second.

8. **CSV/Excel export working** - User can export: portfolio snapshot (positions + metrics), risk report (position-level Greeks + portfolio aggregates), regulatory report (capital, ECL allowance), scenario comparison (multiple scenarios side-by-side). Exports are formatted for downstream systems and audit.

9. **Alerting configured and tested** - Alerts trigger when: portfolio duration exceeds threshold, concentration in single issuer exceeds limit, credit metric deteriorates (rating downgrade, PD increase), liquidity ratio falls below threshold. Alerts are email/Slack, queryable in UI, with alert history.

### Acceptance Criteria

- All 9 requirements delivered
- Frontend pages render and respond in <1 second for 10K-position portfolio
- Regulatory calculations validated against external references (CCAR templates, Basel documentation)
- Audit trail complete for all calculations (no gaps in lineage)
- Model governance framework enforced (all pricers/models versioned and approved before production use)
- Export quality meets audit requirements (complete, verifiable, timestamped)

---

## Success Metrics

**Overall project success when:**

- All 49 v1 requirements delivered and mapped to phases (100% coverage)
- Phase 1 complete: Platform foundation and compute engine ready
- Phase 2 complete: Institutional-grade pricers and risk analytics operational
- Phase 3 complete: Portfolio management and data ingestion pipelines functional
- Phase 4 complete: Regulatory frameworks and reporting operational
- End-to-end workflow tested: Market data ingestion → Portfolio upload → Run execution → Results reporting (all in <15 min for 5000 positions)
- User acceptance testing passed by risk team
- Deployed to AWS with auto-scaling and monitoring in place

---

## Coverage Validation

**Requirement Mapping Summary:**

| Category | Total | Mapped to Phase |
|----------|-------|-----------------|
| Platform (PLAT) | 6 | Phase 1 |
| Pricing (PRICE) | 9 | Phase 2 |
| Portfolio (PORT) | 8 | Phase 3 |
| Cashflow (CF) | 6 | Phase 2 |
| Risk (RISK) | 7 | Phase 2 (6), Phase 3 (1) |
| Scenario (SCEN) | 4 | Phase 2 |
| Regulatory (REG) | 5 | Phase 4 |
| Data (DATA) | 4 | Phase 3 |
| Reporting (RPT) | 4 | Phase 4 |
| **TOTAL** | **49** | **49 / 49** |

**Coverage:** 49/49 requirements mapped. No orphans. No duplicates.

---

## Phase Dependencies

```
Phase 1: Foundation & Infrastructure
  │
  ├─→ Phase 2: Core Compute Engines
  │     └─→ Phase 3: Portfolio & Data Services
  │           └─→ Phase 4: Regulatory Analytics & Reporting
  │
  └─→ Parallelization: Phases 2 and 3 can overlap (compute and portfolio)
      after Phase 1 foundation is complete (Week 3-4).
```

---

## Next Steps

1. **User Review:** Approve or request revisions to phase structure, success criteria, or requirement assignments
2. **Phase 2 Execution:** Begin with `/gsd:execute-phase 2` after roadmap approval
3. **Estimate Effort:** Phase 1 ~3-4 weeks, Phase 2 ~4-5 weeks, Phase 3 ~3-4 weeks, Phase 4 ~3-4 weeks (with parallelization, total ~12-14 weeks)

---

*Roadmap Version 1.0 created 2026-02-11 by GSD Roadmapper*
*Phase 2 plans added 2026-02-11 by GSD Planner*
