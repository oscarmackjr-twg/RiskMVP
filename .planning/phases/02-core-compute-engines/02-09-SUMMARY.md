---
phase: 02-core-compute-engines
plan: 09
subsystem: compute-golden-tests
tags: [testing, verification, gap-closure]
dependency_graph:
  requires:
    - 02-02: Putable bond pricer with embedded options
    - 02-05: Derivatives pricer (interest rate swaps)
    - 02-05: Structured product pricer (CLO/CDO)
  provides:
    - 3 golden tests for putable bond pricer
    - 3 golden tests for derivatives pricer
    - 3 golden tests for structured product pricer
    - Complete Phase 2 success criterion 8 (>=3 golden tests per pricer)
  affects:
    - Phase 2 verification completeness
    - Pricer test coverage
tech_stack:
  added: []
  patterns: [golden-testing, scenario-testing, rate-sensitivity]
key_files:
  created: []
  modified:
    - compute/tests/golden/test_putable_bond_golden.py
    - compute/tests/golden/test_derivatives_golden.py
    - compute/tests/golden/test_structured_golden.py
    - compute/pricers/structured.py
decisions:
  - id: SCENARIO_APPLICATION
    summary: Added scenario application to structured pricer
    rationale: Structured pricer was missing scenario support needed for rate scenario testing; implemented PARALLEL_SHIFT scenario type matching other pricers
    alternatives: [Use existing scenarios.py module, Manual scenario application in tests]
    trade_offs: Added 40 lines to structured.py for consistency with other pricers
metrics:
  duration_seconds: 296
  completed_date: 2026-02-11
---

# Phase 02 Plan 09: Gap Closure - Golden Tests Summary

**One-liner:** Added missing golden tests (credit spread, DV01 sensitivity, multiple scenarios) to satisfy Phase 2 success criterion 8 (>=3 tests per pricer)

## Objective

Close verification gaps for three pricers (PUTABLE_BOND, DERIVATIVES, STRUCTURED) that had only 2 golden tests each. Add exactly 1 test per pricer to meet the >=3 requirement, bringing total golden tests from 23 to 26.

## Tasks Completed

### Task 1: Credit Spread Test for Putable Bond (COMPLETE)
- **File:** `compute/tests/golden/test_putable_bond_golden.py`
- **Test:** `test_putable_bond_credit_spread`
- **Coverage:**
  - Putable bond pricing with +25bp credit spread shock scenario
  - Position: $1M notional putable bond (4% coupon, 5-year, putable at 100 after 3 years)
  - Validates credit spread shock decreases PV (spread widens → bond price falls)
  - Confirms put option provides downside protection (price bounded by put price of 100)
  - Assertions: spread shock decreases PV, but price change bounded by put option (< 10%)
- **Commit:** 68b2eee

### Task 2: DV01 Sensitivity Test for Derivatives (COMPLETE)
- **File:** `compute/tests/golden/test_derivatives_golden.py`
- **Test:** `test_swap_dv01_sensitivity`
- **Coverage:**
  - Swap DV01 calculation and rate sensitivity verification
  - Position: $1M notional pay-fixed swap (5% fixed, receive SOFR, 5-year maturity)
  - Validates DV01 measure is computed correctly
  - Tests rate sensitivity with 10bp parallel shift across OIS and SOFR curves
  - Verifies PV change direction is consistent with DV01 sign
  - Assertions: DV01 exists, reasonable magnitude ($1-$2000 per bp), directionally correct
- **Commit:** ad48bb8

### Task 3: Multiple Scenarios Test for Structured Products (COMPLETE)
- **File:** `compute/tests/golden/test_structured_golden.py`
- **Test:** `test_structured_scenarios`
- **Coverage:**
  - Structured product pricing across multiple rate scenarios (BASE, RATES_UP, RATES_DOWN)
  - Position: Senior tranche of CLO ($80M senior at 4%, $20M junior at 8%)
  - Collateral: 3 periods with interest and principal (~5-year average maturity)
  - Validates RATES_DOWN increases PV (discount rates fall → PV rises)
  - Validates RATES_UP decreases PV (discount rates rise → PV falls)
  - Verifies rate sensitivity is reasonable (1-15% for 100bp shock)
  - Assertions: All PVs positive, directional sensitivities correct, magnitudes reasonable
- **Commit:** 6651c0a

## Verification Results

### Full Golden Test Suite
```bash
pytest compute/tests/golden/ -v
```

**Results:** 26 tests PASSED (was 23 before this plan)
- test_putable_bond_golden.py: 3 tests ✓ (was 2)
- test_derivatives_golden.py: 3 tests ✓ (was 2)
- test_structured_golden.py: 3 tests ✓ (was 2)
- All other pricer tests: PASSING ✓

**Phase 2 Success Criterion 8 SATISFIED:** "Each pricer has >=3 golden tests"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] Missing scenario application in structured pricer**
- **Found during:** Task 3 (test_structured_scenarios)
- **Issue:** Structured product pricer did not apply scenarios from market_snapshot, causing all scenario PVs to be identical (BASE = RATES_UP = RATES_DOWN)
- **Fix:** Added `_apply_scenario` function to `compute/pricers/structured.py` to handle PARALLEL_SHIFT scenario type
- **Implementation:**
  - Added `copy` import for deep copying curves
  - Modified `price_structured` to call `_apply_scenario` before pricing
  - Implemented `_apply_scenario` function (40 lines) matching pattern from putable_bond.py
  - Supports custom scenarios with `PARALLEL_SHIFT` type from market_snapshot.scenarios dict
  - Applies rate shifts to curve nodes for specified curves
- **Files modified:** `compute/pricers/structured.py` (added _apply_scenario, updated price_structured)
- **Rationale:** Structured pricer was the only pricer without scenario support; required for testing rate sensitivity
- **Commit:** Included in 6651c0a with Task 3

## Key Insights

### Test Pattern Consistency
- All three new tests follow established golden test patterns:
  - Import QuantLib and set evaluation date
  - Position dict with position_id, quantity/notional, attributes
  - Instrument dict with product-specific parameters
  - Market snapshot with curves (instruments or nodes), scenarios
  - Call pricer function with measures and scenario_id
  - Assert PV/measures exist, are positive, and in reasonable ranges
  - Assert scenario sensitivities are directionally correct and bounded

### Scenario Application Architecture
- Pricers now have consistent scenario handling:
  - Putable bond pricer: Has `_apply_scenario` with PARALLEL_SHIFT support ✓
  - Derivatives pricer: Applies scenarios via curve bumping internally ✓
  - Structured pricer: NOW has `_apply_scenario` with PARALLEL_SHIFT support ✓ (added in this plan)
  - Other pricers: May need scenario support in future (callables, floating rate, ABS/MBS)

### DV01 Sign Convention
- Derivatives pricer DV01 calculation: `DV01 = PV(rates + 1bp) - PV(base)`
- For off-market swaps, DV01 sign depends on swap position:
  - Pay-fixed swap with negative PV: DV01 typically positive (rates up → PV less negative)
  - Receive-fixed swap with positive PV: DV01 typically negative (rates up → PV down)
- Test validates directional consistency rather than absolute sign convention

## Success Criteria Verification

- [x] test_putable_bond_golden.py has 3 tests, all passing
- [x] test_derivatives_golden.py has 3 tests, all passing
- [x] test_structured_golden.py has 3 tests, all passing
- [x] New tests follow existing patterns (QuantLib setup, position/instrument dicts, market snapshots, assertions)
- [x] New tests verify meaningful scenarios (credit spread shock, DV01 sensitivity, multiple rate scenarios)
- [x] Phase 2 success criterion 8 fully satisfied: "Each pricer has >=3 golden tests"

## Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| compute/tests/golden/test_putable_bond_golden.py | +105 | Added test_putable_bond_credit_spread |
| compute/tests/golden/test_derivatives_golden.py | +140 | Added test_swap_dv01_sensitivity |
| compute/tests/golden/test_structured_golden.py | +143 | Added test_structured_scenarios |
| compute/pricers/structured.py | +41 | Added _apply_scenario function and copy import |

**Total:** 4 files modified, +429 lines

## Self-Check: PASSED

**Created files:**
```bash
[ -f "C:/Users/omack/Intrepid/pythonFramework/RiskPlatform/riskmvp/.planning/phases/02-core-compute-engines/02-09-SUMMARY.md" ] && echo "FOUND: 02-09-SUMMARY.md"
```
✓ FOUND: 02-09-SUMMARY.md

**Commits exist:**
```bash
git log --oneline --all | grep -q "68b2eee" && echo "FOUND: 68b2eee"
git log --oneline --all | grep -q "ad48bb8" && echo "FOUND: ad48bb8"
git log --oneline --all | grep -q "6651c0a" && echo "FOUND: 6651c0a"
```
✓ FOUND: 68b2eee (Task 1: putable bond credit spread test)
✓ FOUND: ad48bb8 (Task 2: derivatives DV01 sensitivity test)
✓ FOUND: 6651c0a (Task 3: structured scenarios test + scenario fix)

**Modified files exist:**
```bash
[ -f "C:/Users/omack/Intrepid/pythonFramework/RiskPlatform/riskmvp/compute/tests/golden/test_putable_bond_golden.py" ] && echo "FOUND: test_putable_bond_golden.py"
[ -f "C:/Users/omack/Intrepid/pythonFramework/RiskPlatform/riskmvp/compute/tests/golden/test_derivatives_golden.py" ] && echo "FOUND: test_derivatives_golden.py"
[ -f "C:/Users/omack/Intrepid/pythonFramework/RiskPlatform/riskmvp/compute/tests/golden/test_structured_golden.py" ] && echo "FOUND: test_structured_golden.py"
[ -f "C:/Users/omack/Intrepid/pythonFramework/RiskPlatform/riskmvp/compute/pricers/structured.py" ] && echo "FOUND: structured.py"
```
✓ FOUND: test_putable_bond_golden.py
✓ FOUND: test_derivatives_golden.py
✓ FOUND: test_structured_golden.py
✓ FOUND: structured.py

## Recommendations

### Phase 2 Next Steps
- **Phase 2 COMPLETE:** All 9 plans executed (01-08 + gap closure 09)
- **Golden test coverage:** 26 tests across all pricers (>=3 per pricer achieved)
- **Ready for Phase 3:** Portfolio & Data Services

### Future Enhancements
1. **Scenario consistency:** Consider adding scenario support to remaining pricers (callable_bond, floating_rate, abs_mbs) if not already present
2. **DV01 enhancement:** Consider parallel DV01 (bump both OIS and SOFR) vs partial DV01 (bump OIS only) for derivatives
3. **Structured product stress testing:** Consider adding prepayment and default stress scenarios to structured product tests
4. **Golden test automation:** Consider generating golden test templates from pricer signatures

## Duration
- **Start:** 1770843152 (2026-02-11)
- **End:** 1770843448 (2026-02-11)
- **Duration:** 296 seconds (4 minutes 56 seconds)
