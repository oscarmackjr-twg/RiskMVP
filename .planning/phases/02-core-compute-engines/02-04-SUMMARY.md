---
phase: 02-core-compute-engines
plan: 04
subsystem: pricing
tags: [abs, mbs, prepayment, default-model, cashflow-projection]
dependencies:
  requires: [02-01]
  provides: [abs-mbs-pricer, psa-prepayment-model, default-recovery-model]
  affects: [worker-registry, risk-calculations]
tech-stack:
  added: []
  patterns: [period-by-period-cashflow-projection, behavioral-modeling]
key-files:
  created:
    - compute/pricers/abs_mbs.py
    - compute/cashflow/prepayment.py
    - compute/cashflow/default_model.py
    - compute/tests/golden/test_abs_mbs_golden.py
  modified:
    - compute/pricers/registry.py
    - compute/quantlib/scenarios.py
decisions:
  - title: "Period-by-period balance tracking"
    rationale: "Prepayments and defaults must be calculated on beginning-of-period balance, with interest recalculated on actual balance after prepayments. Ensures accurate cashflow projection without double-counting."
    alternatives: ["Use prepayment/default models with running balance", "Rely on base amortization schedule without adjustment"]
  - title: "Simplified PD model (marginal per period)"
    rationale: "MVP uses monthly marginal PD (annual_pd / 12) rather than full survival curve. Sufficient for initial implementation. Phase 4 enhancement will add cumulative survival modeling."
    alternatives: ["Full credit model with survival curves", "CDR-based constant default rate"]
  - title: "PSA 100% as default prepayment speed"
    rationale: "Industry standard baseline. Instruments can override with custom PSA speeds. Calibration to historical prepayments flagged as Phase 4 enhancement."
    alternatives: ["CPR lookup tables by vintage", "Machine learning prepayment model"]
metrics:
  duration: 521
  completed: "2026-02-11T20:16:08Z"
  tasks: 4
  files: 6
  commits: 4
---

# Phase 02 Plan 04: ABS/MBS Pricer with Prepayment & Default Modeling

**One-liner:** ABS/MBS pricer with PSA prepayment ramp, PD/LGD default modeling, and loss-adjusted present value calculation

## What Was Built

Implemented institutional-grade ABS/MBS pricer (PRICE-04) with behavioral models for prepayments and defaults:

1. **PSA and CPR Prepayment Models (CF-02)**
   - `apply_psa_prepayment()`: CPR ramps 0.2% → 6% over 30 months (PSA standard)
   - `apply_cpr_prepayment()`: Constant CPR model for sensitivity analysis
   - SMM (single monthly mortality) calculation from annual CPR
   - Prepayment calculated on beginning-of-period balance

2. **Default and Recovery Modeling (CF-03)**
   - `apply_default_model()`: PD × LGD × EAD expected loss calculation
   - Marginal PD per period (simplified model, Phase 4 will add survival curves)
   - Recovery = (1 - LGD) × default amount
   - Default loss and recovery fields added to cashflow schedule

3. **ABS/MBS Pricer with Cashflow Projection**
   - `price_abs_mbs()`: Full cashflow projection with prepayments, defaults, and discounting
   - Period-by-period balance tracking with accurate interest calculation
   - Measures: PV, WAL (weighted average life), DV01
   - Supports configurable PSA speed, LGD, PD, discount curve

4. **Golden Tests and Registration**
   - 4 golden tests: basic pricing, fast prepayment, default sensitivity, DV01
   - Registered as `ABS_MBS` product type in worker registry
   - All tests pass with realistic market assumptions

## How It Works

### Cashflow Projection Sequence

For each month in the pool's life:

1. **Calculate interest** on beginning balance: `interest = balance × (WAC / 12)`
2. **Calculate prepayment** (PSA model): `prepay = balance × SMM`, where SMM from CPR ramp
3. **Calculate default loss**: `loss = balance × PD × LGD`
4. **Calculate recovery**: `recovery = balance × PD × (1 - LGD)`
5. **Scheduled principal** from base amortization (constrained by remaining balance)
6. **Total principal out** = scheduled + prepayment + default
7. **Update balance** for next month: `balance -= total_principal_out`

### Present Value Calculation

For each cashflow:
```
total_cf = scheduled_principal + interest + prepayment - default_loss + recovery
pv += total_cf × discount_factor(month / 12)
```

### Weighted Average Life (WAL)

```
WAL = sum(principal_i × time_i) / sum(principal_i)
```
where principal includes both scheduled and prepaid amounts.

## Test Results

```
✓ test_abs_mbs_basic: PV=$1,013,327.81, WAL=8.87 years
  - $1M pool, 5% WAC, 30-year, PSA 100%, LGD 40%, PD 1%
  - PV above par due to 5% coupon vs 4% discount (positive carry)
  - WAL ~9 years (30-year mortgage shortened by prepayments)

✓ test_abs_mbs_fast_prepayment:
  - PSA 100%: WAL=8.87 years
  - PSA 200%: WAL=6.20 years (30% shorter life)

✓ test_abs_mbs_default_sensitivity:
  - LGD 20%: PV=$1,040,903.66
  - LGD 60%: PV=$985,751.97
  - Impact: $55,151.69 (5.5% of notional)

✓ test_abs_mbs_with_dv01: DV01=-$698.30 per 1bp
  - Negative DV01 (rates up → PV down)
  - Magnitude reasonable for ~9-year WAL
```

## Deviations from Plan

### Auto-fixed Issues (Deviation Rules 1-3)

**1. [Rule 1 - Bug] Prepayment double-counting**
- **Found during:** Task 3 initial testing
- **Issue:** PV was $1.72M (72% above par). Prepayment model was reducing `remaining_principal` but pricer was treating it as beginning balance, causing over-counting.
- **Fix:** Removed balance updates from prepayment/default models. Pricer now tracks balances period-by-period with proper sequencing: prepayment → defaults → scheduled principal.
- **Files modified:** `compute/cashflow/prepayment.py`, `compute/pricers/abs_mbs.py`
- **Commit:** a80364f

**2. [Rule 1 - Bug] Interest calculated on wrong balance**
- **Found during:** Task 3 debugging
- **Issue:** Base amortization schedule calculates interest on full balance (no prepayments). With prepayments, actual balance is lower, so interest was overstated.
- **Fix:** Recalculate interest period-by-period on actual beginning balance: `interest = current_balance × monthly_rate`
- **Files modified:** `compute/pricers/abs_mbs.py`
- **Commit:** a80364f

**3. [Rule 1 - Bug] Scenarios.py field name inconsistency**
- **Found during:** Task 4 DV01 test
- **Issue:** `scenarios.py` expected `zero_rate` field but test fixtures used `rate` field. Caused KeyError in DV01 calculation.
- **Fix:** Updated `apply_scenario()` to support both `zero_rate` and `rate` field names (backward compatibility).
- **Files modified:** `compute/quantlib/scenarios.py`
- **Commit:** a80364f

**4. [Rule 3 - Missing field handling] Backward-compatible field names**
- **Found during:** Integration with default_model.py
- **Issue:** Default model expected `principal` field but ABS/MBS pricer uses `scheduled_principal` to distinguish from prepayments.
- **Fix:** Updated `default_model.py` to check for `scheduled_principal` first, fall back to `principal` (backward compatibility).
- **Files modified:** `compute/cashflow/default_model.py`
- **Commit:** 8c32045

## Key Decisions Made

### 1. Period-by-Period Balance Tracking in Pricer

**Context:** Prepayment and default models need beginning-of-period balance, but each reduces the balance for the next period.

**Decision:** Pricer manually tracks balances period-by-period rather than relying on prepayment/default models to update `remaining_principal`.

**Rationale:**
- Prepayments calculated on beginning balance (BEFORE scheduled principal)
- Defaults calculated on beginning balance (BEFORE any principal reduction)
- Interest calculated on beginning balance (BEFORE any payments)
- Ending balance = beginning - scheduled - prepayment - default

This ensures correct sequencing and avoids double-counting or balance mismatches.

**Alternatives considered:**
- Have prepayment/default models chain balance updates → rejected (error-prone, hard to debug)
- Use separate passes for prepayment/default/interest → rejected (requires multiple iterations)

### 2. Simplified Marginal PD Model

**Context:** Full credit modeling requires survival curves, hazard rates, and term structure of credit.

**Decision:** Use marginal PD per period (`monthly_pd = annual_pd / 12`) as MVP simplification.

**Rationale:**
- Sufficient for initial ABS/MBS pricing capability
- Avoids complexity of survival curve bootstrapping
- Clearly documented as Phase 4 enhancement area
- Flagged in STATE.md research flags

**Phase 4 Enhancement:** Implement full survival curve with `S(t) = exp(-integral(hazard_rate))` and term structure of PD.

### 3. PSA 100% as Industry Baseline

**Context:** Prepayment speeds vary by vintage, geography, rate environment.

**Decision:** Default to PSA 100% with instrument-level override capability.

**Rationale:**
- PSA 100% is industry standard reference speed
- Instruments can specify custom PSA speeds (e.g., 150%, 200%)
- Avoids need for prepayment model calibration in MVP
- Historical prepayment data availability flagged as blocker in STATE.md

**Future Enhancement:** Calibrate PSA speeds to historical pool data, add CPR lookup tables by vintage.

## Technical Insights

### PSA Model Ramp

The PSA standard defines a 30-month ramp:
```
month ≤ 30: base_cpr = month × 0.002 (0.2% → 6%)
month > 30:  base_cpr = 0.06 (constant at 6%)
actual_cpr = base_cpr × (psa_speed / 100)
```

This captures the industry observation that prepayments start slow (refinancing friction, seasoning) and accelerate over first 2.5 years.

### SMM Conversion

CPR (Conditional Prepayment Rate) is annualized. Convert to monthly:
```
SMM = 1 - (1 - CPR)^(1/12)
```

This is the standard formula ensuring monthly compounding consistency.

### WAL Sensitivity to Prepayments

Test results show PSA 200% reduces WAL from 8.87 to 6.20 years (30% reduction). This matches industry expectations: faster prepayments shorten life, reduce interest income, and lower duration risk.

## Validation

✅ PSA prepayment model ramps correctly (0.2% → 6% over 30 months)
✅ CPR model applies constant prepayment speed
✅ Default model reduces principal by PD × LGD × EAD
✅ ABS/MBS pricer generates full cashflow schedule
✅ 4 golden tests pass (basic, fast prepayment, default sensitivity, DV01)
✅ ABS_MBS registered in pricer registry (8 types total)
✅ WAL calculation correct (prepayments shorten life significantly)
✅ PV reflects positive carry (5% coupon vs 4% discount) net of credit losses

## Success Criteria Met

- [x] PSA and CPR prepayment models (CF-02) implemented per industry standard
- [x] Default and recovery modeling (CF-03) reduces cashflows by expected losses
- [x] `price_abs_mbs()` generates cashflow schedule with prepayments and defaults
- [x] PV calculated from loss-adjusted discounted cashflows
- [x] WAL (weighted average life) computed correctly
- [x] 4 golden tests validate prepayment sensitivity, default sensitivity, DV01
- [x] Pricer registered and functional in worker

## Files Changed

### Created (4 files)
- `compute/pricers/abs_mbs.py` (255 lines) - ABS/MBS pricer with cashflow projection
- `compute/cashflow/prepayment.py` (140 lines) - PSA and CPR prepayment models
- `compute/cashflow/default_model.py` (93 lines) - Default and recovery modeling
- `compute/tests/golden/test_abs_mbs_golden.py` (265 lines) - Golden tests

### Modified (2 files)
- `compute/pricers/registry.py` - Added ABS_MBS registration
- `compute/quantlib/scenarios.py` - Support both 'rate' and 'zero_rate' fields

## Commits

| Hash | Type | Message |
|------|------|---------|
| f1e48f1 | feat | Implement PSA and CPR prepayment models |
| 8c32045 | feat | Implement default and recovery modeling |
| a80364f | feat | Implement ABS/MBS pricer with cashflow projection (includes bug fixes) |
| 31f1881 | test | Add golden tests for ABS/MBS pricer and register in worker |

## What's Next

**Immediate dependencies met:**
- ABS_MBS pricer ready for production use
- Worker can price ABS_MBS product types via registry
- Prepayment and default models available for other structured products

**Phase 2 continuation:**
- Plan 02-05: Floating Rate Note Pricer (LIBOR/SOFR index curves)
- Plan 02-06: Structured Product Pricer (waterfall logic)
- Plan 02-07: Market Risk Analytics (DV01, convexity, key rate durations)

**Phase 4 enhancements (flagged in STATE.md):**
- Calibrate PSA speeds to historical prepayment data
- Implement full survival curve credit modeling
- Add CPR lookup tables by vintage and geography
- Validate against Bloomberg/Markit reference prices

---

**Plan completed:** 2026-02-11T20:16:08Z
**Duration:** 521 seconds (8 min 41 sec)
**Status:** ✅ All tasks complete, all tests passing

## Self-Check: PASSED

✅ All created files exist:
- compute/pricers/abs_mbs.py
- compute/cashflow/prepayment.py
- compute/cashflow/default_model.py
- compute/tests/golden/test_abs_mbs_golden.py

✅ All commits exist:
- f1e48f1: PSA and CPR prepayment models
- 8c32045: Default and recovery modeling
- a80364f: ABS/MBS pricer with cashflow projection
- 31f1881: Golden tests and registry registration

✅ All 4 golden tests pass (test_abs_mbs_golden.py)

✅ ABS_MBS successfully registered in pricer registry
