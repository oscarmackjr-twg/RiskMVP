# STATE: IPRS Portfolio Analytics Platform

**Project:** IPRS Institutional Portfolio Risk & Analytics System
**Created:** 2026-02-11
**Last Updated:** 2026-02-11T20:14:21Z

---

## Project Reference

**Core Value:** The risk team can run end-to-end portfolio analytics on their loan portfolio with institutional-grade reproducibility and audit trails.

**Current Status:** Phase 1 Complete - Ready for Phase 2

**Team:** Solo developer + Claude (orchestrator mode)

---

## Current Position

| Metric | Status |
|--------|--------|
| **Active Phase** | Phase 2: Core Compute Engines (IN PROGRESS) |
| **Current Plan** | 02-05 COMPLETE ✓ — Plan 02-06 next |
| **Overall Progress** | 33% (Phase 1 complete + 2/8 Phase 2 plans, 9/49 requirements delivered) |
| **Requirements Coverage** | 49/49 mapped (100%) |
| **Blockers** | None |

### Progress Bar

```
Foundation [########] Core Compute [##......] Portfolio [........] Regulatory [........]
    100%                    25%                     0%                  0%
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

**Phase 02 Plan 06: Payment Schedule Generation Engine**

1. **Implemented generate_schedule()** - QuantLib-based cashflow schedule generator supporting LEVEL_PAY, BULLET, and CUSTOM amortization
2. **Verified amortization logic** - level_pay_schedule, bullet_schedule, custom_schedule already implemented in Plan 02-04
3. **QuantLib Schedule integration** - Date generation with calendar adjustments using ModifiedFollowing convention
4. **Future-only filtering** - Schedules filter for pay_date > as_of_date enabling mid-life valuation
5. **Comprehensive test suite** - 19 tests covering all amortization types, schedule generation, and edge cases
6. **Bug fixes** - Fixed QuantLib API usage, schedule date indexing, issue date exclusion, and validation

**Commits:**
- 2171df5: feat(02-06): implement payment schedule generator with QuantLib
- f480bc1: test(02-06): add comprehensive tests for cashflow generation

**Duration:** 330 seconds (5 min 30 sec)

---

**Phase 2 Plan 06 Complete!** Cashflow generation infrastructure ready.
- Payment schedule generator with QuantLib date handling
- All amortization types (level pay, bullet, custom)
- Future-only filtering for mid-life valuation
- 19 tests validating all scenarios and edge cases

### Next Session Starting Point

**Phase 2 Plan 06 complete. Plan 02-01 previously completed. Next: Plan 02-02 (Callable/Putable Bond Pricer)**

**Files to reference:**
- `.planning/phases/02-core-compute-engines/02-06-SUMMARY.md` — Cashflow generation summary
- `.planning/phases/02-core-compute-engines/02-01-SUMMARY.md` — QuantLib curve construction summary
- `.planning/phases/02-core-compute-engines/02-02-PLAN.md` — Next plan (callable/putable bonds)
- `compute/cashflow/generator.py` — Payment schedule generation engine
- `compute/quantlib/curve_builder.py` — Multi-curve framework ready for bond pricing

**Git status:**
- Main branch active
- Phase 2 Plan 01 complete (3 commits, 5 files) - QuantLib curves
- Phase 2 Plan 06 complete (2 commits, 2 files) - Cashflow generation
- Ready to implement callable/putable bond pricer using QuantLib TreeCallableFixedRateBondEngine

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
