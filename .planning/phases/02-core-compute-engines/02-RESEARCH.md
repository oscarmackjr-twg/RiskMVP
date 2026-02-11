# Phase 2: Core Compute Engines - Research

**Researched:** 2026-02-11
**Domain:** Quantitative Finance - Institutional-Grade Pricing, Cashflow Modeling, Risk Analytics
**Confidence:** MEDIUM-HIGH

## Summary

Phase 2 builds institutional-grade valuation engines for fixed income instruments using QuantLib-Python as the primary quant library. QuantLib (version 1.41) is the industry standard for derivatives pricing and fixed income analytics, providing battle-tested implementations of callable/putable bond pricing, OAS/Z-spread calculations, curve bootstrapping, and Monte Carlo simulation. The library is written in C++ for performance and exposed to Python via SWIG bindings, enabling integration with NumPy/SciPy for numerical operations.

The architecture should leverage QuantLib's pricing engines (TreeCallableFixedRateBondEngine for embedded options, DiscountingBondEngine for vanilla bonds) while maintaining the existing function-based pricer registry pattern. Skeleton files already exist for all required components (pricers, cashflow modeling, risk analytics), indicating a structured approach to implementation. Key challenges include prepayment model calibration for ABS/MBS, structured product waterfall logic, and Monte Carlo path generation for scenario analysis.

Critical insight: QuantLib handles the complex mathematics (yield curve construction, option pricing, interest rate models) — don't hand-roll bootstrapping, interpolation, or tree-based valuation. The team should focus on instrument-specific logic, market data mapping, and measure calculation orchestration.

**Primary recommendation:** Use QuantLib 1.41 with Python 3.11+ for all pricing engines; integrate with existing registry pattern; leverage NumPy for vectorized operations on large portfolios; implement golden tests with verified Bloomberg/Markit reference prices.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| QuantLib-Python | 1.41+ | Fixed income pricing, curve construction, Monte Carlo | Industry standard used by major banks; battle-tested; comprehensive |
| NumPy | 1.26+ | Numerical arrays, linear algebra, vectorization | Foundation for all scientific Python; QuantLib integration |
| SciPy | 1.12+ | Optimization (curve bootstrapping), interpolation, solvers | Complements QuantLib; Brent solver for Z-spread, advanced interpolation |
| Python | 3.11+ | Runtime | QuantLib 1.41 supports Python 3.8+ via abi3; 3.11 performance improvements |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pandas | 2.2+ | Time series, cashflow schedules as DataFrames | Portfolio aggregation, cashflow output formatting |
| pytest | 8.3+ | Golden tests with reference pricing | Already in use; validation of all new pricers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| QuantLib | Custom pricer implementation | QuantLib is 500K+ LOC, 20+ years development; custom = years of work, high risk |
| QuantLib | Bloomberg API | Bloomberg licensing cost; vendor lock-in; not open source |
| QuantLib | Markit Analytics | Licensing; less transparent; Python integration limited |
| QuantLib-Python | QuantLib.jl (Julia) | Julia less mature in production systems; team Python expertise |

**Installation:**
```bash
pip install QuantLib==1.41
pip install numpy scipy pandas
```

**Note:** QuantLib 1.41 ships with pre-built wheels for Windows/Linux/macOS (Intel/ARM64), simplifying deployment.

## Architecture Patterns

### Recommended Project Structure
```
compute/
├── pricers/                 # Instrument-specific pricing (already exists)
│   ├── registry.py          # Function-based registry (existing pattern)
│   ├── base.py              # AbstractPricer (optional, for class-based)
│   ├── callable_bond.py     # TreeCallableFixedRateBondEngine wrapper
│   ├── putable_bond.py      # TreeCallableFixedRateBondEngine wrapper
│   ├── floating_rate.py     # FloatingRateBond with index curves
│   ├── abs_mbs.py           # Prepayment model integration
│   ├── structured.py        # Waterfall logic + base pricer
│   └── derivatives.py       # Hedge instrument pricer
├── quantlib/                # QuantLib adapter layer
│   ├── curve_builder.py     # PiecewiseYieldCurve wrappers
│   ├── interpolation.py     # LogCubic, Linear, CubicSpline
│   ├── day_count.py         # QuantLib DayCounter adapters (existing stub)
│   ├── calendar.py          # QuantLib Calendar adapters (existing stub)
│   └── scenarios.py         # Curve/spot shock application
├── cashflow/                # Cashflow schedule generation
│   ├── generator.py         # QuantLib Schedule + Leg builders
│   ├── prepayment.py        # PSA/CPR models (existing stubs)
│   ├── amortization.py      # Level pay, bullet, custom
│   ├── waterfall.py         # Structured product logic
│   └── arm_reset.py         # Index reset logic
├── risk/                    # Risk metric calculation
│   ├── market/              # Market risk
│   │   ├── duration.py      # BondFunctions.duration wrappers
│   │   ├── convexity.py     # BondFunctions.convexity
│   │   ├── dv01.py          # Curve bump/reprice
│   │   └── key_rate.py      # SpreadedLinearZeroInterpolatedTermStructure
│   ├── credit/              # Credit risk
│   │   ├── pd_model.py      # PD curve construction
│   │   └── expected_loss.py # PD * LGD * EAD
│   └── liquidity/           # Liquidity metrics
└── worker/
    └── worker.py            # Registry lookup + measure orchestration
```

### Pattern 1: QuantLib Pricer Wrapper Pattern
**What:** Wrap QuantLib instruments and pricing engines in function-based pricers for registry compatibility.

**When to use:** All new pricers (callable, putable, floating, ABS/MBS, derivatives).

**Example:**
```python
# Source: http://gouthamanbalaraman.com/blog/callable-bond-quantlib-python.html
import QuantLib as ql
from typing import Dict, List

def price_callable_bond(
    position: dict,
    instrument: dict,
    market_snapshot: dict,
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    """Price callable bond using TreeCallableFixedRateBondEngine."""

    # 1. Build QuantLib objects from instrument definition
    calc_date = ql.Date(...)  # from position/market date
    ql.Settings.instance().evaluationDate = calc_date

    # 2. Construct yield curve (from market_snapshot)
    day_count = ql.ActualActual(ql.ActualActual.Bond)
    ts = ql.FlatForward(calc_date, rate, day_count, ql.Compounded, ql.Semiannual)
    ts_handle = ql.YieldTermStructureHandle(ts)

    # 3. Define callability schedule
    call_schedule = ql.CallabilitySchedule()
    for call in instrument['call_schedule']:
        call_price = ql.BondPrice(call['price'], ql.BondPrice.Clean)
        call_date = ql.Date(...)
        call_schedule.append(ql.Callability(call_price, ql.Callability.Call, call_date))

    # 4. Create bond
    schedule = ql.MakeSchedule(...)
    bond = ql.CallableFixedRateBond(
        settlement_days=2,
        faceAmount=100.0,
        schedule=schedule,
        coupons=[instrument['coupon']],
        accrualDayCounter=day_count,
        paymentConvention=ql.ModifiedFollowing,
        redemption=100.0,
        issueDate=ql.Date(...),
        putCallSchedule=call_schedule
    )

    # 5. Set pricing engine (Hull-White + Tree)
    model = ql.HullWhite(ts_handle, a=0.03, sigma=0.12)
    engine = ql.TreeCallableFixedRateBondEngine(model, grid_points=40)
    bond.setPricingEngine(engine)

    # 6. Compute requested measures
    results = {}
    if 'PV' in measures:
        results['PV'] = bond.NPV()
    if 'CLEAN_PRICE' in measures:
        results['CLEAN_PRICE'] = bond.cleanPrice()
    if 'OAS' in measures:
        results['OAS'] = bond.OAS(...)  # requires market price

    return results
```

### Pattern 2: Yield Curve Construction Pattern
**What:** Bootstrap QuantLib PiecewiseYieldCurve from market instruments; cache in market_snapshot.

**When to use:** All pricers need discount curves; run orchestrator builds curves once per snapshot.

**Example:**
```python
# Source: https://quantlib-python-docs.readthedocs.io/en/latest/termstructures/yield.html
import QuantLib as ql

def build_discount_curve(market_data: dict, curve_id: str) -> ql.YieldTermStructure:
    """Bootstrap a discount curve from market instruments."""

    # 1. Helpers from market instruments
    helpers = []
    for instrument in market_data['instruments']:
        if instrument['type'] == 'DEPOSIT':
            helper = ql.DepositRateHelper(
                ql.QuoteHandle(ql.SimpleQuote(instrument['rate'])),
                ql.Period(instrument['tenor']),
                instrument['fixing_days'],
                ql.UnitedStates(ql.UnitedStates.GovernmentBond),
                ql.ModifiedFollowing,
                False,
                ql.Actual360()
            )
        elif instrument['type'] == 'SWAP':
            helper = ql.SwapRateHelper(...)
        helpers.append(helper)

    # 2. Bootstrap with interpolation method
    curve = ql.PiecewiseLogCubicDiscount(
        calc_date,
        helpers,
        ql.Actual360()
    )
    curve.enableExtrapolation()

    return curve
```

### Pattern 3: Spread Calculation with Brent Solver
**What:** Use SciPy Brent solver (or QuantLib's Brent) to find Z-spread/OAS by trial-and-error pricing.

**When to use:** Z-spread, OAS calculation for measures.

**Example:**
```python
# Source: https://dataninjago.com/2025/01/01/coding-towards-cfa-21-calculate-z-spread-with-quantlib/
import QuantLib as ql

def calculate_z_spread(bond, market_price, spot_curve, day_counter):
    """Calculate Z-spread using Brent solver."""

    def z_spread_func(z_spread):
        # Shift curve by trial spread
        spread_handle = ql.QuoteHandle(ql.SimpleQuote(z_spread))
        spreaded_curve = ql.ZeroSpreadedTermStructure(
            ql.YieldTermStructureHandle(spot_curve),
            spread_handle
        )
        bond.setPricingEngine(ql.DiscountingBondEngine(
            ql.YieldTermStructureHandle(spreaded_curve)
        ))
        return bond.NPV() - market_price

    # Solve for spread where NPV = market price
    solver = ql.Brent()
    solver.setMaxEvaluations(100)
    z_spread = solver.solve(
        z_spread_func,
        accuracy=1e-8,
        guess=0.01,
        min=-0.5,
        max=0.5
    )
    return z_spread
```

### Pattern 4: Prepayment Model Integration
**What:** Apply PSA/CPR prepayment models to amortization schedules.

**When to use:** ABS/MBS pricing (PRICE-04).

**Example:**
```python
# Source: Existing stub + PSA definition
def project_prepayments(schedule, psa_speed):
    """Apply PSA prepayment model to cashflows."""

    for month, cf in enumerate(schedule, start=1):
        # PSA ramps 0.2% → 6% over 30 months
        base_cpr = min(month * 0.002, 0.06)
        cpr = base_cpr * (psa_speed / 100.0)
        smm = 1.0 - (1.0 - cpr) ** (1.0 / 12.0)

        # Apply to remaining principal
        prepay_amount = cf['remaining_principal'] * smm
        cf['prepayment'] = prepay_amount
        cf['remaining_principal'] -= prepay_amount

    return schedule
```

### Pattern 5: Monte Carlo Path Generation
**What:** Use QuantLib's Hull-White or CIR models to generate interest rate paths for scenario analysis.

**When to use:** SCEN-03 Monte Carlo simulation.

**Example:**
```python
# Source: http://gouthamanbalaraman.com/blog/hull-white-simulation-quantlib-python.html
import QuantLib as ql

def generate_rate_paths(model, num_paths, time_horizon, time_steps):
    """Generate interest rate paths using Hull-White model."""

    # Setup random number generator
    rng = ql.GaussianRandomSequenceGenerator(
        ql.UniformRandomSequenceGenerator(
            time_steps, ql.UniformRandomGenerator(seed=42)
        )
    )
    seq = ql.GaussianPathGenerator(model, time_horizon, time_steps, rng, False)

    paths = []
    for i in range(num_paths):
        sample_path = seq.next()
        path = [sample_path.value().value(j) for j in range(time_steps + 1)]
        paths.append(path)

    return paths
```

### Anti-Patterns to Avoid

- **Hand-rolling curve bootstrapping:** QuantLib's PiecewiseYieldCurve handles instrument ordering, convergence, interpolation. Don't reimplement.
- **Ignoring evaluation date:** QuantLib is stateful via `Settings.instance().evaluationDate`. Must set before pricing; reset between positions in worker loop.
- **Direct date arithmetic for day counts:** Use QuantLib DayCounter classes (Actual360, Thirty360) — handles leap years, month-end, ISDA conventions correctly.
- **Synchronous Monte Carlo:** Use QuantLib's MultiPathGenerator with threading; avoid single-threaded loops for 10K+ paths.
- **Rebuilding instruments per measure:** Create QuantLib bond/swap once; call multiple methods (NPV, cleanPrice, duration) on same instance.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Yield curve bootstrapping | Custom Newton solver, manual ordering | QuantLib PiecewiseYieldCurve | Handles instrument priority, convergence, multiple interpolation methods; tested on billions of trades |
| Callable bond pricing | Binomial tree from scratch | QuantLib TreeCallableFixedRateBondEngine | Implements Hull-White calibration, backward induction, early exercise; 20+ years refinement |
| Day count conventions | Manual ACT/360 calculation | QuantLib DayCounter classes | Handles 30/360 variants (ISDA, European, US), ACT/ACT (ISDA, ICMA, AFB); edge cases like Feb 29 |
| Business day calendars | Holiday list maintenance | QuantLib Calendar classes | Pre-built calendars for 50+ countries; joint calendars; updated for holiday changes |
| OAS/Z-spread calculation | Manual iterative search | QuantLib Brent solver + BondFunctions | Numerical stability; proven convergence; integrates with bond pricing |
| Monte Carlo path generation | Custom random number generation | QuantLib GaussianPathGenerator | Low-discrepancy sequences; antithetic variates; Sobol sequences for variance reduction |
| Interpolation methods | Linear/cubic spline from scratch | QuantLib interpolation (LogCubic, Linear, etc.) | Specialized for finance (log-linear on discounts); extrapolation handling |
| Prepayment models (PSA) | Custom prepayment logic | Existing `compute/cashflow/prepayment.py` stub | Already has PSA ramp logic; extend with calibration, not rebuild |

**Key insight:** QuantLib is 500K+ lines of C++ refined over 20+ years by quants at major banks. Its complexity (option pricing trees, curve bootstrapping convergence, holiday calendars) is deceptive — "simple" problems have 50+ edge cases. Use QuantLib for all financial mathematics; focus custom code on business logic, data mapping, and measure orchestration.

## Common Pitfalls

### Pitfall 1: Evaluation Date Not Set
**What goes wrong:** QuantLib raises `RuntimeError: null evaluation date` or produces incorrect results when `Settings.instance().evaluationDate` is not initialized.

**Why it happens:** QuantLib is stateful; all date calculations depend on global evaluation date.

**How to avoid:** Set evaluation date at start of each pricer call; reset in worker loop between positions.

**Warning signs:** Intermittent pricing failures; results change based on test execution order.

**Code:**
```python
# WRONG: evaluation date not set
bond = ql.FixedRateBond(...)
price = bond.cleanPrice()  # May fail or use stale date

# CORRECT: set before pricing
calc_date = ql.Date(15, 1, 2026)
ql.Settings.instance().evaluationDate = calc_date
bond = ql.FixedRateBond(...)
price = bond.cleanPrice()
```

### Pitfall 2: Mismatch Between Day Count Conventions
**What goes wrong:** Bond priced with Actual/360 curve but Actual/Actual accrual → incorrect cashflow PV.

**Why it happens:** Instrument and curve may have different conventions; not all QuantLib methods enforce consistency.

**How to avoid:** Explicitly verify day count convention alignment; use instrument's accrualDayCounter for curve if instrument-specific.

**Warning signs:** Small but systematic pricing errors vs. Bloomberg; golden tests fail by 1-2 bps.

### Pitfall 3: Curve Not Bootstrapped (Lazy Evaluation)
**What goes wrong:** Code creates PiecewiseYieldCurve but doesn't trigger calculation; later access fails or is slow.

**Why it happens:** QuantLib uses lazy evaluation; curve only bootstraps when first accessed.

**How to avoid:** Force evaluation immediately after construction with `curve.discount(calc_date)` or `curve.nodes()`.

**Warning signs:** First pricing in worker takes 10x longer than subsequent; unexpected exceptions on curve access.

**Code:**
```python
curve = ql.PiecewiseLogCubicDiscount(calc_date, helpers, ql.Actual360())
# Force bootstrap NOW (fail fast if data invalid)
_ = curve.discount(calc_date)
curve.enableExtrapolation()
```

### Pitfall 4: Handle Relinking Without Understanding Observer Pattern
**What goes wrong:** Modifying a quote doesn't update dependent instruments; or excessive recalculations slow worker.

**Why it happens:** QuantLib uses Observer pattern; RelinkableHandle propagates changes, but understanding when/how is critical.

**How to avoid:** Use `QuoteHandle` for market data that changes per scenario; relink curve handles for scenario shocks.

**Warning signs:** Scenario results identical to BASE; or pricing slows 10x with scenarios enabled.

### Pitfall 5: Ignoring Hull-White Calibration for Callable Bonds
**What goes wrong:** TreeCallableFixedRateBondEngine produces unrealistic OAS; prices differ wildly from market.

**Why it happens:** Hull-White model requires calibration (mean reversion `a`, volatility `sigma`) to swaption prices; using arbitrary values → garbage.

**How to avoid:** Calibrate Hull-White to swaption volatilities from market data; or use market-standard values (a=0.03, sigma=0.12 for USD as starting point).

**Warning signs:** OAS > 500 bps on investment-grade bond; callable bond price > straight bond price.

### Pitfall 6: CPR/PSA Prepayment Model Not Calibrated to Current Environment
**What goes wrong:** ABS/MBS valuation uses historical PSA 100% assumption; actual prepayments differ dramatically in low/high rate environments.

**Why it happens:** PSA is a convention, not a forecast; requires adjustment for current rate levels, borrower characteristics, refi incentives.

**How to avoid:** Implement rate-dependent prepayment model (S-curve); calibrate to recent prepayment speeds; scenario-test across rate environments.

**Warning signs:** MBS price deviates >5% from dealer quotes; prepayment speeds flat across all scenarios.

### Pitfall 7: Not Handling Accrued Interest Correctly
**What goes wrong:** Confused between clean price, dirty price, NPV; double-counting or missing accrued interest in PV calculation.

**Why it happens:** QuantLib `NPV()` returns dirty price; `cleanPrice()` subtracts accrued; market data may quote either.

**How to avoid:** Document which price convention is used in market_snapshot; use appropriate QuantLib method; verify with `accruedAmount()`.

**Warning signs:** Bond PV differs from market price by exact amount of accrued interest.

### Pitfall 8: Forgetting to Enable Extrapolation on Curves
**What goes wrong:** Pricing long-dated bonds fails with "1st iteration: failed at 1st alive instrument" when curve doesn't cover maturity.

**Why it happens:** QuantLib curves don't extrapolate by default; bonds maturing beyond last market instrument raise exceptions.

**How to avoid:** Call `curve.enableExtrapolation()` after construction; or extend market data to cover all instrument maturities.

**Warning signs:** Pricing works for 5Y bonds but fails for 10Y; error mentions "extrapolation not enabled".

## Code Examples

Verified patterns from official sources:

### Building a Discount Curve from Deposits and Swaps
```python
# Source: https://www.quantlibguide.com/Curve%20bootstrapping.html
import QuantLib as ql

calc_date = ql.Date(15, 1, 2026)
ql.Settings.instance().evaluationDate = calc_date

# Define helpers from market instruments
helpers = [
    ql.DepositRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(0.0250)),
        ql.Period(3, ql.Months),
        2,
        ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        ql.ModifiedFollowing,
        False,
        ql.Actual360()
    ),
    ql.SwapRateHelper(
        ql.QuoteHandle(ql.SimpleQuote(0.0300)),
        ql.Period(2, ql.Years),
        ql.UnitedStates(ql.UnitedStates.GovernmentBond),
        ql.Annual,
        ql.Unadjusted,
        ql.Thirty360(ql.Thirty360.BondBasis),
        ql.USDLibor(ql.Period(3, ql.Months))
    ),
]

# Bootstrap with LogCubic interpolation on discount factors
curve = ql.PiecewiseLogCubicDiscount(calc_date, helpers, ql.Actual360())
curve.enableExtrapolation()

# Use in pricing
curve_handle = ql.YieldTermStructureHandle(curve)
```

### Pricing a Callable Bond with OAS
```python
# Source: http://gouthamanbalaraman.com/blog/callable-bond-quantlib-python.html
import QuantLib as ql

calc_date = ql.Date(16, 8, 2016)
ql.Settings.instance().evaluationDate = calc_date

# Flat yield curve (3.5%)
day_count = ql.ActualActual(ql.ActualActual.Bond)
rate = 0.035
ts = ql.FlatForward(calc_date, rate, day_count, ql.Compounded, ql.Semiannual)
ts_handle = ql.YieldTermStructureHandle(ts)

# Callable bond with 5% coupon, callable at 100 after 2 years
issue_date = ql.Date(16, 8, 2016)
maturity_date = ql.Date(16, 8, 2021)
schedule = ql.MakeSchedule(issue_date, maturity_date, ql.Period(ql.Semiannual))

call_schedule = ql.CallabilitySchedule()
call_price = ql.BondPrice(100.0, ql.BondPrice.Clean)
call_date = ql.Date(16, 8, 2018)
call_schedule.append(ql.Callability(call_price, ql.Callability.Call, call_date))

bond = ql.CallableFixedRateBond(
    2, 100.0, schedule, [0.05], day_count,
    ql.ModifiedFollowing, 100.0, issue_date, call_schedule
)

# Price with Hull-White model
model = ql.HullWhite(ts_handle, a=0.03, sigma=0.12)
engine = ql.TreeCallableFixedRateBondEngine(model, grid_points=40)
bond.setPricingEngine(engine)

clean_price = bond.cleanPrice()  # 68.38
```

### Calculating Duration and Convexity
```python
# Source: https://quantlib-python-docs.readthedocs.io/en/latest/instruments/bonds.html
import QuantLib as ql

# Fixed rate bond
bond = ql.FixedRateBond(
    2, 100.0, schedule, [0.04], ql.ActualActual(ql.ActualActual.Bond)
)
bond.setPricingEngine(ql.DiscountingBondEngine(curve_handle))

# Calculate risk metrics
ytm = bond.bondYield(ql.ActualActual(ql.ActualActual.Bond), ql.Compounded, ql.Annual)
duration = ql.BondFunctions.duration(
    bond, ytm, ql.ActualActual(ql.ActualActual.Bond), ql.Compounded, ql.Annual,
    ql.Duration.Modified
)
convexity = ql.BondFunctions.convexity(
    bond, ytm, ql.ActualActual(ql.ActualActual.Bond), ql.Compounded, ql.Annual
)
```

### Applying Scenarios with ZeroSpreadedTermStructure
```python
# Source: http://gouthamanbalaraman.com/blog/bonds-with-spreads-quantlib-python.html
import QuantLib as ql

base_curve = ql.PiecewiseLogCubicDiscount(calc_date, helpers, ql.Actual360())
base_curve.enableExtrapolation()
base_handle = ql.YieldTermStructureHandle(base_curve)

# Scenario: +25 bps spread shock
spread_quote = ql.QuoteHandle(ql.SimpleQuote(0.0025))  # 25 bps
scenario_curve = ql.ZeroSpreadedTermStructure(base_handle, spread_quote)
scenario_handle = ql.YieldTermStructureHandle(scenario_curve)

bond.setPricingEngine(ql.DiscountingBondEngine(scenario_handle))
scenario_pv = bond.NPV()

# Change scenario by modifying quote
spread_quote.setValue(0.0050)  # 50 bps
scenario_pv_50 = bond.NPV()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom curve builders | QuantLib PiecewiseYieldCurve | 2010s adoption | Reduced quant library development by 90%; focus on business logic |
| LIBOR curves | SOFR/SONIA (multi-curve framework) | 2021-2023 LIBOR transition | QuantLib supports OIS discounting, basis curves; code must handle multiple rate indices |
| Single discount curve | Multi-curve (OIS discount, tenor forwards) | Post-2008 crisis | Modern pricers must separate discount curve from projection curve |
| Parametric VaR only | Expected Shortfall (CVaR) required | Basel III (2016+) | VaR insufficient; ES mandatory for regulatory capital |
| Static prepayment models | ML-based prepayment forecasting | 2020s | PSA/CPR still baseline; ML augments for ABS/MBS valuation accuracy |
| Bloomberg API (proprietary) | Open-source QuantLib | 2000s-2010s | QuantLib matured; competitive with vendor libraries; zero licensing cost |

**Deprecated/outdated:**
- **LIBOR-based instruments:** Transition to SOFR (USD), SONIA (GBP), ESTR (EUR) complete by 2023; code should not hardcode LIBOR.
- **Single-curve discounting:** Post-2008, OIS curve for discounting, LIBOR/SOFR curves for projection; don't assume same curve.
- **QuantLib Python 2.x support:** As of QuantLib 1.30+, Python 2 unsupported; require Python 3.8+.
- **Manual Monte Carlo without variance reduction:** Modern implementations use Sobol sequences, antithetic variates; don't use naive random sampling.

## Open Questions

### 1. Hull-White Calibration Data Source
- **What we know:** TreeCallableFixedRateBondEngine requires Hull-White parameters (mean reversion `a`, volatility `sigma`); calibration to swaption volatilities is standard practice.
- **What's unclear:** Does `market_snapshot` include swaption volatility surface? Or use fixed parameters?
- **Recommendation:** Start with market-standard fixed parameters (a=0.03, sigma=0.12 for USD as literature baseline); add swaption vol surface in future phase if OAS accuracy critical.

### 2. ABS/MBS Prepayment Model Calibration
- **What we know:** PSA/CPR models are conventions; actual prepayments vary by collateral, rate environment, borrower profile.
- **What's unclear:** Source of historical prepayment data for calibration? Bloomberg PREPS, Intex, or internal data?
- **Recommendation:** Implement PSA 100% as baseline (per existing stub); flag PRICE-04 as requiring quant team spike for calibration strategy.

### 3. Structured Product Waterfall Specification
- **What we know:** Requirement PRICE-05 calls for structured product pricer; waterfall logic is deal-specific (CLO, CDO, etc.).
- **What's unclear:** Structured product types in scope? Waterfall rules standardized or per-deal parsing?
- **Recommendation:** Defer until portfolio sample data available; waterfall logic likely too complex for generic pricer (may need deal-specific subclasses).

### 4. Derivatives Hedge Instruments Scope
- **What we know:** PRICE-06 mentions derivatives for hedging; could be interest rate swaps, swaptions, FX forwards, etc.
- **What's unclear:** Which derivative types are priority? Existing FX_FWD pricer covers FX; what else?
- **Recommendation:** Start with interest rate swaps (QuantLib SwapRateHelper already used in curve building); defer exotic options.

### 5. VaR Methodology (Historical vs. Parametric vs. Monte Carlo)
- **What we know:** RISK-04 requires Historical and Parametric VaR; Monte Carlo also mentioned in SCEN-03.
- **What's unclear:** Which is primary for production? All three, or focus on one initially?
- **Recommendation:** Implement Historical VaR first (simplest, no distributional assumptions); add Parametric/Monte Carlo in later tasks.

### 6. Regulatory Stress Scenario Source (CCAR/DFAST)
- **What we know:** STATE.md flags CCAR/DFAST stress scenarios as requiring compliance input; scenarios are Fed-published curves.
- **What's unclear:** Are stress scenarios in scope for Phase 2 or deferred to Regulatory phase?
- **Recommendation:** Implement scenario infrastructure (curve shock application) in Phase 2; defer CCAR-specific scenarios to regulatory phase (likely Phase 6+).

### 7. Golden Test Reference Price Source
- **What we know:** Success criteria call for golden tests validating all pricers; need verified reference prices.
- **What's unclear:** Bloomberg? Markit? Manual calculations? Third-party pricing service?
- **Recommendation:** Use QuantLib itself for golden tests (price with known inputs, verify against documented examples); supplement with Bloomberg for spot-checks if available.

## Sources

### Primary (HIGH confidence)
- [QuantLib PyPI 1.41](https://pypi.org/project/QuantLib/) - Current version, installation, Python compatibility
- [QuantLib-Python Bond Documentation](https://quantlib-python-docs.readthedocs.io/en/latest/instruments/bonds.html) - Bond types, CallableFixedRateBond API
- [QuantLib Yield Term Structures](https://quantlib-python-docs.readthedocs.io/en/latest/termstructures/yield.html) - PiecewiseYieldCurve, interpolation methods
- [QuantLib Dates and Conventions](https://quantlib-python-docs.readthedocs.io/en/latest/dates.html) - DayCounter, Calendar classes
- [Coding towards CFA: Callable/Putable Bonds](https://dataninjago.com/2025/01/07/coding-towards-cfa-25-pricing-callable-and-putable-bonds-with-quantlib/) - CallableFixedRateBond examples (January 2025)
- [Coding towards CFA: Z-Spread](https://dataninjago.com/2025/01/01/coding-towards-cfa-21-calculate-z-spread-with-quantlib/) - Brent solver pattern (January 2025)
- [Goutham Balaraman: Callable Bonds](http://gouthamanbalaraman.com/blog/callable-bond-quantlib-python.html) - TreeCallableFixedRateBondEngine walkthrough
- [Goutham Balaraman: Bonds with Spreads](http://gouthamanbalaraman.com/blog/bonds-with-spreads-quantlib-python.html) - ZeroSpreadedTermStructure pattern

### Secondary (MEDIUM confidence)
- [QuantLib Curve Bootstrapping Guide](https://www.quantlibguide.com/Curve%20bootstrapping.html) - PiecewiseYieldCurve internals, interpolation comparison
- [QuantLib Architecture Guide](https://risk-quant-haun.github.io/quantlib/architecture) - Observer pattern, pricing engine design
- [Hull-White Simulation Tutorial](http://gouthamanbalaraman.com/blog/hull-white-simulation-quantlib-python.html) - Monte Carlo path generation
- [PyQuant News: Risk Metrics Guide](https://www.pyquantnews.com/free-python-resources/risk-metrics-in-python-var-and-cvar-guide) - VaR/CVaR calculation methods
- [ISDA Day Counters GitHub](https://github.com/miradulo/isda_daycounters) - Python implementation of ISDA conventions (validates QuantLib usage)
- [SciPy Interpolation](https://scipy-lectures.org/intro/scipy.html) - Numerical methods complementing QuantLib
- [NumPy/SciPy for Finance](https://www.pyquantnews.com/free-python-resources/mastering-python-for-finance-numpy-pandas-scipy) - Vectorization patterns

### Tertiary (LOW confidence - validation needed)
- [Prepayment Modeling Overview](https://thismatter.com/money/bonds/types/abs/prepayment-models.htm) - PSA/CPR definitions (general reference, not Python-specific)
- [PSA Prepayment Model Wikipedia](https://en.wikipedia.org/wiki/PSA_prepayment_model) - PSA ramp specification
- [GT-Score Financial Risk Validation](https://www.arxiv.org/pdf/2602.00080) - 2026 generalization testing methodology (academic, not yet industry-standard)

## Metadata

**Confidence breakdown:**
- **Standard stack: HIGH** - QuantLib 1.41 is verified current version; widely documented; PyPI installation confirmed
- **Architecture patterns: MEDIUM-HIGH** - Patterns sourced from official docs and recent tutorials (Jan 2025); production usage patterns less documented
- **Pitfalls: MEDIUM** - Common errors documented in tutorials/forums; some extrapolated from QuantLib architecture; golden test validation recommended
- **Code examples: HIGH** - All examples from official QuantLib docs or verified tutorials with working code
- **Prepayment/ABS: LOW-MEDIUM** - PSA formula verified; calibration strategies less documented; flagged as needing quant review

**Research date:** 2026-02-11
**Valid until:** 2026-03-15 (30 days; QuantLib stable, but quant finance moves fast on regulatory changes)

**Notes for planner:**
- Skeleton files already exist for all major components (pricers, cashflow, risk) — indicates prior planning; leverage existing structure
- Function-based registry pattern is established (Phase 1); maintain compatibility; AbstractPricer (base.py) is optional, not required
- QuantLib handles complexity; planner should focus tasks on data mapping, measure orchestration, golden test creation
- Prepayment calibration (PRICE-04), structured products (PRICE-05), and regulatory scenarios flagged as requiring specialist input
- Monte Carlo infrastructure (SCEN-03) can reuse QuantLib's path generators; don't rebuild RNG/variance reduction
