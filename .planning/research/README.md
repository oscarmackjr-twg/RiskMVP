# Research Documentation Index

**Research Date:** 2026-02-11
**Project:** IPRS Risk Platform - Expansion to Institutional Portfolio Analytics
**Status:** COMPLETE - Ready for Phase Planning

---

## Overview

This research investigates the technology stack, architecture, features, pitfalls, and roadmap for expanding an existing Python/FastAPI/PostgreSQL risk MVP into a full institutional-grade portfolio analytics platform for loan-heavy fixed income portfolios (70%+).

**Key finding:** The MVP's architectural patterns (distributed task queue, immutable snapshots, UPSERT idempotency) are production-grade and scalable. No rewrites needed. Build incrementally on proven foundation.

---

## Research Documents

### 1. **SUMMARY.md** — Executive Summary & Roadmap Implications

**Start here.** Synthesizes all research into clear phase recommendations.

- Executive summary of findings
- Phase structure (1-5, 10-12 weeks total)
- Phase ordering rationale
- Critical research flags
- Confidence assessment
- Gaps to address

**Use for:** Project planning, team kickoff, executive briefs

---

### 2. **STACK.md** — Technology Stack Recommendations

**Comprehensive technology audit** for all layers of the platform.

Covers:
- Core quantitative libraries (QuantLib, NumPy, SciPy, Numba)
- Risk and credit modeling (Statsmodels, scikit-learn)
- Monte Carlo / distributed compute (Ray)
- Cash flow modeling (custom + QuantLib patterns)
- Regulatory engines (custom CECL, Basel III)
- Database layer (PostgreSQL, psycopg3, SQLAlchemy optional)
- Frontend (React 18, Plotly.js, TanStack Query/Table)
- Infrastructure (AWS ECS Fargate, RDS Aurora, Terraform)

Each recommendation includes:
- Specific version
- Rationale (why this choice)
- Alternatives considered and why rejected
- Confidence level (HIGH/MEDIUM/LOW)

**Dependency map** showing load order and integration points.

**Use for:** Architecture decisions, engineering specs, vendor evaluations

---

### 3. **FEATURES.md** — Feature Landscape

**Map of what to build** across phases.

Categorized as:
- **Table Stakes** — Features users expect (PV, DV01, scenarios, drill-down)
- **Differentiators** — Competitive advantages (CECL, performance attribution, macro linking)
- **Anti-Features** — What NOT to build (real-time streaming, ML prepayment, white-label SaaS)

For each feature:
- Why it's expected/valued
- Complexity (Low/Med/High)
- Phase (1-5)

**Feature dependencies graph** shows what must be built in what order.

**User stories by persona** (risk manager, trader, compliance officer).

**MVP recommendation** prioritizes core features Phase 1.

**Use for:** Product requirements, scope management, sprint planning

---

### 4. **ARCHITECTURE.md** — System Architecture & Patterns

**Detailed technical blueprint** for the distributed system.

Sections:
- **Recommended architecture diagram** (services, compute, database, cache)
- **Component boundaries** — Which service owns what data
- **Data flow** — End-to-end run execution
- **Compute pipeline** — Multi-stage processing (pricing → scenarios → cashflows → risk → regulatory)
- **Deployment model** — AWS ECS Fargate, RDS Aurora, CloudWatch
- **Database schema** — Tables for portfolio, positions, scenarios, results, regulatory metrics
- **Patterns to follow** — 7 proven architectural patterns
  1. Immutable snapshots with content hashing
  2. Lease-based task queue (FOR UPDATE SKIP LOCKED)
  3. Measure-based computation (request-time filtering)
  4. Scenario application via copy-and-modify
  5. UPSERT for idempotency
  6. Service as query layer (async composition)
  7. Hash-bucket sharding for parallelization
- **Anti-patterns to avoid** — 8 common mistakes
- **Scalability considerations** — How system performs at 100, 10K, 1M positions
- **Component build order** — Dependency graph for implementation sequence

**Use for:** System design, implementation planning, code reviews

---

### 5. **PITFALLS.md** — Domain Pitfalls & Risk Mitigation

**Comprehensive catalog of things that go wrong** in financial risk platforms.

**Critical pitfalls (HIGH risk):**
1. Premature microservice decomposition
2. JSONB schema without structure discipline
3. Curve construction data lineage loss
4. Numerical stability ignored
5. Pricer API evolution without backward compatibility
6. Distributed worker state explosion
7. Insufficient test coverage
8. Cash flow modeling complexity
9. Missing data consistency boundaries
10. Performance degradation at scale
11. Regulatory compliance bolt-on too late
12. Microservice observability blindness

Each includes:
- What goes wrong
- Why it happens
- Consequences
- Prevention strategy
- Detection signals
- Example code (when applicable)

**Domain-specific warnings:**
- Loan portfolio pitfalls (amortization assumptions, loss recovery)
- Fixed income pitfalls (spread curve construction, day-count errors, negative rates)

**Architecture anti-patterns** — 5 common missteps

**Scaling milestones & readiness checklist** — What to verify at 100, 500, 1K, 5K+ positions

**Remediation priorities by cost** — What to fix in each phase

**Use for:** Risk management, QA strategy, team education, decision gates

---

### 6. **ROADMAP_SYNTHESIS.md** — Actionable Roadmap

**Integration of all research into concrete phase plan.**

Sections:
- Quick executive summary
- What you have (MVP audit)
- What you need (gap analysis)
- **Detailed phase structure (1-5)**
  - Goals, deliverables, timeline, success criteria for each phase
  - What NOT to do in each phase
  - Why this order
  - Risks and mitigation
- Recommended stack (final summary)
- Critical dependencies & blockers
- Risk assessment (HIGH/MEDIUM factors and mitigations)
- Success criteria by phase
- Team structure & effort allocation
- Decision gates (go/no-go criteria)
- Open questions to resolve before starting

**Use for:** Project roadmap, phase planning, sprint commitment

---

## How to Use This Research

### For Project Leads
1. Read **SUMMARY.md** (overview)
2. Skim **ROADMAP_SYNTHESIS.md** (phase breakdown)
3. Reference **PITFALLS.md** (risk mitigation strategy)

### For Architects
1. Study **ARCHITECTURE.md** (system design)
2. Review **STACK.md** (technology decisions)
3. Validate patterns in **PITFALLS.md** (anti-patterns to avoid)

### For Engineering Teams
1. Reference **STACK.md** (library versions, installation)
2. Follow **ARCHITECTURE.md** (component boundaries, build order)
3. Test against **PITFALLS.md** (edge cases, performance targets)

### For Quant Engineers
1. Review **FEATURES.md** (instrument scope)
2. Study **ARCHITECTURE.md** (compute pipeline)
3. Check **PITFALLS.md** (numerical stability, pricer edge cases)

### For QA/Testing
1. Plan based on **ROADMAP_SYNTHESIS.md** (phase success criteria)
2. Design tests against **PITFALLS.md** (edge cases, scaling limits)
3. Validate using **FEATURES.md** (golden test data requirements)

---

## Key Decisions Made

### Architecture
✓ **Distributed worker pattern** — Proven in MVP, scale via parallelization
✓ **Service-as-query-layer** — No RPC during compute, composition at query time
✓ **Immutable snapshots** — For auditability, reproducibility, disaster recovery
✓ **PostgreSQL queue** — FOR UPDATE SKIP LOCKED sufficient to 10K tasks/sec

### Technology
✓ **QuantLib 1.34** — Industry standard, institutional-grade pricing
✓ **FastAPI** — Async, production-ready, proven
✓ **PostgreSQL Aurora** — Managed, replicas, RDS Proxy for connection pooling
✓ **ECS Fargate** — Serverless, auto-scaling, CloudWatch integration
✓ **React 18 + Plotly** — Modern frontend, financial visualizations

### Scope
✓ **Phase 1 focus** — Pricers, not services. Get compute production-ready first.
✓ **Skip Phase 1 Phase 2 parallelization** — Services can be built concurrently once database ready
✓ **Defer Monte Carlo to Phase 4** — Batch scenarios sufficient for Phases 1-3
✓ **Defer regulatory reporting to Phase 5** — CECL framework Phase 3, reporting Phase 5

### Risks Mitigated
✓ **Premature optimization** — Get correctness Phase 1, optimize Phase 4
✓ **Data consistency** — Immutable snapshots + position locking
✓ **Microservice coupling** — Clear boundaries, database-driven composition
✓ **Performance at scale** — Profile early (Phase 1 end), test at 1K positions before Phase 2

---

## Confidence Summary

| Area | Level | Notes |
|------|-------|-------|
| **Architecture** | HIGH | MVP patterns proven. No architectural rewrites needed. |
| **Core technology stack** | HIGH | QuantLib, FastAPI, PostgreSQL are industry standards. |
| **Database design** | MEDIUM-HIGH | Schema designed, refinements expected Phase 1. |
| **Phase structure** | MEDIUM-HIGH | Order validated by dependencies, but effort estimates ±20%. |
| **Institutional pricing** | MEDIUM | Callable/putable bond formulas known, but edge cases need testing. |
| **ABS/MBS prepayment** | MEDIUM | Conceptually sound, but complexity uncertain. Recommend spike. |
| **Structured products** | LOW | Scope unclear. Requires separate feasibility study. |
| **CECL compliance** | MEDIUM | Framework ready, regulatory details need team input. |
| **Scaling to 1M positions** | MEDIUM | Theoretically sound, requires load testing to validate. |

---

## Next Steps

1. **Week 1:** Resolve open questions
   - [ ] Quant team: Estimate ABS/MBS prepayment complexity
   - [ ] Quant team: Estimate structured product Monte Carlo scope
   - [ ] Compliance: Clarify CECL regulatory framework (ASC 326 vs IFRS 9)
   - [ ] Data team: Obtain golden test data (Bloomberg prices, historical prepayment curves)

2. **Week 2:** Team planning
   - [ ] Kickoff meeting: Review roadmap, commit to Phase 1
   - [ ] Assign roles: Quant/backend/frontend/ops leads
   - [ ] Setup infrastructure: AWS account, ECR, Terraform skeleton
   - [ ] Setup development: Branch strategy, testing framework

3. **Week 3:** Phase 1 sprint planning
   - [ ] Sprint 1: Database schema + QuantLib integration (Week 1)
   - [ ] Sprint 2: Pricers + golden tests (Week 2)
   - [ ] Sprint 3: Cash flow + risk metrics + CECL scaffold (Week 3)
   - [ ] Sprint 4: Performance testing + edge case fixes (Week 4)

---

## Document Quality Checklist

- [x] All domains investigated (stack, features, architecture, pitfalls)
- [x] Negative claims verified with context
- [x] Multiple sources for critical claims
- [x] URLs/sources provided for authoritative references
- [x] Confidence levels assigned honestly
- [x] "What might we have missed?" review completed
- [x] Trade-offs explained (not just feature lists)
- [x] Anti-patterns documented (not just best practices)
- [x] Phase dependencies validated
- [x] Success criteria measurable and realistic

---

## References

**Existing codebase:**
- CLAUDE.md — Project overview
- services/README_SERVICES.md — Service architecture
- sql/001_mvp_core.sql — Database schema
- .claude/docs/architectural_patterns.md — Pattern documentation

**External sources:**
- QuantLib documentation: https://www.quantlib.org
- FastAPI: https://fastapi.tiangolo.com
- PostgreSQL: https://www.postgresql.org
- AWS ECS: https://docs.aws.amazon.com/ecs
- React 18: https://react.dev
- Terraform AWS provider: https://registry.terraform.io/providers/hashicorp/aws

**Domain knowledge:**
- Fixed income analytics (Fabozzi, Hull)
- Loan portfolio risk (Altman, Kealhofer)
- Regulatory frameworks (Basel III, CECL, IFRS 9)
- Financial engineering patterns (industry best practices)

---

**Research completed:** 2026-02-11
**Status:** READY FOR PHASE PLANNING
**Next phase:** Architecture review + team kickoff
