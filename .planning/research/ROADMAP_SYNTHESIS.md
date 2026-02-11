# Roadmap Synthesis: Complete Research Summary

**Date:** 2026-02-11
**Status:** RESEARCH COMPLETE - Ready for Phase Planning
**Overall Confidence:** HIGH (HIGH on architecture, MEDIUM-HIGH on domain complexity)

---

## Quick Executive Summary

The existing MVP has proven the core architectural pattern: distributed workers with PostgreSQL queue, immutable snapshots, UPSERT idempotency. **No architectural rethinking needed.** Scale by:

1. **Phase 1 (Weeks 1-4):** Extend database schema + build new pricers in isolated worker loop
2. **Phase 2 (Weeks 5-8):** Add 7 FastAPI query services (no inter-service RPC during compute)
3. **Phase 3 (Weeks 9-12):** Frontend enhancements + caching + integration tests
4. **Phase 4 (Weeks 13+):** Distributed worker scaling (50+ workers) + Monte Carlo

**Technology:** Python 3.11 + QuantLib 1.34 + FastAPI + PostgreSQL Aurora + React 18

**Effort estimate:** 4-6 FTE over 12 weeks. Critical path is compute enhancements (pricers, cash flow, risk calculations).

---

## What You Have (MVP Foundation)

| Component | Status | Quality |
|-----------|--------|---------|
| Distributed task queue (PostgreSQL FOR UPDATE SKIP LOCKED) | ✓ Production-ready | HIGH - proven pattern |
| Immutable snapshots + content hashing | ✓ Implemented | HIGH - audit-ready |
| UPSERT-based idempotency | ✓ Working | HIGH - safe retries |
| Basic pricers (FX, loan, bond) | ✓ Functional | MEDIUM - needs institutional expansion |
| Scenario application framework | ✓ Working | MEDIUM - needs edge case testing |
| FastAPI 3-service skeleton | ✓ Deployed | MEDIUM - needs 7 more services |
| React 18 + React Query frontend | ✓ Basic UI | MEDIUM - needs analytics views |
| PostgreSQL schema (core run tables) | ✓ Initialized | MEDIUM - needs dimension tables |

**Verdict:** Foundation is solid. Safe to build on. No rewrites needed.

---

## What You Need (Gap Analysis)

### Compute Engine Gaps (Critical Path)

| Gap | Impact | Effort | Roadblock |
|-----|--------|--------|-----------|
| QuantLib integration | HIGH | 2 weeks | NO - straightforward |
| Callable/putable bond pricers | HIGH | 2 weeks | NO - QuantLib handles |
| ABS/MBS with prepayment models | HIGH | 3 weeks | YES - needs CPR/SMM research |
| Structured product pricers | MEDIUM | 4 weeks | YES - Monte Carlo complexity unclear |
| Cash flow generator (unified) | HIGH | 1 week | NO - skeleton exists |
| ARM reset modeling | MEDIUM | 1 week | NO - amortization logic |
| Risk metric calculators (DV01, duration, spreads, credit) | HIGH | 2 weeks | NO - formulas straightforward |
| CECL allowance engine | MEDIUM | 2 weeks | YES - needs compliance input |
| Basel III RWA calculator | MEDIUM | 1 week | NO - regulatory formula |

**Roadblock analysis:** Two unknowns - ABS/MBS prepayment complexity and structured product Monte Carlo. Recommend 1-week spike with quant team before committing Phase 1.

### Service Layer Gaps

| Gap | Impact | Effort | Dependencies |
|-----|--------|--------|--------------|
| portfolio_svc | HIGH | 1 week | Database schema |
| risk_svc | HIGH | 1.5 weeks | results_api, risk_metrics table |
| cashflow_svc | MEDIUM | 0.5 weeks | cashflow_schedule table |
| regulatory_svc | HIGH | 1.5 weeks | regulatory_metrics table |
| scenario_svc | MEDIUM | 0.5 weeks | Scenario table |
| data_ingestion_svc | MEDIUM | 1.5 weeks | All dimension tables |
| results_api (enhancement) | MEDIUM | 0.5 weeks | Existing, extend |

**Effort:** 6.5 weeks total. Can parallelize after database ready.

### Database Gaps

| Gap | Impact | Effort |
|-----|--------|--------|
| portfolio, position, counterparty tables | HIGH | 1 day |
| scenario, scenario_set tables | MEDIUM | 0.5 day |
| valuation_result, cashflow_schedule, risk_metrics tables | HIGH | 1 day |
| regulatory_metrics table | MEDIUM | 0.5 day |
| Indexes + partitioning strategy | HIGH | 0.5 day |
| Aurora setup + RDS Proxy + read replicas | HIGH | 2 days |

**Effort:** ~1 week.

### Infrastructure Gaps

| Gap | Impact | Effort | Critical |
|-----|--------|--------|----------|
| Terraform modules (ECS, RDS, networking) | HIGH | 2 weeks | NO - standard patterns |
| CloudWatch logging + alarms | MEDIUM | 1 week | NO - standard setup |
| ECR registry setup | LOW | 1 day | NO - AWS managed |
| CI/CD (GitHub Actions) | MEDIUM | 1 week | NO - can defer to Phase 2 |

**Effort:** 3-4 weeks. Can parallelize with compute work.

---

## Recommended Phase Structure

### Phase 1: Foundation (Weeks 1-4)

**Goal:** Extend MVP pricing to institutional-grade instruments. No new services yet.

**Deliverables:**
1. Database: Add portfolio, position, scenario, cashflow_schedule, risk_metrics, regulatory_metrics tables (Week 1)
2. Compute: Add QuantLib integration, new pricers (callable, putable, floating-rate, ABS/MBS baseline) (Weeks 1-2)
3. Compute: Unified cash flow generator with day-count conventions (Week 1)
4. Compute: Risk metric calculators (DV01, spread duration, key-rate duration) (Week 2)
5. Compute: CECL allowance engine skeleton + Basel III RWA calculator (Week 3)
6. Golden tests: 100+ positions with known Bloomberg prices (Weeks 2-3)
7. Performance testing: Validate <100ms/position pricing at 1000 positions (Week 4)

**What NOT to do:**
- Don't build new services yet. Compute only.
- Don't optimize yet. Get correctness first.
- Don't do Monte Carlo yet. Batch scenarios sufficient.

**Why this order:**
- Database is prerequisite for all downstream services
- Compute enhancements must be battle-tested before scaling
- Services depend on stable compute results
- Golden tests prevent integration-time surprises

**Risks:**
- ABS/MBS prepayment complexity underestimated (might spill to Phase 2)
- Structured product scope unclear (spike first, commit later)

**Success criteria:**
- [ ] QuantLib curve construction passes golden tests (match Bloomberg ±5bps)
- [ ] Callable bond pricer passes golden tests (OAS within market ±10bps)
- [ ] Portfolio pricing: 1000 positions in <15 minutes with 5 workers
- [ ] CECL engine computes allowance (values TBD, structure correct)
- [ ] All pricers handle edge cases (0% coupon, negative rates, stressed spreads) without NaN

---

### Phase 2: Query Services Layer (Weeks 5-8)

**Goal:** Build analytics services that independently query compute results. No service-to-service RPC during compute.

**Deliverables:**
1. portfolio_svc (Week 5)
   - Portfolio hierarchy CRUD
   - Position ingestion + validation
   - Portfolio tagging (desk, strategy, book)

2. risk_svc (Week 5-6)
   - Portfolio risk aggregation (SUM DV01, WEIGHTED DURATION, concentration)
   - Risk vectors by factor
   - VaR/ES aggregation

3. results_api (Week 5) - extend existing
   - Add filter/drill-down by position, scenario, product_type
   - Support pagination (keyset pagination for 1M+ positions)

4. cashflow_svc (Week 6)
   - Payment schedule queries
   - Maturity ladder aggregation
   - Duration bridge

5. regulatory_svc (Week 6-7)
   - Capital adequacy (Basel RWA aggregation)
   - CECL allowance by segment
   - Stress capital reporting

6. scenario_svc (Week 5) - lightweight
   - Scenario CRUD
   - Scenario set management

7. data_ingestion_svc (Week 7-8)
   - CSV/JSON position import
   - Market data upload validation
   - Bulk instrument master import

**What NOT to do:**
- Don't have services call each other. All read from database independently.
- Don't cache yet. Get functionality first.
- Don't optimize queries yet. Correctness first.

**Why this order:**
- Services are independent (can parallelize)
- All depend on Phase 1 compute completion
- Data-driven architecture avoids coupling

**Success criteria:**
- [ ] portfolio_svc can load 10K positions without errors
- [ ] risk_svc aggregates DV01 correctly (matches manual sum)
- [ ] cashflow_svc serves maturity ladder in <500ms
- [ ] No inter-service RPC calls during compute
- [ ] End-to-end run takes <20 min for 5K positions

---

### Phase 3: Analytics Frontend & Caching (Weeks 9-12)

**Goal:** Build UI for drill-down analysis. Add caching only after measuring slow queries.

**Deliverables:**
1. Frontend: Scenario selection UI + drill-down views (Week 9)
2. Frontend: Risk aggregation dashboard (Week 10)
3. Frontend: Cashflow ladder visualization (Week 10)
4. Frontend: Regulatory summary reports (Week 11)
5. Cache layer: Redis for repeated portfolio aggregations (4h TTL) (Week 11)
6. Integration tests: End-to-end runs + service composition (Week 12)
7. Load testing: 5K positions × 10 scenarios × 10 workers (Week 12)

**Measurement before caching:**
- Profile queries: which ones take >1s?
- Cache only if repeated 10+ times in same user session
- Never cache: curves, positions, pricing results (volatility too high)
- Cache: scenario definitions, FX conversion tables, portfolio aggregations

**Success criteria:**
- [ ] Dashboard loads aggregate portfolio risk in <2s
- [ ] Drill-down to position detail in <500ms
- [ ] Cache hit rate >70% for typical user session
- [ ] Full run: 5K positions in <30 min (not <10 min yet, optimize later)

---

### Phase 4: Distributed Scaling & Monte Carlo (Weeks 13+)

**Goal:** Scale to 50+ workers. Add Monte Carlo for correlated scenarios.

**Deliverables:**
1. Worker scaling: Terraform auto-scaling by task queue depth
2. Connection pooling: RDS Proxy for 50+ concurrent workers
3. Monte Carlo engine: Rate path generation + portfolio revaluation (separate from pricing)
4. VaR/ES reporting: Tail risk aggregation
5. Performance optimization: Query plan analysis, result partitioning
6. Monitoring: CloudWatch dashboards for worker utilization, pricing latency

**Caution:**
- Don't start Monte Carlo until pricing is <15 min for full portfolio
- Don't parallelize workers until determinism verified (same run_id always yields same result)

**Success criteria:**
- [ ] 50 workers, task queue depth stable <100
- [ ] Monte Carlo: 1000 paths in <60 sec
- [ ] Database query latency stable at <500ms even with 1M result rows
- [ ] Pricing + Monte Carlo: 5K positions, 1000 paths in <2 hours

---

### Phase 5: Production Hardening & Regulatory (Weeks 20+)

**Goal:** Production-grade operations. Regulatory compliance.

**Deliverables:**
1. Audit trail: Full lineage (input → model → output) for regulatory queries
2. Regulatory reporting: Templated Basel III, CECL, stress-test submissions
3. Model governance: Pricer versioning, validation status tracking
4. Disaster recovery: Backup/restore strategy, multi-AZ setup
5. SLA monitoring: Alerts on pricing latency, accuracy drift
6. Documentation: Model documentation, assumptions, limitations

**Timeline:** Post-Phase 4, driven by regulatory requirements.

---

## Recommended Stack (Final)

### Backend

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Runtime** | Python 3.11 | FastAPI requirement, stable LTS |
| **Framework** | FastAPI 0.109+ | Async REST, proven at scale |
| **Database** | PostgreSQL 15+ Aurora | Managed, auto-backups, read replicas |
| **Pricing** | QuantLib 1.34 | Industry standard, institutional-grade |
| **Math** | NumPy 1.26 + SciPy 1.14 | Standard financial compute |
| **Performance** | Numba 0.59 | 50-100x for cashflow generation |
| **Risk models** | Statsmodels 0.14 | PD/LGD calibration |
| **Distributed** | Ray 2.28 (Phase 4) | Horizontal Monte Carlo scaling |
| **Database driver** | psycopg 3.1 | Async, no ORM overhead |

### Frontend

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Runtime** | React 18 | Standard, stable, rich ecosystem |
| **Language** | TypeScript 5.6 | Type safety for financial calculations |
| **Build** | Vite 5.4 | Fast dev/build, modern tooling |
| **Styling** | TailwindCSS 3.4 | Utility CSS, fast prototyping |
| **Data fetching** | TanStack Query 5.6 | Server state, caching, refetch |
| **Tables** | TanStack Table 8.16 | Virtualized 1K+ positions |
| **Charts** | Plotly.js 2.26 | Interactive financial visualizations |

### Infrastructure

| Component | Version | Rationale |
|-----------|---------|-----------|
| **Container** | Docker 27 | Standard, ECR integration |
| **Orchestration** | ECS Fargate | Serverless, auto-scaling, CloudWatch |
| **Database** | RDS Aurora | Managed PostgreSQL, replicas, Proxy |
| **IaC** | Terraform 1.7 | Reproducible, version-controlled |
| **Monitoring** | CloudWatch | Built-in ECS/RDS integration |
| **Secrets** | Secrets Manager | Credential rotation, audit trail |

---

## Critical Dependencies & Blockers

### Known Unknowns (Requires Research)

| Item | Impact | Status | Resolution |
|------|--------|--------|-----------|
| ABS/MBS prepayment modeling complexity | MEDIUM-HIGH | Researched but not coded | Spike with quant team, estimate effort |
| Structured product Monte Carlo scope | MEDIUM | Researched but deferred | Separate feasibility study Phase 1 Week 1 |
| CECL regulatory interpretation (by segment) | MEDIUM | Framework ready, details TBD | Collaboration with compliance team |
| Multi-currency aggregation rules | LOW | Not yet researched | Clarify with risk team Phase 1 |

### Data Availability

| Data | Source | Status | Action |
|------|--------|--------|--------|
| Golden test data (100+ Bloomberg prices) | Bloomberg Terminal / FactSet | Needed | Assign to data team Week 1 |
| Historical prepayment data (CPR/PSA) | Investor pools / Freddie Mac | Needed | Obtain historical tables Week 1 |
| Regulatory stress scenarios (CCAR, DFAST) | Federal Reserve / OCC | Available | Compliance team to source Week 1 |
| Peer portfolio data (for benchmarking) | TBD | Optional | Phase 4+ feature, defer |

---

## Risk Assessment

### High Risk Factors

| Factor | Mitigation |
|--------|-----------|
| **Numerical stability in pricers** | Extensive edge case testing (0% coupon, negative rates, distressed spreads). Compare to Bloomberg on sample positions. |
| **Prepayment model assumptions** | Use market CPR/PSA curves (conservative). Validate against historical prepayment data. Review with investors. |
| **Regulatory compliance gaps** | Capture audit trail from day 1. Involve compliance team in Phase 1. Model governance framework Phase 5. |
| **Performance at scale (1M positions)** | Profile early (Phase 1 end). Test at 1K positions before Phase 2. Optimize queries before scaling workers. |
| **Data consistency in distributed system** | Immutable snapshots + position locking + run state machine. Tested patterns from MVP. |

### Medium Risk Factors

| Factor | Mitigation |
|--------|-----------|
| **Microservice coupling** | Service boundaries based on data ownership, not code org. All read database independently (no RPC during compute). |
| **JSONB schema fragility** | Strict validation via Pydantic models. Quarterly audits of JSONB documents. Version schemas. |
| **Curve construction lineage loss** | Capture metadata (source, interpolation, adjustments). Version snapshots immutably. |
| **Task leasing failures at 50+ workers** | Robust heartbeat + lease management. Tested FOR UPDATE patterns. Idempotent result writes. |

---

## Success Criteria by Phase

### Phase 1 Success
- ✓ Institutional pricers (callable/putable, floating-rate) tested against Bloomberg
- ✓ 1000 positions priced in <15 minutes with 5 workers
- ✓ CECL framework functional (values TBD, structure validated)
- ✓ Golden test suite covers 100+ realistic positions
- ✓ No edge case crashes (0% coupon, negative rates, distressed spreads)

### Phase 2 Success
- ✓ All 7 new services deployed and functional
- ✓ Portfolio drill-down latency <500ms
- ✓ End-to-end run: 5K positions in <30 min
- ✓ Zero inter-service RPC calls during compute
- ✓ Results consistency validated (position sum = portfolio total)

### Phase 3 Success
- ✓ Frontend drill-down dashboard operational
- ✓ Cache hit rate >70% for typical user session
- ✓ Cache invalidation working correctly
- ✓ Load testing: 5K positions, 10 scenarios, performance baseline established

### Phase 4 Success
- ✓ 50 workers auto-scaling by task queue depth
- ✓ Monte Carlo: 1000 paths, 5K positions in <2 hours
- ✓ Database query latency <500ms at 1M result rows
- ✓ VaR/ES reporting functional

---

## Team Structure & Effort Allocation

**Recommended team:** 4-6 FTE

| Role | FTE | Weeks 1-4 | Weeks 5-8 | Weeks 9-12 | Weeks 13+ |
|------|-----|----------|----------|-----------|-----------|
| **Quant Engineer** | 1.5 | Pricers (QuantLib), golden tests | Risk metrics, CECL | Monte Carlo | Structured products |
| **Backend Engineer** | 2 | Database schema, worker enhancements | Services (portfolio, risk) | Caching, aggregation | Distributed worker ops |
| **Frontend Engineer** | 1 | (Review only) | Results API queries | Dashboard, viz | Advanced analytics |
| **DevOps/Infra** | 0.5 | Database setup, Terraform | CloudWatch setup | Monitoring | Scaling, SRE |
| **QA/Data** | 1 | Golden test data, edge cases | Integration tests | Load testing | Regulatory validation |

**Critical path:** Quant engineer (pricers) blocks Backend (services). Frontend unblocked after Phase 1.

---

## Decision Gates

### Before Phase 1 Starts (Day 1)
- [ ] Quant team confirms ABS/MBS prepayment model complexity (estimate vs. actual)
- [ ] Structured product Monte Carlo scope validated (2-week estimate?)
- [ ] Compliance team provides CECL regulatory framework (ASC 326 vs. IFRS 9)
- [ ] Bloomberg terminal access confirmed (golden test data)

### End of Phase 1 (Week 4)
- [ ] Pricers match Bloomberg ±5bps on 20+ golden positions
- [ ] 1000 positions priced in <15 min (latency acceptable?)
- [ ] Edge case testing complete (no NaN/crashes)
- **Gate:** If any criterion fails, adjust Phase 2 timeline; don't proceed until pricing production-ready

### End of Phase 2 (Week 8)
- [ ] All 7 services deployed + queries <500ms
- [ ] End-to-end run: 5K positions in <30 min
- [ ] Portfolio drill-down accurate (top-down = bottom-up)
- **Gate:** If services latency >1s or inconsistency found, iterate Phase 2

### End of Phase 3 (Week 12)
- [ ] Frontend dashboard operational
- [ ] Load testing complete (5K positions, 10 scenarios)
- [ ] Cache strategy working (>70% hit rate)
- **Gate:** If performance <baseline, optimize queries before Phase 4

### End of Phase 4 (Week 20)
- [ ] 50 workers stable, auto-scaling working
- [ ] Monte Carlo <2 hours for 1000 paths
- [ ] VaR/ES reporting functional
- **Gate:** Production release decision

---

## Open Questions to Resolve

1. **ABS/MBS prepayment:** How complex is CPR/SMM model? Days or weeks?
2. **Structured products:** Is Monte Carlo essential or can we defer?
3. **CECL methodology:** Does team want ASC 326 (US) or IFRS 9 (EU) or both?
4. **Curve construction:** Buy QuantLib curves or build custom OIS/spread curve builder?
5. **Multi-currency:** Treat USD base + FX spot conversion or separate workflows?
6. **Audit trail:** Regulatory requirement for full lineage, or summary sufficient?

**Next step:** Sync with team to clarify these before Phase 1 kickoff.

---

## Appendix: Research Confidence Summary

| Area | Confidence | Rationale |
|------|-----------|-----------|
| **Architecture** | HIGH | MVP patterns proven. No rewrites needed. |
| **Core stack (QuantLib, FastAPI, PostgreSQL)** | HIGH | Industry-standard choices. Widely used. |
| **Database schema** | MEDIUM-HIGH | Tables designed, but refinements likely during Phase 1 |
| **Service boundaries** | MEDIUM-HIGH | Logical split, but inter-service needs may require iteration |
| **Compute enhancements (pricers, risk metrics)** | MEDIUM | Formulas known, but implementation complexity for edge cases |
| **ABS/MBS prepayment modeling** | MEDIUM | Conceptually sound, effort estimate uncertain |
| **Structured product pricing** | LOW | Scope unclear. Needs deeper investigation. |
| **CECL compliance interpretation** | MEDIUM | Framework ready, regulatory details TBD |
| **Scaling to 1M positions** | MEDIUM | Theoretically possible, load testing required |
| **Frontend data visualization** | MEDIUM-HIGH | Plotly well-suited, but drill-down complexity TBD |

---

## Document History

- **2026-02-11** — Initial research complete. Phase planning ready.

---

**Prepared by:** Claude Research Agent (Phase 6: Research)
**Next:** Phase planning meeting with team to finalize roadmap
