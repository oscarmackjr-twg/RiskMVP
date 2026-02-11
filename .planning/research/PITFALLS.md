# Pitfalls Research: Portfolio Analytics Platform

**Research Date:** 2026-02-11
**Domain:** Institutional fixed income / loan portfolio analytics
**Platform Context:** Scaling from 3-service MVP to 10+ microservices with institutional pricers, cash flow engine, risk/Monte Carlo engines
**Confidence:** MEDIUM-HIGH (based on domain patterns in distributed financial systems)

---

## Critical Pitfalls

### 1. Premature Microservice Decomposition

**Risk Level:** HIGH
**Description:** Splitting services at wrong boundaries too early creates chatty inter-service dependencies, cascading failures, and distributed transaction nightmares. Common mistakes: separating pricer from curve builder, isolating regulatory engine from position context, fragmenting cash flow computation across services.

**Warning Signs:**
- Services communicating >10 times per single run execution
- Circular dependencies between services or event chains with 4+ hops
- Frequent "but we need position context to price it" conversations
- Database transactions requiring locks across multiple service databases

**Prevention:**
- Keep pricing domain (curves, pricers, scenarios) in single service until >200K positions
- Bundle related computations (cash flows + accrual logic + settlement logic) together
- Use service boundaries based on independent ownership and deployment, not code organization
- Model service calls per position: if calling external service per position, you've decomposed wrong

**Phase Impact:** Architecture phase (before code explosion); fixing mid-project costs 3-4x

**Example Anti-Pattern:**
```
Bad: Position Service -> Curve Service -> FX Service -> Pricer Service (4 hops per position)
Good: Risk Service handles curves, FX spots, and calls integrated pricing engine
```

---

### 2. JSONB Schema Without Structure Discipline

**Risk Level:** HIGH
**Description:** Treating PostgreSQL JSONB columns as schema-free leads to silent data corruption, impossible migrations, and midnight incidents where some positions are missing fields. Without strict validation, pricer crashes on missing `accrual_frequency` or unexpected `pricing_method` variants.

**Warning Signs:**
- Uncertainty about what fields exist in JSONB columns ("maybe it has accrued_interest?")
- Pricer code with defensive `.get()` chains 15 levels deep
- Data migrations requiring manual JSON re-structure
- "Works in staging, fails in production" because staging data is incomplete

**Prevention:**
- Define strict JSON schemas in `contracts/` directory with JSON Schema validation
- Validate on write: pricer must reject positions missing required fields
- Use Python dataclasses/Pydantic models as source of truth, convert to JSONB for storage
- Run quarterly JSONB audits: query outlier documents, document actual schema variants
- Test pricer with minimal vs. complete position documents

**Phase Impact:** Design (schema phase); expensive to fix after 1M positions loaded

**Example Implementation:**
```python
# BAD: silent partial object handling
def price_position(pos):
    coupon = pos.get("coupon")  # None if missing
    frequency = pos.get("frequency", 2)  # Guess!
    return coupon * frequency

# GOOD: explicit validation
from pydantic import BaseModel, Field

class FixedBondPosition(BaseModel):
    coupon: float = Field(..., description="Annual coupon rate")
    frequency: int = Field(default=2, description="Coupon frequency per year")

def price_position(pos_dict):
    pos = FixedBondPosition(**pos_dict)  # Raises ValueError if invalid
    return pos.coupon * pos.frequency
```

---

### 3. Curve Construction Data Lineage Loss

**Risk Level:** HIGH
**Description:** Building curves without recording source data, timestamps, and adjustment methodology creates non-reproducible results. Six months later: "Why does the 5Y rate differ by 3bps from that trade reconciliation?"

**Warning Signs:**
- Curve snapshots without metadata (which Bloomberg terminals, which spreads applied, which interpolation method)
- Cannot reproduce previous day's curve
- Pricer results vary without position changes
- Regulatory queries fail: "Show me the market inputs for this computation"

**Prevention:**
- Capture curve metadata: {source_system, timestamp, version, interpolation_method, adjustment_rules}
- Store both raw points and interpolated rates for audit trail
- Version curve snapshots in PostgreSQL as immutable records with creation timestamp
- Unit tests verify curve stability: same input always produces same output
- Log every curve-building decision: which spreads, which adjustments, interpolation parameters

**Phase Impact:** Regulatory/audit phase (becomes critical at year-end close)

**Example Schema:**
```python
class CurveSnapshot(BaseModel):
    snapshot_id: str
    curve_date: date
    curve_type: str  # "TREASURY", "OIS", "LIBOR_3M"
    raw_points: List[CurvePoint]
    interpolation_method: str  # "LINEAR", "CUBIC_SPLINE"
    adjustments_applied: List[str]
    built_by: str
    built_at: datetime
    built_from: str  # e.g., "BLOOMBERG_TERMINAL_3"
```

---

### 4. Numerical Stability Ignored Until Production

**Risk Level:** HIGH
**Description:** Floating-point arithmetic, logarithmic interpolation, Newton-Raphson on edge cases (zero coupon bonds, negative rates, credit spread compression) creates silent errors, small divergences that amplify across portfolios of thousands.

**Warning Signs:**
- Pricer works for 95% of positions, silently NaN or crashes on edge cases
- Zero-coupon bonds priced differently from 0.1bp coupon bonds
- Negative rate scenarios produce garbage
- Portfolio P&L rolls by 0.5% for no reason

**Prevention:**
- Test pricers exhaustively on edge cases: 0% coupon, negative rates, 30yr maturity, tiny spreads
- Use stable numerical algorithms: avoid direct subtraction of nearly-equal values
- Log intermediate calculations in debug mode (discount factors, accrued interest, yield iterations)
- Compare pricer output to Bloomberg/Murex as golden source for sample positions
- Use higher precision (Decimal or numpy float64) for intermediate calculations, round at end
- Implement bisection + Newton-Raphson hybrid for yield calculations (more stable than pure Newton)

**Phase Impact:** Pricer development (prevents months of debugging later)

**Example Pitfall:**
```python
# BAD: Naive present value for near-par bonds loses precision
pv = sum(cf / (1 + y) ** t for cf, t in cash_flows)  # Fails if y ~ -0.02

# GOOD: Log-discount stable method
log_df = -t * log(1 + y)  # Handles small/negative yields better
pv = sum(cf * exp(log_df) for cf, t in cash_flows)
```

---

### 5. Pricer API Evolution Without Backward Compatibility

**Risk Level:** HIGH
**Description:** Changing pricer return format (adding fields, renaming outputs, changing measure definitions) forces redeployment of workers and loses ability to compare results across runs. Historical pricing data becomes incompatible with new code.

**Warning Signs:**
- Can't run old runs with new code
- Pricer refactors require entire system redeployment
- Test data from last quarter no longer matches
- Regulatory reporting queries fail on old runs

**Prevention:**
- Freeze pricer output schema: add new fields, never remove or rename
- Use versioned pricer APIs: `price_position_v2()` alongside `price_position_v1()`
- Store pricer version in each result record
- Test backward compatibility: old results must deserialize correctly
- Document pricer contract in JSON Schema; breaking changes require major version bump

**Phase Impact:** Early pricer design (prevents breaking changes mid-system life)

**Example Practice:**
```python
# Pricer API versioning
def price_fixed_bond_v1(position, curves, scenario):
    """Original API - frozen."""
    return {"pv": ..., "dv01": ...}

def price_fixed_bond_v2(position, curves, scenario):
    """Enhanced API - adds accrued interest tracking."""
    result = price_fixed_bond_v1(position, curves, scenario)
    result["accrued_interest"] = ...
    result["__version"] = "v2"
    return result
```

---

### 6. Distributed Worker State Explosion Without Lease Management

**Risk Level:** MEDIUM-HIGH
**Description:** Workers claim tasks, disconnect or pause mid-execution, abandon work. No mature lease/heartbeat mechanism = duplicate execution, orphaned tasks, stuck runs, race conditions in database updates. Scaling from 10 to 100 workers amplifies this.

**Warning Signs:**
- Same position priced twice with different results in same run
- Tasks stuck in "CLAIMED" state with no worker touching them
- Occasional result duplication when production issues cause worker restarts
- Database deadlocks during concurrent result writes

**Prevention:**
- Implement robust task leasing: claim requires heartbeat refresh every N seconds
- Auto-release stale leases (>30 seconds old) back to queue
- Idempotent result writes: store task execution hash, detect re-execution
- Database constraints: (run_id, task_id, execution_hash) unique constraint
- Monitor unclaimed vs. claimed task counts; alert if > 10% stuck
- Graceful shutdown: workers drain claimed tasks before exit, don't just die

**Phase Impact:** Scaling phase (appears at 10-50 workers concurrent)

**Example Patterns:**
```python
# Task lease table schema
CREATE TABLE task_leases (
    task_id UUID PRIMARY KEY,
    worker_id TEXT,
    claimed_at TIMESTAMP,
    heartbeat_at TIMESTAMP,
    expires_at TIMESTAMP,
    UNIQUE(task_id, worker_id)  -- prevent multiple leases
);

# Idempotent result write
INSERT INTO position_results (run_id, task_id, position_id, result, execution_hash)
VALUES (...)
ON CONFLICT (run_id, task_id, position_id)
DO UPDATE SET result = EXCLUDED.result
WHERE execution_hash != EXCLUDED.execution_hash;  -- detect re-execution
```

---

### 7. Insufficient Test Coverage for Pricer Edge Cases

**Risk Level:** MEDIUM-HIGH
**Description:** Pricers tested only on "happy path" data from demo portfolio. Real portfolio has: zero-coupon bonds, callable structures, exotic features, illiquid spreads, stressed scenarios with negative rates. Missing tests = silent crashes or garbage results in production.

**Warning Signs:**
- Golden tests only cover 5-10 position types
- No tests for edge cases: 0% coupon, 50yr maturity, distressed spread
- "We'll find issues in UAT" attitude
- Pricer crashes on 0.1% of positions, requires manual triage

**Prevention:**
- Golden test suite: 100+ realistic positions with known Bloomberg prices
- Edge case matrix: create positions with every combination of (coupon: [0%, 5%], maturity: [1yr, 50yr], spread: [50bp, 500bp])
- Scenario tests: price identical position across BASE, RATES_UP_100BP, SPREAD_DOWN_200BP - should see expected sensitivities
- Property-based tests: for any coupon C and maturity T, PV should decrease monotonically with rate increase
- Stress tests: price portfolio under extreme scenarios, check for NaN/Infinity
- Compare to Bloomberg API or Murex for sample positions

**Phase Impact:** Pricer development; should be done before release to production

**Example Test Structure:**
```python
# Golden test: known position with Bloomberg price
@pytest.mark.golden
def test_fixed_bond_golden_us_treasury_5y():
    pos = FixedBondPosition(cusip="XXXX", coupon=4.5, maturity_years=5)
    curve = load_test_curve("treasury_2025_01_15")
    pv = price_fixed_bond(pos, curve, Scenario.BASE)
    assert abs(pv - 102.34) < 0.01  # Bloomberg price 102.34

# Edge case tests
@pytest.mark.edge_cases
@pytest.mark.parametrize("coupon,maturity", [
    (0.0, 1), (0.0, 30), (0.1, 50), (10.0, 1)
])
def test_fixed_bond_edge_cases(coupon, maturity):
    pos = FixedBondPosition(coupon=coupon, maturity_years=maturity)
    pv = price_fixed_bond(pos, STRESS_CURVE, Scenario.BASE)
    assert not isnan(pv) and not isinf(pv), f"NaN/Inf for {coupon}% {maturity}yr"

    # Monotonicity: higher rates = lower PV
    pv_base = pv
    pv_high_rate = price_fixed_bond(pos, STRESS_CURVE_UP_100BP, Scenario.BASE)
    assert pv_high_rate < pv_base, "PV should decrease with rate increase"
```

---

### 8. Cash Flow Modeling Complexity Underestimation

**Risk Level:** MEDIUM-HIGH
**Description:** Underestimating cash flow engine complexity: day count conventions (ACT/ACT, ACT/360, 30/360), business day adjustments, stub periods, accrual schedules, callable features, default assumptions. Building in pricer leads to duplicated logic across pricers and crashes on edge case features.

**Warning Signs:**
- Accrued interest calculations differ between positions
- Same cash flow pattern computed differently in pricer vs. analytics module
- "But the loan has a call feature and weird coupon frequency" leads to weeks of rework
- P&L reconciliation off by accrual amount

**Prevention:**
- Build centralized cash flow engine: single source of truth for all cash flow generation
- Explicit day count convention handling: ACT/ACT, ACT/360, 30/360 as pluggable components
- Test cash flow engine exhaustively: every instrument type, every day count, every stub period
- Document assumptions: what happens on weekends, holidays, maturity dates, missing schedules
- Use QuantLib patterns: schedule builder, day counter, calendar aware

**Phase Impact:** Architecture phase (building now prevents months of debugging)

**Example Architecture:**
```python
# Centralized cash flow engine
class CashFlowSchedule:
    """Generate cash flows for any instrument."""
    def __init__(self, position: InstrumentPosition):
        self.position = position
        self.day_counter = DayCounter.get(position.day_count_convention)
        self.calendar = Calendar.get(position.calendar)
        self.schedule = self._build_schedule()

    def generate_cash_flows(self) -> List[CashFlow]:
        """Returns all future cash flows with accurate dates and amounts."""
        flows = []
        for period in self.schedule:
            date = self.calendar.adjust(period.date)
            amount = self._calculate_coupon(period)
            accrual_days = self.day_counter.days(period.start, period.end)
            flows.append(CashFlow(date, amount, accrual_days))
        return flows
```

---

### 9. Missing Data Consistency Boundaries in Distributed Architecture

**Risk Level:** MEDIUM-HIGH
**Description:** Without careful consistency models, positions change mid-run, curves update during pricing, FX rates shift between runs. Results become non-reproducible. Worse: result aggregation gets partial old/new data, top-level portfolio P&L doesn't match position-level sum.

**Warning Signs:**
- Occasional portfolio P&L doesn't match sum of position results
- Re-running same run yields different results
- Position updated after partial pricing, results inconsistent
- Time-traveling issues: "market data timestamp T but position timestamp T-1"

**Prevention:**
- Immutable market data snapshots: curves and FX rates versioned with snapshot_id
- Position lock during run: no updates allowed after run_id assigned
- Snapshot consistency checks: market_data timestamp <= run_created_at <= first_price_timestamp
- Use PostgreSQL BEGIN TRANSACTION READ COMMITTED for all run operations
- Document consistency model: snapshot isolation, eventual consistency, or strong consistency
- Implement run state machine: PENDING -> PREPARED -> EXECUTING -> AGGREGATING -> COMPLETE (no updates except within state)

**Phase Impact:** Design phase (fixing mid-scale is painful)

**Example Consistency Layer:**
```python
# Market data immutability
class MarketDataSnapshot:
    snapshot_id: str
    timestamp: datetime
    curves: Dict[str, Curve]  # Immutable after creation
    fx_spots: Dict[str, float]  # Immutable after creation

# Position locking
class PortfolioRun:
    run_id: str
    snapshot_id: str  # Points to immutable snapshot
    state: RunState  # PENDING, PREPARED, EXECUTING, COMPLETE
    locked_at: datetime

    def can_update_position(self, position_id) -> bool:
        return self.state == RunState.PENDING  # Only before execution

# Run state transitions
# PENDING -> PREPARED: Market data finalized, positions locked
# PREPARED -> EXECUTING: Tasks claimed by workers
# EXECUTING -> AGGREGATING: All tasks complete
# AGGREGATING -> COMPLETE: Results aggregated, consistent
```

---

### 10. Performance Degradation at Scale (100s to 1000s Positions)

**Risk Level:** MEDIUM-HIGH
**Description:** MVP performs fine with 100 positions. At 1,000 positions: pricing takes 2 hours instead of 2 minutes. Bottlenecks hidden: serial curve interpolation, N^2 aggregation queries, uncached FX spot lookups, task scheduling overhead.

**Warning Signs:**
- Pricing time increases superlinearly with position count (100 pos: 1min, 1000 pos: 2hrs instead of 10min)
- Database CPU 100% during result aggregation
- Worker utilization drops as positions increase (task queue management overhead)
- Curve interpolation becomes bottleneck
- Result aggregation queries timeout

**Prevention:**
- Profile early and often: measure timing at 10, 100, 1000 positions
- Batch curve interpolation: cache point lookups, vectorize discount factor computation
- Pre-aggregate results: store intermediate aggregations, not final query of 1M rows
- Partition tasks by hash bucket: distribute price computation across workers
- Use database indexes strategically: (run_id, scenario_id) for result queries, (curve_id, tenor) for curve lookups
- Implement result caching: if portfolio/scenario unchanged, reuse prior results
- Async result writes: workers write results in batches, not per-position
- Monitor and log per-position pricing time; alert if mean > 100ms or p99 > 1s

**Phase Impact:** Scaling phase (should test at 1000 position scale before production)

**Example Optimization:**
```python
# BAD: Query each position's results separately
def get_run_results(run_id):
    results = []
    for position_id in get_positions(run_id):
        result = db.query(f"SELECT * FROM results WHERE run_id={run_id} AND position_id={position_id}")
        results.append(result)
    return aggregate(results)

# GOOD: Batch query with aggregation
def get_run_results_optimized(run_id):
    # Single query with aggregation
    results = db.query(f"""
        SELECT position_id, scenario_id, SUM(pv) as total_pv, SUM(dv01) as total_dv01
        FROM results
        WHERE run_id = %s
        GROUP BY position_id, scenario_id
    """, (run_id,))
    return results
```

---

### 11. Regulatory Compliance Bolt-On Too Late

**Risk Level:** MEDIUM-HIGH
**Description:** Building pricing/risk engines without regulatory controls in mind. Then, at year-end close: "We need FRTB, SEC, Basel III, stress testing, model validation." Retrofitting costs 3-4x vs. building in from start. Data lineage, audit trails, model governance become afterthoughts.

**Warning Signs:**
- No audit trail: who priced what, when, with which models
- Model validation not integrated: pricers deployed without formal validation
- Risk limit tracking manual/external
- Stress test scenarios not reproducible
- Regulatory reports cobbled together from multiple systems

**Prevention:**
- From day 1: capture pricer version, curve version, input timestamp in results
- Implement audit logging: every market data upload, every run execution, every result change
- Build model governance: pricers tagged with validation status, validators assigned
- Regulatory scenario library: pre-defined stress scenarios, versions controlled
- Risk limit framework: positions tagged with limits, alerts on breach
- Reconciliation support: position, market data, results all joinable for audit
- Stress testing integrated: can run portfolio under historical stress scenarios

**Phase Impact:** Architecture/design phase (impossible to bolt-on)

**Example Audit Trail:**
```python
class PricingAuditLog:
    """Every pricing event captured for regulatory queries."""
    run_id: str
    position_id: str
    pricer_model: str
    pricer_version: str
    curve_snapshot_id: str
    scenario_id: str
    execution_timestamp: datetime
    executed_by: str  # worker-1, automated, etc.
    result_pv: float
    result_hash: str  # For data integrity verification
    approved_for_reporting: bool
    approval_timestamp: Optional[datetime]
```

---

### 12. Microservice Observability Blindness

**Risk Level:** MEDIUM
**Description:** With 10 services running across multiple AWS instances, you can't see what's happening. "Portfolio run took 5 hours, why?" scattered across logs in 5 services, no correlation IDs, no timing breakdown. Scaling becomes guesswork.

**Warning Signs:**
- Can't trace a single run across services
- Performance issues discovered in production (UAT didn't replicate)
- Debugging requires manual log tailing across services
- "Service X is slow" but no metrics to prove it
- Alert on "service down" without knowing why or for how long

**Prevention:**
- Implement structured logging from day 1: JSON logs with correlation_id, service_name, component
- OpenTelemetry tracing: every run carries trace_id, measure latency per service boundary
- Metrics for business logic: time to price N positions, time to aggregate results, curve interpolation latency
- Centralized log aggregation: ELK/Datadog, searchable by correlation_id
- Dashboard: run execution timeline, service latencies, worker utilization
- Alert thresholds: if pricing takes >10 minutes for 1000 positions, alert

**Phase Impact:** Early infrastructure setup (hard to retrofit)

**Example Logging Pattern:**
```python
# Structured logging with correlation_id
import logging
import json
from uuid import uuid4

class StructuredLogger:
    def __init__(self, service_name):
        self.service_name = service_name
        self.correlation_id = None

    def log_event(self, event_type, duration_ms=None, **context):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "correlation_id": self.correlation_id,
            "event": event_type,
            "duration_ms": duration_ms,
            **context
        }
        print(json.dumps(entry))
```

---

## Domain-Specific Warnings

### Loan Portfolio Specific Pitfalls

1. **Amortization Schedule Assumption Fragility**
   - Hard-coded assumptions about prepayment speeds (CPR), maturity dates, step-down schedules break on real portfolios
   - Different pools have different prepayment behaviors; generic model fails
   - **Prevention:** Make assumptions explicit and configurable; store actual schedule in position data, not assumptions

2. **Missing Loss Recovery & Recovery Rates**
   - Pricing loans without recovery rate assumptions underestimates risk
   - High-yield loans priced at par when distressed borrower = major mispricing
   - **Prevention:** Incorporate recovery rates in loan pricer; link to credit spreads and default probability curves

3. **Collateral & Cross-Default Not Modeled**
   - Syndicated loans have complex guarantees, cross-defaults, subordination
   - Missing these relationships in risk engine underestimates correlated defaults
   - **Prevention:** Store collateral hierarchy and cross-default links; model portfolio concentration in collateral

### Fixed Income Specific Pitfalls

1. **Credit Spread Curve Construction**
   - Credit spreads are sparse (few liquid bonds per issuer), interpolation choices matter
   - Assuming linear spread interpolation breaks on distressed credits
   - **Prevention:** Use conservative (flat) spread extrapolation; flag illiquid tenors; maintain bid-ask width separately

2. **Day Count Convention Errors**
   - ACT/ACT vs. 30/360 can swing P&L by 10+ bps on longer bonds
   - Mismatched conventions between position data and pricer = reconciliation nightmare
   - **Prevention:** Validate day count convention in position; test pricer against Bloomberg for sample bonds

3. **Negative Rate Handling**
   - Pricers break on negative rates (logs of negative numbers, discount factor formula breaks)
   - Crisis scenarios require negative rate support
   - **Prevention:** Test pricers with -2% to +5% rate scenarios; use numerically stable implementations

---

## Architecture Anti-Patterns

### Anti-Pattern 1: "Service Per Data Entity"
**Why It Fails:** Position Service, Curve Service, Scenario Service, Result Service = 8+ inter-service calls per position
**Better Approach:** Service per *domain process* (Pricing Service, Risk Service, Reporting Service)

### Anti-Pattern 2: "Cache Everything"
**Why It Fails:** Curves updated, cached old curve used, results wrong. No cache invalidation strategy = stale data in production
**Better Approach:** Cache strategically (scenarios, FX conversion tables); never cache curves, positions, or results. Use time-based expiry with validation.

### Anti-Pattern 3: "Polyglot Persistence Everywhere"
**Why It Fails:** PostgreSQL for positions, MongoDB for results, Redis for cache, S3 for logs = nightmare reconciliation, backup/restore chaos
**Better Approach:** Single PostgreSQL (JSONB for flexibility), separate S3 for archived runs. Polyglot only if you have >1000 positions AND specifically validated each store.

### Anti-Pattern 4: "Deploy Microservices, Get Microservices Problems Day 1"
**Why It Fails:** Distributed testing is hard; race conditions hidden until production with 100 concurrent workers
**Better Approach:** Keep pricing engine monolithic until 10K+ positions; decompose services based on scaling requirements, not team structure.

### Anti-Pattern 5: "Tests Pass, Ship It"
**Why It Fails:** Golden tests pass on 100 demo positions; production portfolio has 5K positions with exotic features
**Better Approach:** Scale testing to 1000+ positions; test with actual portfolio data (anonymized); stress test edge cases.

---

## Scaling Milestones & Readiness Checklist

### 100 Positions (MVP)
- [ ] Single pricing service
- [ ] Golden test suite
- [ ] Pricer works on demo portfolio

### 500 Positions (Beta)
- [ ] Pricer tested on edge cases (0% coupon, negative rates, long dated)
- [ ] Task leasing implemented
- [ ] Database indexes on run_id, scenario_id
- [ ] Performance profiling: mean <100ms/position

### 1,000 Positions (Production)
- [ ] Batched result writes (avoid 1M individual INSERTs)
- [ ] Aggregation queries optimized
- [ ] Structured logging with correlation IDs
- [ ] Scenario tests pass (verify rate sensitivities make sense)
- [ ] Risk limits framework in place

### 5,000+ Positions (Institutional Scale)
- [ ] Distributed worker pool (10+) with lease management tested
- [ ] Curve caching with validation
- [ ] Result partitioning/archiving strategy
- [ ] Regulatory audit trail complete
- [ ] Monte Carlo engine separate from pricing (don't block pricing on MC)

---

## Remediation Priorities by Cost

### Phase 1: Foundation (Before 1K positions)
1. Implement cash flow engine (single source of truth)
2. Golden test suite (100+ realistic positions)
3. Curve immutability + metadata capture
4. Task lease management with idempotent writes

**Effort:** 4-6 weeks | **Cost to fix later:** 100x

### Phase 2: Scale (At 1K positions)
1. Structured logging + correlation IDs
2. Database optimization: indexes, batch writes
3. Performance profiling framework
4. Regulatory audit trail

**Effort:** 3-4 weeks | **Cost to fix later:** 50x

### Phase 3: Institutional (At 5K+ positions)
1. Distributed worker hardening (10+ concurrent workers)
2. Monte Carlo engine isolation
3. Stress testing framework
4. Result caching strategy

**Effort:** 6-8 weeks | **Cost to fix later:** 20x

---

## Quick Risk Assessment Template

Use this for major decisions:

```
DECISION: [Add 10th microservice / Change JSONB schema / Refactor pricer]

PITFALL RISK ANALYSIS:
1. Microservice coupling: 1-10 scale _____
2. Data consistency: 1-10 scale _____
3. Testing complexity: 1-10 scale _____
4. Regulatory impact: 1-10 scale _____
5. Rollback difficulty: 1-10 scale _____

SCORE: ___/50
>35: STOP - De-risk first, then decide
25-34: CAUTION - Build extensive tests, staged rollout
<25: PROCEED - Standard approach

MITIGATIONS (if proceeding):
- [ ] Test at 1000 positions
- [ ] Audit trail complete
- [ ] Rollback plan documented
- [ ] SLA impact assessed
```

---

## References & Further Reading

- QuantLib documentation: Day count conventions, schedule builders
- PostgreSQL JSONB best practices: Schema validation, performance
- Microservice operational patterns: Circuit breakers, bulkheads, timeouts
- Institutional risk systems: Basel III, FRTB, stress testing frameworks
- Financial calculations: Numerical stability in bond math, yield curve construction

---

*Document prepared: 2026-02-11*
*Status: RESEARCH - Use as guide, validate against your specific context*
*Next: Architecture review session with team to prioritize Phase 1 mitigations*
