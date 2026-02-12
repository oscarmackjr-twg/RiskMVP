---
phase: 04-regulatory-analytics-reporting
plan: 02
subsystem: regulatory-compute
tags: [cecl, basel-iii, gaap, ifrs-9, regulatory-calculations]
completed: 2026-02-12T03:54:05Z
duration_seconds: 341

dependency_graph:
  requires:
    - compute.risk.credit (PD curves, LGD models)
    - compute.quantlib (curve infrastructure)
  provides:
    - compute.regulatory.cecl (CECL allowance calculation)
    - compute.regulatory.basel (Basel III RWA and capital ratios)
    - compute.regulatory.gaap_ifrs (GAAP/IFRS valuation framework)
  affects:
    - services.regulatory_svc (will consume these compute modules)

tech_stack:
  added:
    - ASC 326 multi-scenario CECL implementation
    - Basel III standardized approach RWA
    - GAAP ASC 320 valuation framework
    - IFRS 9 classification and ECL integration
  patterns:
    - Probability-weighted multi-scenario ECL calculation
    - Risk weight lookup with fallback logic
    - Business model-based IFRS 9 classification
    - SPPI test for contractual cash flow characteristics

key_files:
  created:
    - compute/regulatory/cecl.py (187 lines)
    - compute/regulatory/basel.py (214 lines)
    - compute/regulatory/gaap_ifrs.py (363 lines)
    - compute/tests/test_cecl.py (277 lines)
    - compute/tests/test_basel.py (236 lines)
    - compute/tests/test_gaap_ifrs.py (386 lines)
  modified: []

decisions:
  - Multi-scenario CECL with probability weighting for base/adverse/severely adverse scenarios
  - Lifetime PD calculation using survival probability method (1 - Π(1-PD_i))
  - Stage classification aligned with IFRS 9 for international consistency
  - Basel III standardized approach with tuple-based risk weight lookup
  - Risk weight fallback order: exact match → (type, ANY) → default 1.00
  - GAAP impairment threshold: >10% decline for "other than temporary" impairment
  - IFRS 9 SPPI test: bonds/loans pass, derivatives fail
  - Business model override parameter for IFRS classification flexibility

metrics:
  tests_created: 49
  test_pass_rate: 100%
  functions_implemented: 11
  lines_of_code: 1663
---

# Phase 04 Plan 02: Regulatory Calculation Modules Summary

**One-liner:** ASC 326 CECL allowance, Basel III RWA with standardized approach, and GAAP/IFRS valuation framework with impairment and ECL integration.

## What Was Built

Implemented three core regulatory calculation modules for credit loss allowance, capital adequacy, and accounting valuation:

### 1. CECL Allowance Calculation (REG-02)

**ASC 326 Current Expected Credit Loss implementation:**
- Multi-scenario probability-weighted ECL approach
- Lifetime PD calculation from marginal annual PD curves using survival probability
- Issuer-based portfolio segmentation
- Stage classification (Stage 1/2/3) aligned with IFRS 9
- Qualitative adjustment factor (Q-factor) support

**Key functions:**
- `compute_cecl_allowance()`: Main ECL calculation with scenario weighting
- `_compute_lifetime_pd()`: Converts marginal PD curve to lifetime cumulative PD
- `stage_classification()`: IFRS 9 / CECL staging logic

**Integration points:**
- Uses `compute.risk.credit.pd_model.build_pd_curve()` for PD curve fallback
- Accepts pre-built PD curves from risk analytics
- LGD assumptions from credit risk models

### 2. Basel III RWA Calculation (REG-03)

**Standardized approach for Risk-Weighted Assets:**
- Risk weight lookup by (counterparty_type, rating) tuple
- Fallback logic: exact match → (type, ANY) → default 100%
- Aggregation by counterparty type and credit rating
- Capital adequacy ratios: CET1, Tier 1, Total Capital

**Key functions:**
- `compute_basel_rwa()`: Portfolio RWA calculation with aggregation
- `get_risk_weight()`: Risk weight lookup with fallback chain
- `compute_capital_ratios()`: CET1, Tier 1, Total Capital ratios

**Risk weights implemented:**
- Sovereigns: 0% (AAA) to 150% (B)
- Corporates: 20% (AAA/AA) to 150% (BB/B/CCC)
- Retail: 75% (all ratings)
- Unrated: 100% (default)

### 3. GAAP/IFRS Valuation Framework (REG-01)

**Dual accounting framework for financial instruments:**

**GAAP (ASC 320):**
- Classification by management intent: HTM, AFS, Trading
- HTM: Amortized cost with "other than temporary" impairment (>10% decline)
- AFS: Fair value with unrealized gain/loss in OCI
- Trading: Fair value with realized gain/loss in P&L

**IFRS 9:**
- Classification by business model and SPPI test
- Amortized Cost: Hold-to-collect + SPPI pass
- FVOCI: Hold-and-sell + SPPI pass
- FVTPL: Trading or SPPI fail (derivatives)
- ECL integration for amortized cost

**Key functions:**
- `classify_gaap_category()`: HTM/AFS/Trading classification
- `classify_ifrs_category()`: Amortized Cost/FVOCI/FVTPL classification
- `compute_gaap_valuation()`: Carrying value with impairment
- `compute_ifrs_valuation()`: Carrying value with ECL

## Test Coverage

**49 golden tests across three modules:**

**CECL Tests (13):**
- Single and multi-scenario ECL calculation
- Multiple segment aggregation
- Q-factor adjustment
- PD curve fallback logic
- Lifetime PD calculation accuracy
- Stage classification edge cases

**Basel Tests (14):**
- Corporate, sovereign, retail, mixed portfolios
- Risk weight lookup with fallbacks
- RWA aggregation by type and rating
- Capital ratios at minimum thresholds
- Well-capitalized scenarios
- Zero RWA edge case

**GAAP/IFRS Tests (22):**
- Classification by intent and business model
- Impairment recognition (GAAP HTM)
- ECL integration (IFRS Amortized Cost)
- Unrealized gain/loss in OCI (AFS, FVOCI)
- Realized gain/loss in P&L (Trading, FVTPL)
- GAAP vs IFRS comparison for same position

All tests pass with known golden values.

## Deviations from Plan

None - plan executed exactly as written.

All functions implemented according to specification:
- CECL: compute_cecl_allowance, _compute_lifetime_pd, stage_classification
- Basel: compute_basel_rwa, get_risk_weight, compute_capital_ratios
- GAAP/IFRS: classify_gaap_category, classify_ifrs_category, compute_impairment, compute_gaap_valuation, compute_ifrs_valuation

All minimum line counts exceeded:
- cecl.py: 187 lines (plan: 150 min)
- basel.py: 214 lines (plan: 120 min)
- gaap_ifrs.py: 363 lines (plan: 100 min)

## Integration with Existing System

**Phase 2 Risk Analytics Integration:**
- CECL uses PD curves from `compute.risk.credit.pd_model.build_pd_curve()`
- LGD assumptions align with `compute.risk.credit.lgd` module
- EAD values from credit risk exposure models

**Phase 3 Portfolio Data:**
- Portfolio positions with issuer_id for CECL segmentation
- Counterparty type and rating for Basel RWA
- Intent and business model metadata for GAAP/IFRS classification
- Reference data (issuers, sectors, ratings) supports regulatory calculations

**Ready for Phase 4 Regulatory Service:**
- Compute modules provide calculation logic
- Service layer (Plan 03) will expose REST endpoints
- Reports (Plan 04) will consume regulatory metrics

## Technical Highlights

### 1. Probability-Weighted Multi-Scenario CECL

```python
# Example: Three scenarios with different probabilities
macro_scenarios = [
    {"name": "base", "gdp_growth": 2.5},
    {"name": "adverse", "gdp_growth": 0.5},
    {"name": "severely_adverse", "gdp_growth": -2.0},
]
scenario_weights = [0.60, 0.30, 0.10]  # Must sum to 1.0

result = compute_cecl_allowance(
    portfolio, pd_curves, lgd_assumptions,
    macro_scenarios, scenario_weights
)
# Returns: total_allowance, by_segment, scenario_detail
```

### 2. Basel III Risk Weight Lookup with Fallback

```python
# Exact match
get_risk_weight('CORPORATE', 'AAA', weights) → 0.20

# Fallback to ANY
get_risk_weight('RETAIL', 'NR', weights) → 0.75  # Uses ('RETAIL', 'ANY')

# Default 100%
get_risk_weight('UNKNOWN', 'UNKNOWN', weights) → 1.00
```

### 3. GAAP vs IFRS Valuation Comparison

```python
# Same bond, different accounting standards
position_gaap = {"intent": "HTM", "product_type": "FIXED_BOND"}
position_ifrs = {"business_model": "HOLD_TO_COLLECT", "product_type": "FIXED_BOND"}

# Market value decline: 850K vs 1M book
gaap_result = compute_gaap_valuation(position_gaap, 850000, 1000000)
# Carrying value: 850K (book - impairment)

ifrs_result = compute_ifrs_valuation(position_ifrs, 850000, 1000000, ecl_allowance=30000)
# Carrying value: 970K (book - ECL)

# Different carrying values despite same market decline
```

## Files Changed

### Created (6 files, 1,663 lines)

**Implementation:**
1. `compute/regulatory/cecl.py` (187 lines)
   - `compute_cecl_allowance()`: Multi-scenario ECL calculation
   - `_compute_lifetime_pd()`: Lifetime PD from marginal curve
   - `stage_classification()`: IFRS 9 staging

2. `compute/regulatory/basel.py` (214 lines)
   - `compute_basel_rwa()`: RWA with standardized approach
   - `get_risk_weight()`: Risk weight lookup
   - `compute_capital_ratios()`: CET1, Tier 1, Total Capital

3. `compute/regulatory/gaap_ifrs.py` (363 lines)
   - `classify_gaap_category()`: HTM/AFS/Trading
   - `classify_ifrs_category()`: Amortized Cost/FVOCI/FVTPL
   - `compute_impairment()`: GAAP impairment logic
   - `compute_gaap_valuation()`: GAAP carrying value
   - `compute_ifrs_valuation()`: IFRS carrying value with ECL

**Tests:**
4. `compute/tests/test_cecl.py` (277 lines, 13 tests)
5. `compute/tests/test_basel.py` (236 lines, 14 tests)
6. `compute/tests/test_gaap_ifrs.py` (386 lines, 22 tests)

### Modified

None.

## Commits

1. **f560595** - feat(04-02): implement CECL allowance calculation (REG-02)
   - ASC 326 multi-scenario probability-weighted ECL
   - Lifetime PD calculation from marginal annual PD curves
   - Segment-level ECL with issuer-based grouping
   - Stage classification for IFRS 9 / CECL alignment
   - 13 passing golden tests

2. **5681445** - feat(04-02): implement Basel III RWA calculation (REG-03)
   - Standardized approach risk-weighted asset calculation
   - Risk weight lookup with fallback logic
   - Aggregation by counterparty type and credit rating
   - Capital adequacy ratios (CET1, Tier 1, Total Capital)
   - 14 passing golden tests

3. **f9a8205** - feat(04-02): implement GAAP/IFRS valuation framework (REG-01)
   - GAAP classification: HTM/AFS/Trading by management intent
   - IFRS 9 classification: Amortized Cost/FVOCI/FVTPL
   - GAAP impairment: Other-than-temporary impairment (>10% decline)
   - IFRS ECL integration: Amortized cost less ECL allowance
   - 22 passing golden tests

## Success Criteria Verification

- [x] CECL allowance calculation implements ASC 326 multi-scenario approach with stage classification
- [x] Basel III RWA calculation uses standardized approach risk weights from regulatory reference
- [x] GAAP/IFRS valuation framework classifies positions correctly and computes impairment
- [x] All regulatory compute modules have golden tests with known scenarios (49 tests total)
- [x] Modules integrate with Phase 2 risk analytics (PD curves, LGD assumptions)
- [x] Code follows Phase 2 compute patterns (type hints, docstrings, error handling)

All 6 success criteria met.

## Next Steps

**Phase 4 Plan 03: Regulatory Analytics Service**
- Expose CECL, Basel, GAAP/IFRS calculations via REST endpoints
- Query interface for regulatory metrics
- Integration with portfolio and reference data services

**Phase 4 Plan 04: Regulatory Reporting**
- CECL allowance reports with scenario detail
- Basel III capital adequacy reports
- GAAP/IFRS carrying value and impairment reports
- Export to Excel/PDF for regulatory submission

## Self-Check: PASSED

### Files Created
- [x] compute/regulatory/cecl.py exists
- [x] compute/regulatory/basel.py exists
- [x] compute/regulatory/gaap_ifrs.py exists
- [x] compute/tests/test_cecl.py exists
- [x] compute/tests/test_basel.py exists
- [x] compute/tests/test_gaap_ifrs.py exists

### Commits Verified
- [x] f560595: CECL allowance calculation
- [x] 5681445: Basel III RWA calculation
- [x] f9a8205: GAAP/IFRS valuation framework

### Test Execution
- [x] All 49 tests passing (13 CECL + 14 Basel + 22 GAAP/IFRS)
- [x] All modules importable
- [x] All exported functions verified

All self-check items verified successfully.
