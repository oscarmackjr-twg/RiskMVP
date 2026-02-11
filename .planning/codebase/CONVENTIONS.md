# Coding Conventions

**Analysis Date:** 2026-02-11

## Naming Patterns

**Files:**
- Lowercase with underscores: `curve.py`, `fx_fwd.py`, `price_bond.py`
- Test files: `test_bond_golden.py`, `test_fx_fwd_golden.py` (test prefix)
- Private/internal utilities: `_golden_utils.py` (leading underscore)

**Functions:**
- snake_case for all functions: `price_bond()`, `price_fx_fwd()`, `_get_curve()`, `tenor_to_years()`
- Pricer functions follow pattern: `price_<instrument_type>()` (e.g., `price_bond`, `price_loan`, `price_fx_fwd`)
- Private/helper functions prefixed with underscore: `_get_curve()`, `_parse_date()`, `_extract_required_fields()`, `_bootstrap()`
- Utility functions are lowercase: `load_json()`, `sha256_json()`, `apply_scenario()`

**Variables:**
- snake_case for all variables: `market_snapshot`, `position_snapshot_id`, `curve_id`, `as_of_time`
- Single letter shortcuts for temporary values: `t` (time), `df` (discount factor), `c_ois` (curve OIS), `c_spread` (curve spread), `pv` (present value)
- Abbreviations follow pattern: `c_ois`, `c_for`, `df_ois`, `df_dom`, `df_ois_b` (bumped)
- Dictionary retrieval: `attrs`, `snap`, `out` (for output dict)

**Types:**
- PascalCase for classes: `AbstractPricer`, `ZeroCurve`, `PositionSnapshotIn`, `PositionSnapshotOut`, `RunRequestedV1`, `ErrorResponse`
- Pydantic models use PascalCase: `BaseModel` subclasses like `PositionSnapshotIn`, `ScenarioSpec`, `PortfolioScope`
- Type hints use capitalized names: `Dict[str, float]`, `List[str]`, `Tuple[float, float]`

## Code Style

**Formatting:**
- No explicit formatter configured in `pyproject.toml`
- PEP 8 style observed: 4-space indentation, max line length ~100 characters
- Imports are organized but not strictly enforced

**Linting:**
- No linting tool configured (no `.pylintrc`, `.flake8`, `ruff.toml`)
- Code follows PEP 8 conventions implicitly

## Import Organization

**Order:**
1. `from __future__ import annotations` (always at top)
2. Standard library imports (`os`, `json`, `hashlib`, `math`, `copy`, `datetime`, etc.)
3. Third-party imports (`psycopg`, `fastapi`, `pydantic`)
4. Local/relative imports (from `compute.*` or `services.*`)

**Path Aliases:**
- Absolute imports from project root: `from compute.pricers.bond import price_bond`
- Standard practice: `from compute.quantlib.curve import ZeroCurve, effective_df`
- No underscore aliases (use full names)

**Example import structure:**
```python
from __future__ import annotations
from typing import Dict, List
from datetime import date, datetime
from compute.quantlib.curve import ZeroCurve, effective_df
from compute.quantlib.scenarios import apply_scenario
```

## Error Handling

**Patterns:**
- Raise specific exceptions for domain errors: `ValueError`, `KeyError`, `HTTPException`
- Custom exception classes for REST API: `NotFoundError`, `ConflictError` (in `services/common/errors.py`)
- HTTPException from FastAPI for REST endpoints with explicit status codes: `HTTPException(status_code=400, detail="...")`
- Re-raise caught exceptions after logging/wrapping: See `services/common/db.py` pattern with try/except/raise
- Context managers used for resource cleanup: `with db_conn() as conn:` handles commit/rollback

**Error messages:**
- Descriptive with context: `f"Curve not found: {curve_id}"`
- Include variable values in error messages: `f"Invalid as_of_time string: {as_of_time}"`
- Database errors wrapped with detail: `f"DB error writing position_snapshot: {repr(e)}"`

## Logging

**Framework:** No logging framework configured; uses standard Python conventions

**Patterns:**
- Minimal logging in codebase (no logger calls visible)
- Error details passed to HTTP responses: `detail=f"DB error: {repr(e)}"`
- Use `repr()` for exception objects to include full traceback context

## Comments

**When to Comment:**
- Comments appear rarely (codebase is self-documenting)
- Comments used to explain MVP limitations: `# MVP: approximate maturity as 1M`
- Comments mark code sections: `# PV in USD for long base forward:`
- Comments for mathematical/financial concepts that need clarification

**Docstrings:**
- Module-level docstrings present: `"""Abstract base class for all pricers."""`
- Class docstrings: Present in abstract/base classes with detailed descriptions
- Function docstrings: Present for abstract methods and public APIs (compute layer)
- docstring format: Standard Python docstring with Args, Returns, Raises sections
- Example (from `compute/pricers/base.py`):
  ```python
  def price(
      self,
      position: dict,
      instrument: dict,
      market_snapshot: dict,
      measures: List[str],
      scenario_id: str,
  ) -> Dict[str, float]:
      """Compute requested measures for a position under a scenario.

      Args:
          position: Position dict with position_id, attributes, etc.
          instrument: Instrument definition with terms, conventions, etc.
          market_snapshot: Market data snapshot with curves, fx_spots, etc.
          measures: List of measure names to compute (e.g. ["PV", "DV01"]).
          scenario_id: Scenario identifier (e.g. "BASE", "RATES_PARALLEL_1BP").

      Returns:
          Dict mapping measure name to computed float value.
      """
  ```

## Function Design

**Size:** Functions are compact and focused
- Helper functions typically 5-15 lines
- Main pricing functions 10-30 lines
- Pricers have clear single responsibility: apply scenario, extract data, compute measures

**Parameters:**
- Type-hinted parameters: `position: dict`, `market_snapshot: dict`, `measures: List[str]`, `scenario_id: str`
- All public pricer functions follow standard signature: `(position: dict, instrument: dict, market_snapshot: dict, measures: List[str], scenario_id: str) -> Dict[str, float]`
- Private functions take specific typed parameters: `_get_curve(snapshot: dict, curve_id: str) -> ZeroCurve`

**Return Values:**
- Always return typed values: `-> Dict[str, float]`, `-> ZeroCurve`, `-> date`
- Pricers return dictionary of measure names to float values
- Helper functions return specific types, not None on error (raise exceptions instead)

## Module Design

**Exports:**
- Pricer modules export single function: `price_<type>()`
- Utility modules export functions or classes directly
- Private utilities use underscore prefix or hidden in helper modules

**Barrel Files:**
- Not used extensively; modules expose specific functions
- Registry pattern for pricers: `compute/pricers/registry.py` centralizes pricer dispatch
- No `__all__` exports observed (implicit public API)

## Database Access Pattern

**SQL Organization:**
- Raw SQL strings stored as uppercase constants near functions: `UPSERT_POSITION_SNAPSHOT_SQL = ""`
- Parameterized queries with dict binding: `%(position_snapshot_id)s`
- SQL defined in same file as usage (no separate schema files in Python code)

**Connection Pattern:**
- Context manager for DB connections: `with db_conn() as conn:`
- Connection factory in `services/common/db.py` handles autocommit=False, commit/rollback
- Row factory set to dict_row for dict-like access: `conn.row_factory = dict_row`

## Type Hints

**Usage:**
- Type hints present on function signatures throughout compute layer
- Pydantic models for REST API inputs/outputs (services layer)
- Generic types used: `Dict[str, float]`, `List[str]`, `Dict[str, Any]`
- Optional types used sparingly: `Optional[datetime]`, `Optional[str]`

## Pydantic Model Conventions

**Service Layer Models:**
- Input models end with `In`: `PositionSnapshotIn`
- Output models end with `Out`: `PositionSnapshotOut`
- Request models end with request suffix: `RunRequestedV1`
- Models inherit from `BaseModel`
- Field descriptions provided for clarity: `Field(..., description="...")`
- Default factories for optional lists: `Field(default_factory=lambda: [ScenarioSpec(...)])`

---

*Convention analysis: 2026-02-11*
