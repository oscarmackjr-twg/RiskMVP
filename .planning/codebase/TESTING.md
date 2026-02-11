# Testing Patterns

**Analysis Date:** 2026-02-11

## Test Framework

**Runner:**
- pytest 7.4.0+ (specified in `pyproject.toml`)
- Config: `pyproject.toml` under `[tool.pytest.ini_options]`

**Assertion Library:**
- Custom assertions in `compute/tests/golden/_golden_utils.py`
- Standard Python assertions (`assert` keyword)

**Run Commands:**
```bash
pytest -q                    # Run all tests
pytest compute/tests/        # Run compute layer tests only
pytest compute/tests/golden/ # Run golden tests only
pytest -v                    # Verbose output
```

## Test File Organization

**Location:**
- Co-located in `compute/tests/` directory parallel to `compute/` source code
- Tests organized by type: `compute/tests/golden/` for golden tests

**Naming:**
- Test files start with `test_`: `test_bond_golden.py`, `test_fx_fwd_golden.py`, `test_loan_golden.py`
- Test functions start with `test_`: `test_bond_case1()`, `test_fx_fwd_case1()`, `test_loan_case1()`
- Utility modules start with underscore: `_golden_utils.py`

**Structure:**
```
compute/
├── tests/
│   ├── __init__.py
│   ├── golden/
│   │   ├── __init__.py
│   │   ├── _golden_utils.py       # Shared test utilities
│   │   ├── test_bond_golden.py    # Bond pricer tests
│   │   ├── test_fx_fwd_golden.py  # FX Forward pricer tests
│   │   ├── test_loan_golden.py    # Loan pricer tests
│   │   ├── inputs/                # Test input fixtures
│   │   │   ├── market_snapshot_case1.json
│   │   │   ├── bond_case1.json
│   │   │   └── ...
│   │   └── expected/              # Expected output fixtures
│   │       ├── bond_case1_expected.json
│   │       └── ...
```

## Test Structure

**Suite Organization:**
```python
from pathlib import Path
from compute.pricers.bond import price_bond
from ._golden_utils import load_json, assert_close

BASE = Path(__file__).parent
INPUTS = BASE / "inputs"
EXPECTED = BASE / "expected"

def test_bond_case1():
    market = load_json(INPUTS / "market_snapshot_case1.json")
    case = load_json(INPUTS / "bond_case1.json")
    exp = load_json(EXPECTED / "bond_case1_expected.json")

    out = price_bond(case["position"], case["instrument"], market, exp["measures"], exp["scenario_id"])
    for k, vexp in exp["expected"].items():
        assert_close(float(out[k]), float(vexp), float(exp["tolerances"][k]), k)
```

**Patterns:**
- **Setup:** Load JSON fixtures from `inputs/` directory into variables
- **Execution:** Call pricer function with position, instrument, market, measures, scenario
- **Assertion:** Loop through expected results and validate with tolerance using `assert_close()`
- **Teardown:** None (fixtures are immutable JSON, no cleanup needed)

## Mocking

**Framework:** No external mocking framework used (no `unittest.mock` or `pytest-mock`)

**Patterns:**
- Fixtures are JSON files, not mocked objects
- Market data is loaded from JSON: `load_json()` reads from file
- No database mocking (no service layer tests visible)
- Scenarios mocked via `apply_scenario()` function which modifies market snapshot copy

**What to Mock:**
- External APIs would be mocked if tested
- File I/O would use fixtures (currently using real files from `inputs/` directory)

**What NOT to Mock:**
- Quantlib curve calculations (tested with golden values)
- Pricing calculations (core logic tested directly)
- Market data structures (load from JSON fixtures)

## Fixtures and Factories

**Test Data:**
```json
// compute/tests/golden/inputs/bond_case1.json
{
  "position": {
    "position_id": "pos-123",
    "attributes": {
      "as_of_date": "2026-01-15",
      "accrued_interest": 0.5,
      "cashflows": [...]
    }
  },
  "instrument": {
    "instrument_id": "bond-456",
    "terms": {
      "coupon_rate": 0.05,
      ...
    }
  }
}
```

**Location:**
- Input fixtures: `compute/tests/golden/inputs/` (JSON files)
- Expected outputs: `compute/tests/golden/expected/` (JSON files with expected values and tolerances)
- Fixtures are data-driven: test data contains inputs and expected results

**Fixture Pattern:**
- Each test case has three JSON files:
  1. Market snapshot: `market_snapshot_case1.json` (shared across tests)
  2. Test case input: `{product}_case1.json` (position, instrument)
  3. Expected output: `{product}_case1_expected.json` (expected values, tolerances, measures, scenario_id)

**Tolerance Pattern:**
```json
{
  "expected": {
    "PV": 98.5,
    "DV01": -0.85
  },
  "tolerances": {
    "PV": 0.01,
    "DV01": 0.001
  },
  "measures": ["PV", "DV01"],
  "scenario_id": "BASE"
}
```

## Coverage

**Requirements:** Not explicitly enforced in `pyproject.toml`

**View Coverage:**
```bash
pytest --cov=compute --cov-report=html compute/tests/
pytest --cov=compute --cov-report=term compute/tests/
```

## Test Types

**Unit Tests:**
- Golden tests validate pricer output against known values
- Scope: Individual pricer functions (bond, loan, FX forward)
- Approach: Load fixture → Execute pricer → Assert against expected values with tolerance
- Location: `compute/tests/golden/test_*.py`
- Tests are independent (no shared state between tests)

**Integration Tests:**
- Not explicitly present in codebase
- Would test: Market data snapshot retrieval → Task fanout → Worker pricing

**E2E Tests:**
- Not present in codebase
- Would test: API calls → Orchestrator → Worker → Results API

**Service Tests:**
- Not found in `services/` directories
- No test files exist for: `marketdata_svc`, `run_orchestrator`, `results_api`
- Services are untested in current codebase

## Common Patterns

**Async Testing:**
- No async tests present (compute layer is synchronous)
- Service layer uses FastAPI but no test infrastructure for async endpoints

**Error Testing:**
- Not explicitly present in current golden tests
- Pricer functions raise exceptions (ValueError, KeyError) for missing data
- Error cases could be tested by providing invalid market snapshots or position attributes

**Floating-Point Assertions:**
```python
def assert_close(actual: float, expected: float, tol: float, name: str):
    if abs(actual - expected) > tol:
        raise AssertionError(f"{name} actual={actual} expected={expected} tol={tol}")
```
- Custom tolerance-based comparison (not direct equality)
- Tolerance specified per measure in expected output JSON
- Raises AssertionError with descriptive message on failure

## Test Utilities

**Helper Functions** (from `compute/tests/golden/_golden_utils.py`):

```python
def load_json(path: Path):
    """Load JSON from file path."""
    return json.loads(path.read_text(encoding="utf-8"))

def assert_close(actual: float, expected: float, tol: float, name: str):
    """Assert that actual value is within tolerance of expected.

    Raises AssertionError with descriptive message if not within tolerance.
    """
    if abs(actual - expected) > tol:
        raise AssertionError(f"{name} actual={actual} expected={expected} tol={tol}")
```

## Test Data Management

**Sharing Fixtures:**
- `market_snapshot_case1.json` is shared across pricer tests
- Each pricer test references same market snapshot
- No test setup/teardown fixtures (data is read-only JSON)

**Adding New Tests:**
1. Create test case JSON files in `compute/tests/golden/inputs/` and `expected/`
2. Create test function in appropriate test module: `compute/tests/golden/test_*.py`
3. Follow pattern: load JSON → call pricer → assert_close for each measure
4. Update expected outputs with correct tolerances based on acceptable error margin

---

*Testing analysis: 2026-02-11*
