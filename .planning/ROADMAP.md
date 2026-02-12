---
# ROADMAP: IPRS Institutional Portfolio Analytics Platform

**Version:** 1.0
**Created:** 2026-02-11
**Depth:** Quick (4 phases)
**Status:** Phase 1 Complete, Phase 2 Complete, Phase 3 Complete, Phase 4 Planned

---

## Overview

Expanding the Risk MVP from a working prototype into an institutional-grade portfolio analytics platform. The roadmap structures 49 v1 requirements into 4 coherent delivery phases that progressively add capability: foundation infrastructure → core compute engines → portfolio & data services → regulatory analytics & reporting. Each phase delivers observable value and unblocks the next.

---

## Phase Structure

| Phase | Goal | Requirements Mapped | Success Criteria | Plans |
|-------|------|-------------------|------------------|-------|
| **1 - Foundation & Infrastructure** ✓ | Platform skeleton ready; compute engine refactored with registry pattern; database schema extended for full analytics pipeline | PLAT-01 through PLAT-06 | 6/6 verified | 5 plans ✓ |
| **2 - Core Compute Engines** ✓ | Institutional-grade pricers, cashflow generation, risk analytics, and scenario execution; worker processes full pipeline end-to-end | PRICE-01 through PRICE-09, CF-01 through CF-06, RISK-01 through RISK-07, SCEN-01 through SCEN-04 | 8/8 verified | 9 plans ✓ |
| **3 - Portfolio & Data Services** ✓ | Portfolio hierarchy, position management, reference data; data ingestion pipelines; independent query services for aggregation | PORT-01 through PORT-08, DATA-01 through DATA-04, RISK-06 | 6/6 verified | 5 plans ✓ |
| **4 - Regulatory Analytics & Reporting** | Regulatory frameworks (GAAP/IFRS, Basel, CECL), audit trails, model governance; frontend expansion with domain-specific views and exports | REG-01 through REG-05, RPT-01 through RPT-04 | 9 success criteria | **6 plans** |

---

## Phase 4: Regulatory Analytics & Reporting

**Goal:** Regulatory frameworks (GAAP, IFRS, Basel, CECL), audit trails, model governance, and expanded frontend. Enables complete analytics and drill-down reporting.

**Why Last:** Phase 3 delivers portfolio and data services. This phase builds on top with regulatory aggregation and reporting. Completes the analytics stack.

**Plans:** 6 plans in 3 waves

Plans:
- [ ] 04-01-PLAN.md — Database schema extension (audit trail, regulatory reference, model governance, alerts)
- [ ] 04-02-PLAN.md — Regulatory compute modules (CECL, Basel, GAAP/IFRS calculations)
- [ ] 04-03-PLAN.md — Regulatory service implementation (CECL/Basel/accounting/audit/model governance routes)
- [ ] 04-04-PLAN.md — Export pipeline (CSV/Excel generation with openpyxl)
- [ ] 04-05-PLAN.md — Frontend expansion (Regulatory, AuditTrail, ModelGovernance, Export pages)
- [ ] 04-06-PLAN.md — Alerting and threshold monitoring (backend + frontend integration)

### Requirements Mapped

**Regulatory & Accounting (5 requirements):**
- **REG-01**: GAAP/IFRS valuation support framework (Plan 04-02, 04-03)
- **REG-02**: Expected credit loss modeling (CECL-style) (Plan 04-02, 04-03)
- **REG-03**: Basel III capital analytics and RWA calculation (Plan 04-02, 04-03)
- **REG-04**: Audit trail and calculation explainability (Plan 04-01, 04-03)
- **REG-05**: Model governance (versioning, backtesting, calibration tracking) (Plan 04-01, 04-03)

**Reporting & Visualization (4 requirements):**
- **RPT-01**: Frontend pages for each analytics domain (Plan 04-05)
- **RPT-02**: Drill-down analytics beyond current cube view (Plan 04-05)
- **RPT-03**: Export to CSV/Excel for downstream systems (Plan 04-04, 04-05)
- **RPT-04**: Alerting and threshold monitoring (Plan 04-06)

### Dependencies

- Phase 1: Shared library, service factory, database
- Phase 2: Compute engines producing results (risk analytics provide PD curves for CECL)
- Phase 3: Portfolio, reference data, data ingestion (portfolio hierarchy enables regulatory aggregation)

### Wave Structure

**Wave 1 (Foundation - parallel):**
- Plan 01: Database schema (audit_trail, regulatory_reference, model_governance, alert_config, alert_log, regulatory_metrics)
- Plan 02: Compute modules (CECL, Basel, GAAP/IFRS calculation functions)

**Wave 2 (Services - depends on Wave 1):**
- Plan 03: Regulatory Service (CECL/Basel/accounting/audit/model governance REST APIs on port 8006)
- Plan 04: Export pipeline (CSV with Python csv module, Excel with openpyxl)

**Wave 3 (Frontend - depends on Wave 2):**
- Plan 05: Frontend pages (Regulatory, AuditTrail, ModelGovernance, Export React components)
- Plan 06: Alerting (threshold evaluation, notification tracking, frontend alerts management)

### Success Criteria

1. **GAAP/IFRS valuation framework operational** - Portfolio can be valued under GAAP HTM (historical cost + impairment) or AFS (fair value), and IFRS (amortized cost + ECL). Valuation method selectable per position. Results show marked-to-market PV, accrued interest, and impairment allowances.

2. **CECL allowance calculated for loan portfolio** - System applies probability-of-default (PD) and loss-given-default (LGD) curves to loan population. Expected credit loss (ECL) allowance computed for each loan cohort (origination year, rating, geography). Portfolio allowance aggregates cohort allowances. Results validate against Basel standardized approach as lower bound.

3. **Basel III capital calculations working** - RWA calculated for all positions (standardized approach for loans/bonds, market risk capital charge for derivatives). Capital ratio (Tier 1 / RWA) computed at portfolio level. Stress tests show capital impact of adverse scenarios.

4. **Audit trail complete and immutable** - Every calculation (pricing, risk, regulatory) has immutable audit log: input data, model version, calculation timestamp, user, results. Logs are queryable and exportable. Explainability available: "why was this bond priced at $102?"

5. **Model governance framework in place** - Each pricer/risk calculator/regulatory model has version number, change log, backtesting results, calibration date. Models can be marked as "approved for production", "testing", or "deprecated". Calculation explainability linked to model version.

6. **Frontend pages cover all analytics domains** - React pages built for: regulatory (CECL allowance, Basel capital ratios), audit trail (calculation provenance search), model governance (version tracking), export (CSV/Excel download), alerts (threshold configuration and trigger history). Navigation intuitive via routing.

7. **Drill-down analytics functional** - Regulatory page shows CECL by segment, Basel RWA by counterparty type and rating. Audit trail page displays calculation assumptions and results JSON. All drill-downs load in <1 second.

8. **CSV/Excel export working** - User can export: regulatory report (CECL allowance by segment, Basel RWA summary, audit trail), CECL segment breakdown, Basel capital ratios. Exports formatted with openpyxl (Excel) or Python csv module (CSV). Downloads trigger via blob responseType.

9. **Alerting configured and tested** - Alerts trigger when: CET1 ratio below threshold, issuer concentration exceeds limit, credit deterioration detected, liquidity ratio falls below threshold. Alert configuration via frontend, evaluation via backend API, trigger history queryable.

### Acceptance Criteria

- All 9 requirements delivered
- Regulatory service runs on port 8006 with CECL, Basel, accounting, audit, model governance, alerts, and export routes
- Frontend pages render and respond in <1 second for regulatory calculations
- Regulatory calculations integrated with Phase 2 risk analytics (PD curves, LGD assumptions)
- Audit trail immutable with PostgreSQL trigger enforcement
- Model governance tracks all regulatory model versions with approval status
- Export quality meets audit requirements (complete, verifiable, timestamped, proper formatting)
- Alerting evaluates thresholds against regulatory_metrics table and logs breaches

---

## Success Metrics

**Overall project success when:**

- All 49 v1 requirements delivered and mapped to phases (100% coverage)
- Phase 1 complete: Platform foundation and compute engine ready ✓
- Phase 2 complete: Institutional-grade pricers and risk analytics operational ✓
- Phase 3 complete: Portfolio management and data ingestion pipelines functional ✓
- Phase 4 complete: Regulatory frameworks and reporting operational
- End-to-end workflow tested: Market data ingestion → Portfolio upload → Run execution → Results reporting (all in <15 min for 5000 positions)
- User acceptance testing passed by risk team
- Deployed to AWS with auto-scaling and monitoring in place

---

## Coverage Validation

**Requirement Mapping Summary:**

| Category | Total | Mapped to Phase |
|----------|-------|-----------------|
| Platform (PLAT) | 6 | Phase 1 ✓ |
| Pricing (PRICE) | 9 | Phase 2 ✓ |
| Portfolio (PORT) | 8 | Phase 3 ✓ |
| Cashflow (CF) | 6 | Phase 2 ✓ |
| Risk (RISK) | 7 | Phase 2 (6) ✓, Phase 3 (1) ✓ |
| Scenario (SCEN) | 4 | Phase 2 ✓ |
| Regulatory (REG) | 5 | Phase 4 |
| Data (DATA) | 4 | Phase 3 ✓ |
| Reporting (RPT) | 4 | Phase 4 |
| **TOTAL** | **49** | **49 / 49** |

**Coverage:** 49/49 requirements mapped. No orphans. No duplicates.

---

## Phase Dependencies

```
Phase 1: Foundation & Infrastructure ✓
  │
  ├─→ Phase 2: Core Compute Engines ✓
  │     └─→ Phase 3: Portfolio & Data Services ✓
  │           └─→ Phase 4: Regulatory Analytics & Reporting
  │
  └─→ Parallelization: Phases 2 and 3 can overlap (compute and portfolio)
      after Phase 1 foundation is complete (Week 3-4).
```

---

## Next Steps

1. **Phase 4 Execution:** Begin with `/gsd:execute-phase 04` to run first wave (Plans 01-02)
2. **Estimate Effort:** Phase 4 ~3-4 weeks (6 plans, 3 waves, regulatory compute + frontend expansion)
3. **Completion:** After Phase 4, all 49 v1 requirements delivered and IPRS platform feature-complete

---

*Roadmap Version 1.0 created 2026-02-11 by GSD Roadmapper*
*Phase 2 plans added 2026-02-11 by GSD Planner*
*Phase 3 plans added 2026-02-11 by GSD Planner*
*Phase 4 plans added 2026-02-11 by GSD Planner*
