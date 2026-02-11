# IPRS - Institutional Portfolio Risk & Analytics System

## What This Is

A distributed portfolio analytics platform for an internal risk team managing a loan-heavy portfolio (thousands of positions). Expands the existing Risk MVP from basic instrument valuation into a full-spectrum analytics engine covering pricing, cash flow modeling, risk analytics (market/credit/liquidity), performance attribution, scenario simulation, and regulatory support. Deployed on AWS with microservices architecture, Terraform infrastructure, and CI/CD pipelines.

## Core Value

The risk team can run end-to-end portfolio analytics - from market data ingestion through pricing, risk calculation, and drill-down reporting - on their loan portfolio with institutional-grade reproducibility and audit trails.

## Requirements

### Validated

<!-- Existing capabilities confirmed from codebase map -->

- ✓ Market data snapshot ingestion (curves, FX spots) with quality checks — existing (marketdata_svc)
- ✓ Run creation with portfolio scope, measures, and scenarios — existing (run_orchestrator)
- ✓ Task fanout by product_type and hash_bucket with lease-based queue — existing (run_orchestrator + worker)
- ✓ FX Forward pricing (PV, DV01, FX_DELTA) — existing (compute/pricers/fx_fwd.py)
- ✓ Amortizing loan pricing (PV, DV01, ACCRUED_INTEREST) — existing (compute/pricers/loan.py)
- ✓ Fixed bond pricing (PV, DV01) — existing (compute/pricers/bond.py)
- ✓ Zero curve interpolation and discount factor calculation — existing (compute/quantlib/curve.py)
- ✓ Scenario application (BASE, RATES_PARALLEL_1BP, SPREAD_25BP, FX_SPOT_1PCT) — existing (compute/quantlib/scenarios.py)
- ✓ Results aggregation with drill-down by portfolio_node_id and product_type — existing (results_api)
- ✓ Immutable snapshot pattern with SHA-256 content addressing — existing (all services)
- ✓ UPSERT idempotency for all writes — existing (all services)
- ✓ Golden test framework for pricers — existing (compute/tests/)
- ✓ React UI for run submission, results polling, and cube drill-down — existing (frontend)
- ✓ Instrument versioning schema with governance fields — existing (sql/001_mvp_core.sql)
- ✓ Run break tracking schema — existing (sql/001_mvp_core.sql)

### Active

<!-- New capabilities to build in this milestone -->

**A. Platform Foundation**
- [ ] Shared library with Pydantic models, events, auth middleware, config management
- [ ] Common service utilities (service factory, health checks, pagination, error handling)
- [ ] Docker containerization for all services and workers
- [ ] Terraform AWS infrastructure (VPC, ECS Fargate, RDS Aurora, API Gateway, SQS, ECR)
- [ ] GitHub Actions CI/CD (lint, test, build, deploy)
- [ ] API Gateway with path-based routing to all services

**B. Instrument & Reference Data**
- [ ] Instrument master service with CRUD for loans, bonds, ABS/MBS, derivatives
- [ ] Reference data management (issuers, sectors, ratings, geography)
- [ ] Trade lifecycle support (booking, amendment, termination)
- [ ] Instrument version approval workflows

**C. Portfolio Management**
- [ ] Portfolio hierarchy and node management
- [ ] Position tracking and holdings aggregation (by issuer, sector, rating, geography)
- [ ] Portfolio segmentation and tagging
- [ ] Historical snapshots and time-series tracking
- [ ] Multi-currency support
- [ ] Portfolio metrics: Market value, Book value, Accrued interest, Unrealized/Realized P&L, Portfolio yield, WAM, WAL

**D. Pricing & Valuation (institutional-grade replacements)**
- [ ] Abstract base pricer with registry pattern (replace if/elif dispatch)
- [ ] Floating-rate instrument pricer
- [ ] Callable/putable bond pricers
- [ ] ABS/MBS pricer
- [ ] Structured product pricer
- [ ] Derivatives hedge pricer
- [ ] Full curve construction (multi-curve, bootstrap)
- [ ] Multiple interpolation methods (linear, log-linear, cubic spline)
- [ ] Day count conventions (ACT/360, ACT/365, 30/360)
- [ ] Business day calendar
- [ ] Measures: Clean/Dirty price, YTM, YTC/YTP, OAS, Z-spread, DM, Par spread

**E. Cash Flow & Amortization**
- [ ] Payment schedule generation
- [ ] Amortization schedule modeling (level pay, bullet, custom)
- [ ] Prepayment modeling (CPR, PSA)
- [ ] Default and recovery modeling (LGD, EAD)
- [ ] Adjustable rate reset logic
- [ ] Scenario cash flow projection
- [ ] Waterfall modeling for structured products

**F. Risk Analytics**
- [ ] Market risk: Duration (Macaulay/Modified/Effective), DV01/PV01, Convexity, Key rate duration, Spread duration
- [ ] VaR (Historical, Parametric, Monte Carlo) and Expected Shortfall
- [ ] Credit risk: PD modeling, Expected/Unexpected loss, Rating migration, Concentration monitoring, RAROC
- [ ] Liquidity risk: Bid/ask spread analytics, Time-to-liquidate, Liquidity coverage ratios

**G. Scenario & Forecasting**
- [ ] Scenario definition and management service
- [ ] Stress testing configuration (rate shocks, spread shocks)
- [ ] Monte Carlo simulation engine (interest rate paths, macro factors)
- [ ] What-if analysis and portfolio rebalancing simulation

**H. Performance & Attribution**
- [ ] Benchmark comparison engine
- [ ] Total return, Income return, Price return decomposition
- [ ] Attribution by duration, spread, security selection, sector allocation
- [ ] Sharpe ratio, Information ratio, Tracking error

**I. Regulatory & Accounting**
- [ ] GAAP/IFRS valuation support framework
- [ ] Expected credit loss modeling (CECL-style)
- [ ] Basel III capital analytics and RWA calculation
- [ ] Audit trail and calculation explainability
- [ ] Model governance (versioning, backtesting, calibration tracking)

**J. Data Integration**
- [ ] Market data feed ingestion (yield curves, credit spreads, ratings)
- [ ] Loan servicing data ingestion
- [ ] Historical data versioning
- [ ] Data lineage tracking

**K. Reporting & Visualization**
- [ ] Expanded frontend pages for each analytics domain
- [ ] Drill-down analytics beyond current cube view
- [ ] Export capabilities for downstream systems
- [ ] Alerting and threshold monitoring

### Out of Scope

- Real-time streaming analytics — batch/intraday sufficient for thousands of positions
- Multi-tenant SaaS features — internal team only, no tenant isolation needed
- Mobile application — web-only
- Pricing vendor API integration (Bloomberg, Refinitiv) — internal models only for v1
- AI/ML models (prepayment prediction, default prediction, anomaly detection) — defer to v2
- Full regulatory reporting generation (call reports, etc.) — framework only for v1

## Context

**Existing codebase:** Working MVP with 3 FastAPI services, distributed worker, 3 pricers, PostgreSQL with JSONB, React frontend. Patterns are solid (immutable snapshots, lease-based queue, content-addressed hashing, UPSERT idempotency). Pricers are simplified prototypes that need institutional-grade replacements.

**User profile:** Internal risk team at an investment firm (lighter regulatory requirements than a bank). Portfolio is loan-heavy (70%+ loans) with bonds and derivatives as hedges. Thousands of positions - manageable scale.

**Technical environment:** Windows 11 development, targeting AWS deployment. Python 3.11+, PostgreSQL, React 18.

**Codebase map:** Full analysis available in `.planning/codebase/` (7 documents, 1,469 lines).

## Constraints

- **Tech stack**: Python 3.11+ / FastAPI / PostgreSQL / React 18 — preserve existing investment
- **Infrastructure**: AWS (ECS Fargate, RDS Aurora, API Gateway) with Terraform IaC
- **CI/CD**: GitHub Actions
- **Database**: Shared PostgreSQL with schema-per-service logical separation (can split later)
- **Compatibility**: Existing MVP services must remain backward-compatible during expansion
- **Asset priority**: Loan instruments are primary; bonds, ABS/MBS, derivatives are secondary
- **Scale**: Thousands of positions, batch + intraday recalculation

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Terraform over CDK/CloudFormation | Industry standard in finance, declarative, cloud-agnostic | — Pending |
| Shared PostgreSQL over DB-per-service | Simpler ops for internal team, easier cross-domain joins, can split later | — Pending |
| GitHub Actions over CodePipeline | Already on GitHub, native integration, larger ecosystem | — Pending |
| Replace MVP pricers rather than extend | Current pricers are prototypes, institutional-grade models needed | — Pending |
| Registry pattern for pricers | Replace if/elif chain with pluggable registry for extensibility | — Pending |
| 10 microservices (3 existing + 7 new) | Clear domain boundaries, independently deployable, team can own domains | — Pending |
| Scaffold-first approach | Get full structure in place before deep feature implementation | — Pending |

---
*Last updated: 2026-02-11 after initialization*
