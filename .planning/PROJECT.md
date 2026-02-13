# IPRS - Institutional Portfolio Risk & Analytics System

## What This Is

A distributed portfolio analytics platform for an internal risk team managing a loan-heavy portfolio (thousands of positions). Provides end-to-end analytics from market data ingestion through pricing, cash flow modeling, risk calculation (market/credit/liquidity), regulatory compliance (CECL/Basel/GAAP-IFRS), and drill-down reporting with export. Deployed on AWS with microservices architecture.

## Core Value

The risk team can run end-to-end portfolio analytics - from market data ingestion through pricing, risk calculation, and drill-down reporting - on their loan portfolio with institutional-grade reproducibility and audit trails.

## Requirements

### Validated

- ✓ Shared library with Pydantic models, service factory, health checks, pagination -- v1.0
- ✓ Docker containerization and Terraform AWS infrastructure -- v1.0
- ✓ GitHub Actions CI/CD pipelines -- v1.0
- ✓ Pricer registry pattern (auto-bootstrap, function-based) -- v1.0
- ✓ 8 institutional-grade pricers (FX Fwd, Bond, Loan, Floating-Rate, Callable, Putable, ABS/MBS, Structured) -- v1.0
- ✓ Full curve construction (multi-curve, QuantLib bootstrap) -- v1.0
- ✓ Day count conventions and business day calendars -- v1.0
- ✓ Cashflow generation (amortization, prepayment, waterfall) -- v1.0
- ✓ Risk analytics: Duration, DV01, Convexity, Key Rate, VaR, ES, Credit Risk, Liquidity Risk -- v1.0
- ✓ Scenario management and Monte Carlo simulation -- v1.0
- ✓ Portfolio hierarchy, position tracking, concentration monitoring -- v1.0
- ✓ Multi-currency FX conversion with content-addressable snapshots -- v1.0
- ✓ Data ingestion (market feeds, loan servicing, lineage) -- v1.0
- ✓ CECL allowance (ASC 326), Basel III RWA, GAAP/IFRS valuation -- v1.0
- ✓ Immutable audit trail with PostgreSQL trigger enforcement -- v1.0
- ✓ Model governance with approval workflow -- v1.0
- ✓ 8-page React frontend with drill-down, export, and alerting -- v1.0

### Active

- [ ] Performance attribution (duration, spread, selection, sector allocation decomposition)
- [ ] Benchmark comparison engine (Sharpe, Information ratio, Tracking error)
- [ ] Loan-specific analytics (FICO distribution, geographic concentration, origination cohorts)
- [ ] AI/ML prepayment and default prediction models
- [ ] Pricing vendor API integration (Bloomberg, Refinitiv)
- [ ] Webhook triggers on run completion
- [ ] Connection pooling for high-concurrency scenarios
- [ ] Swaption and caps/floors pricer extensions
- [ ] CCAR/DFAST regulatory stress scenarios
- [ ] Load testing at 1M+ positions with partitioning strategy

### Out of Scope

- Real-time streaming analytics -- batch/intraday sufficient for thousands of positions
- Multi-tenant SaaS features -- internal team only, no tenant isolation needed
- Mobile application -- web-only, portfolio analytics requires large screens
- Full regulatory reporting generation (FFIEC, SEC N-PORT) -- framework only
- Commodity/FX spot trading analytics -- loan book is core

## Current State

**v1.0 shipped 2026-02-12** — deployed to AWS ECS with 9 live services, 21/21 smoke tests passing, real FRED market data seeded.

**Codebase:** 20,727 LOC across 204 files (Python, TypeScript, SQL). 116 commits over 12 days. 49/49 requirements delivered.

**Tech stack:** Python 3.11+ / FastAPI / PostgreSQL / React 18 / Vite / QuantLib / openpyxl / Terraform / GitHub Actions.

**Architecture:** 9 containerized microservices on ECS Fargate (marketdata, orchestrator, results, portfolio, data ingestion, regulatory, risk, worker, frontend/nginx), Cloud Map service discovery, Aurora PostgreSQL with RDS Proxy, ALB with single frontend target.

**Live environment:** `http://iprs-alb-dev-1833924090.us-east-1.elb.amazonaws.com`

**Known technical debt:**
- Pre-existing compute stubs (allowance.py, rwa.py, stress_capital.py) superseded but not removed
- Two stretch endpoints return 501 (hedge effectiveness, backtesting)
- No connection pooling (sync connection-per-request)
- Fixed volatility assumptions (20% flat for caps/floors)
- No HTTPS/custom domain on ALB
- No WAF or IP restriction on ALB

## Constraints

- **Tech stack**: Python 3.11+ / FastAPI / PostgreSQL / React 18 -- preserve existing investment
- **Infrastructure**: AWS (ECS Fargate, RDS Aurora, API Gateway) with Terraform IaC
- **CI/CD**: GitHub Actions
- **Database**: Shared PostgreSQL with schema-per-service logical separation
- **Compatibility**: v1.0 API contracts must remain backward-compatible in v1.x releases
- **Asset priority**: Loan instruments are primary; bonds, ABS/MBS, derivatives are secondary
- **Scale**: Thousands of positions, batch + intraday recalculation

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Function-based pricer registry | No base class required, backward-compatible | ✓ Good -- 8 pricers registered cleanly |
| QuantLib for curve construction | Industry standard, 20+ years development | ✓ Good -- multi-curve bootstrap works |
| Multi-curve framework from start | Post-2008 industry standard for basis spread | ✓ Good -- OIS/SOFR separation clean |
| Fixed Hull-White params (a=0.03, sigma=0.12) | Market-standard for USD callable bonds | ✓ Good -- defer swaption vol calibration |
| Historical PD lookup from Moody's data | Simpler than econometric models for v1 | ✓ Good -- sufficient for standardized approach |
| PostgreSQL recursive CTEs for hierarchy | DB-optimized tree traversal | ✓ Good -- no N+1 queries |
| Content-addressable snapshots (SHA-256) | Automatic deduplication, immutable versioning | ✓ Good -- proven pattern throughout |
| Trigger-based audit immutability | Regulatory compliance at DB layer | ✓ Good -- blocks UPDATE/DELETE |
| Multi-scenario CECL with probability weighting | ASC 326 compliance | ✓ Good -- enables stress integration |
| Basel III tuple-based risk weight lookup | Clean separation, fallback chain | ✓ Good -- extensible to IRB later |
| Shared PostgreSQL (no DB per service) | Simpler ops for internal team | -- Revisit if scale exceeds 100K positions |
| No connection pooling for v1 | Sufficient for <10K positions | -- Revisit for production load |
| Scaffold-first approach | Full structure before deep features | ✓ Good -- reduced rework |

---
*Last updated: 2026-02-13 after v1.0 milestone completion*
