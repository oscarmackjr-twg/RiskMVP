---
phase: 01-foundation-infrastructure
plan: 02
subsystem: compute
tags: [registry-pattern, extensibility, worker-refactor]
dependency_graph:
  requires: [compute/pricers/{fx_fwd,bond,loan}.py]
  provides: [pricer-registry-pattern]
  affects: [compute/worker/worker.py]
tech_stack:
  added: []
  patterns: [registry-pattern, auto-bootstrap]
key_files:
  created:
    - compute/pricers/registry.py
    - compute/tests/test_worker_registry.py
  modified:
    - compute/worker/worker.py
decisions:
  - Auto-bootstrap registry on module import (eliminates manual registration)
  - Registry raises ValueError for unknown product types (fail-fast principle)
  - Pricer functions remain standalone (backward-compatible, no base class required)
metrics:
  duration_seconds: 130
  completed_at: "2026-02-11T17:52:50Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  tests_added: 4
  commits: 2
---

# Phase 01 Plan 02: Pricer Registry Pattern Summary

**Refactored worker to use registry pattern, eliminating if/elif dispatch chain and enabling pricer extensibility.**

## Objective

Complete PLAT-06 (pricer registry pattern) by refactoring worker.py to dispatch pricing tasks via registry.get_pricer(product_type) instead of if/elif chains. Enables adding new pricers without modifying worker code.

## Tasks Completed

### Task 1: Replace if/elif dispatch in worker.py with registry lookup
**Status:** ✓ Complete
**Commit:** 9f70cd3
**Files:**
- Modified: `compute/worker/worker.py`
- Created: `compute/pricers/registry.py`

**Changes:**
- Refactored `price_position()` to use `registry.get_pricer(product_type)`
- Removed individual pricer imports (price_fx_fwd, price_bond, price_loan)
- Created registry module with `get_pricer()`, `register()`, and `registered_types()` functions
- Registry auto-bootstraps on import via `_bootstrap()` function
- All 3 existing pricers (FX_FWD, AMORT_LOAN, FIXED_BOND) registered automatically

**Verification:**
- All golden tests pass (test_fx_fwd_golden, test_bond_golden, test_loan_golden)
- `registered_types()` returns `['AMORT_LOAN', 'FIXED_BOND', 'FX_FWD']`
- Registry raises clear ValueError for unknown product types

### Task 2: Add test for registry pattern in worker
**Status:** ✓ Complete
**Commit:** 8761666
**Files:**
- Created: `compute/tests/test_worker_registry.py`

**Tests Added:**
1. `test_all_pricers_registered()` - Verifies all 3 pricers in registry
2. `test_unknown_product_type_raises()` - Validates clear error for unknown types
3. `test_registry_bootstrap_on_import()` - Confirms auto-bootstrap works
4. `test_get_pricer_returns_callable()` - Ensures registry returns callable functions

**Verification:**
- All 4 new tests pass
- Total test suite: 7 tests pass (3 golden + 4 registry)

## Deviations from Plan

None - plan executed exactly as written.

## Success Criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Worker uses registry.get_pricer() instead of if/elif chain | ✓ | Code inspection: worker.py lines 171-179 |
| All 3 existing pricers registered and functional | ✓ | `registered_types()` returns all 3, golden tests pass |
| All golden tests pass | ✓ | pytest compute/tests/ shows 7/7 passed |
| Unknown product types raise clear ValueError | ✓ | test_unknown_product_type_raises passes |
| Worker extensible without modification | ✓ | Registry pattern demonstrated |

## Architecture Impact

**Before:**
```python
if product_type == "FX_FWD":
    return price_fx_fwd(...)
elif product_type == "AMORT_LOAN":
    return price_loan(...)
elif product_type == "FIXED_BOND":
    return price_bond(...)
else:
    raise ValueError(...)
```

**After:**
```python
from compute.pricers.registry import get_pricer

pricer_fn = get_pricer(product_type)
return pricer_fn(position, instrument, market_snapshot, measures, scenario_id)
```

**Benefits:**
- Adding new pricers requires ZERO worker.py changes
- Clear separation of concerns (worker = orchestration, registry = dispatch)
- Type safety maintained (registry validates product_type)
- Fail-fast on unknown product types

## Technical Details

### Registry Pattern Implementation

**Registry Module Structure:**
- `_REGISTRY: Dict[str, PricerFn]` - Internal registry mapping
- `register(product_type, pricer_fn)` - Registration function
- `get_pricer(product_type)` - Lookup with validation
- `registered_types()` - Query registered types
- `_bootstrap()` - Auto-registration on import

**Auto-Bootstrap:**
Registry automatically imports and registers all existing pricers when the module is imported. This eliminates manual registration calls and ensures consistency.

**Backward Compatibility:**
Pricer functions remain standalone (no base class inheritance required). Existing pricers work unchanged with the registry pattern.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Auto-bootstrap on import | Eliminates manual registration, prevents missing pricers |
| ValueError for unknown types | Fail-fast principle, clear error messages |
| No base class required | Backward-compatible, simpler for pricer authors |
| Function-based registry | Matches existing pricer signatures, no refactoring needed |

## Test Coverage

| Test Category | Tests | Status |
|---------------|-------|--------|
| Golden (end-to-end pricer validation) | 3 | ✓ All pass |
| Registry integration | 4 | ✓ All pass |
| **Total** | **7** | **✓ All pass** |

## Next Steps

1. **Phase 01 Plan 03:** Error handling patterns (shared library setup)
2. **Phase 02:** Add 6 new institutional pricers using registry pattern (no worker changes needed)

## Files Modified

| File | Change | Lines |
|------|--------|-------|
| compute/worker/worker.py | Refactored to use registry | -13, +3 |
| compute/pricers/registry.py | Created registry module | +49 |
| compute/tests/test_worker_registry.py | Added integration tests | +45 |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 9f70cd3 | refactor | Replace if/elif dispatch with registry pattern |
| 8761666 | test | Add registry pattern integration tests |

## Self-Check: PASSED

**Created files verified:**
```
FOUND: compute/pricers/registry.py
FOUND: compute/tests/test_worker_registry.py
```

**Modified files verified:**
```
FOUND: compute/worker/worker.py
```

**Commits verified:**
```
FOUND: 9f70cd3
FOUND: 8761666
```

**Tests verified:**
```
pytest compute/tests/ -v
7 passed
```

**Registry state verified:**
```
sorted(registered_types()) = ['AMORT_LOAN', 'FIXED_BOND', 'FX_FWD']
```

---

*Summary completed: 2026-02-11T17:52:50Z*
*Duration: 130 seconds (~2 minutes)*
*Executor: Claude Sonnet 4.5*
