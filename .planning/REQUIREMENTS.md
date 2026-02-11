# Requirements: IPRS Portfolio Analytics Platform

**Defined:** 2026-02-11
**Core Value:** The risk team can run end-to-end portfolio analytics on their loan portfolio with institutional-grade reproducibility and audit trails.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Platform Foundation

- [ ] **PLAT-01**: Shared Pydantic models, events, auth middleware, and config across all services
- [ ] **PLAT-02**: Common service factory with health checks, pagination, and error handling
- [ ] **PLAT-03**: Docker containerization for all services and workers
- [ ] **PLAT-04**: Terraform AWS infrastructure (VPC, ECS Fargate, RDS Aurora, API Gateway, SQS, ECR)
- [ ] **PLAT-05**: GitHub Actions CI/CD pipelines (lint, test, build, deploy)
- [ ] **PLAT-06**: Pricer registry pattern replacing if/elif dispatch

### Pricing & Valuation

- [ ] **PRICE-01**: Floating-rate instrument pricer
- [ ] **PRICE-02**: Callable bond pricer with OAS
- [ ] **PRICE-03**: Putable bond pricer
- [ ] **PRICE-04**: ABS/MBS pricer with prepayment models
- [ ] **PRICE-05**: Structured product pricer
- [ ] **PRICE-06**: Derivatives hedge pricer
- [ ] **PRICE-07**: Full curve construction (multi-curve, bootstrap, interpolation methods)
- [ ] **PRICE-08**: Day count conventions (ACT/360, ACT/365, 30/360) and business day calendar
- [ ] **PRICE-09**: Measures: Clean/Dirty price, YTM, YTC/YTP, OAS, Z-spread, DM, Par spread

### Portfolio Management

- [ ] **PORT-01**: Instrument master service with CRUD for loans, bonds, ABS/MBS, derivatives
- [ ] **PORT-02**: Reference data management (issuers, sectors, ratings, geography)
- [ ] **PORT-03**: Portfolio hierarchy and node management
- [ ] **PORT-04**: Position tracking and holdings aggregation (by issuer, sector, rating, geography)
- [ ] **PORT-05**: Portfolio segmentation and tagging
- [ ] **PORT-06**: Historical snapshots and time-series tracking
- [ ] **PORT-07**: Multi-currency support with FX conversion to base currency
- [ ] **PORT-08**: Portfolio metrics: Market value, Book value, Accrued interest, Unrealized/Realized P&L, Portfolio yield, WAM, WAL

### Cash Flow Modeling

- [ ] **CF-01**: Payment schedule generation (level pay, bullet, custom amortization)
- [ ] **CF-02**: Prepayment modeling (CPR, PSA speeds)
- [ ] **CF-03**: Default and recovery modeling (LGD, EAD)
- [ ] **CF-04**: Adjustable rate reset logic
- [ ] **CF-05**: Scenario cash flow projection
- [ ] **CF-06**: Waterfall modeling for structured products

### Risk Analytics

- [ ] **RISK-01**: Duration calculations (Macaulay, Modified, Effective)
- [ ] **RISK-02**: DV01/PV01 and Convexity
- [ ] **RISK-03**: Key rate duration and Spread duration
- [ ] **RISK-04**: VaR (Historical, Parametric) and Expected Shortfall
- [ ] **RISK-05**: Credit risk: PD modeling, Expected loss, Unexpected loss
- [ ] **RISK-06**: Rating migration tracking and Concentration monitoring
- [ ] **RISK-07**: Liquidity risk: Bid/ask spread analytics, Time-to-liquidate, LCR

### Scenario & Forecasting

- [ ] **SCEN-01**: Scenario definition and management service (CRUD, scenario sets)
- [ ] **SCEN-02**: Stress testing configuration (rate shocks, spread shocks, FX shocks)
- [ ] **SCEN-03**: Monte Carlo simulation engine (interest rate paths, macro factors)
- [ ] **SCEN-04**: What-if analysis and portfolio rebalancing simulation

### Regulatory & Accounting

- [ ] **REG-01**: GAAP/IFRS valuation support framework
- [ ] **REG-02**: Expected credit loss modeling (CECL-style)
- [ ] **REG-03**: Basel III capital analytics and RWA calculation
- [ ] **REG-04**: Audit trail and calculation explainability
- [ ] **REG-05**: Model governance (versioning, backtesting, calibration tracking)

### Data Integration

- [ ] **DATA-01**: Market data feed ingestion (yield curves, credit spreads, ratings feeds)
- [ ] **DATA-02**: Loan servicing data ingestion
- [ ] **DATA-03**: Historical data versioning
- [ ] **DATA-04**: Data lineage tracking

### Reporting & Visualization

- [ ] **RPT-01**: Frontend pages for each analytics domain (instruments, portfolio, risk, cashflows, scenarios, regulatory)
- [ ] **RPT-02**: Drill-down analytics beyond current cube view (by issuer, sector, rating, geography)
- [ ] **RPT-03**: Export to CSV/Excel for downstream systems
- [ ] **RPT-04**: Alerting and threshold monitoring

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Analytics

- **ADV-01**: Performance attribution (duration, spread, selection, sector allocation decomposition)
- **ADV-02**: Benchmark comparison engine (Sharpe, Information ratio, Tracking error)
- **ADV-03**: Loan-specific analytics (FICO distribution, geographic concentration, origination cohorts)
- **ADV-04**: Prepayment forecasting with seasonal adjustments

### AI/ML

- **ML-01**: Prepayment prediction model
- **ML-02**: Default prediction model
- **ML-03**: Spread forecasting model
- **ML-04**: Anomaly detection

### Integration

- **INT-01**: Pricing vendor API integration (Bloomberg, Refinitiv)
- **INT-02**: Webhook triggers on run completion
- **INT-03**: API-first design for downstream system integration

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time streaming analytics | Batch + intraday sufficient for thousands of positions; 5x infra cost for 2% improvement |
| Multi-tenant SaaS | Internal team only; 30-50% architectural overhead for no benefit |
| Mobile application | Portfolio analytics requires large screens; 1-2% of users |
| Full regulatory reporting (FFIEC, SEC N-PORT) | Beyond scope for internal tool; provide framework for firm's compliance systems |
| AI/ML models | Hard to maintain, need 3+ years of data; defer to v2 with heuristic models for now |
| Commodity/FX spot trading analytics | Loan book is core; different risk model |
| Custom portfolio optimization (mean-variance) | Domain expertise heavy; provide raw analytics for PM decision-making |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PLAT-01 | — | Pending |
| PLAT-02 | — | Pending |
| PLAT-03 | — | Pending |
| PLAT-04 | — | Pending |
| PLAT-05 | — | Pending |
| PLAT-06 | — | Pending |
| PRICE-01 | — | Pending |
| PRICE-02 | — | Pending |
| PRICE-03 | — | Pending |
| PRICE-04 | — | Pending |
| PRICE-05 | — | Pending |
| PRICE-06 | — | Pending |
| PRICE-07 | — | Pending |
| PRICE-08 | — | Pending |
| PRICE-09 | — | Pending |
| PORT-01 | — | Pending |
| PORT-02 | — | Pending |
| PORT-03 | — | Pending |
| PORT-04 | — | Pending |
| PORT-05 | — | Pending |
| PORT-06 | — | Pending |
| PORT-07 | — | Pending |
| PORT-08 | — | Pending |
| CF-01 | — | Pending |
| CF-02 | — | Pending |
| CF-03 | — | Pending |
| CF-04 | — | Pending |
| CF-05 | — | Pending |
| CF-06 | — | Pending |
| RISK-01 | — | Pending |
| RISK-02 | — | Pending |
| RISK-03 | — | Pending |
| RISK-04 | — | Pending |
| RISK-05 | — | Pending |
| RISK-06 | — | Pending |
| RISK-07 | — | Pending |
| SCEN-01 | — | Pending |
| SCEN-02 | — | Pending |
| SCEN-03 | — | Pending |
| SCEN-04 | — | Pending |
| REG-01 | — | Pending |
| REG-02 | — | Pending |
| REG-03 | — | Pending |
| REG-04 | — | Pending |
| REG-05 | — | Pending |
| DATA-01 | — | Pending |
| DATA-02 | — | Pending |
| DATA-03 | — | Pending |
| DATA-04 | — | Pending |
| RPT-01 | — | Pending |
| RPT-02 | — | Pending |
| RPT-03 | — | Pending |
| RPT-04 | — | Pending |

**Coverage:**
- v1 requirements: 49 total
- Mapped to phases: 0
- Unmapped: 49

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after initial definition*
