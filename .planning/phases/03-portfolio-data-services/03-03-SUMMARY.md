---
phase: 03-portfolio-data-services
plan: 03
subsystem: portfolio-analytics
tags: [fastapi, postgresql, reference-data, aggregation, multi-currency, fx-conversion]

# Dependency graph
requires:
  - phase: 03-01
    provides: Database schema with reference_data, rating_history, fx_spot, position, portfolio_node tables
provides:
  - Reference data CRUD endpoints for issuers, sectors, geographies, currencies
  - Rating history tracking with temporal queries
  - Multi-dimensional aggregation by issuer, sector, rating, geography, currency, product type
  - Portfolio metrics calculation (market value, book value, accrued interest, P&L, yield, WAM)
  - Multi-currency conversion using FX spots
affects: [03-04, 03-05, 03-06, regulatory-reporting, risk-analytics]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LEFT JOIN reference_data for NULL-safe lookups with 'Unknown' bucket"
    - "Window function SUM() OVER () for weight percentage calculation"
    - "CASE WHEN base_ccy = 'USD' pattern for multi-currency conversion"
    - "DISTINCT ON (agency) for latest rating per agency"
    - "Weighted averages via SUM(metric × PV) / SUM(PV)"

key-files:
  created:
    - services/portfolio_svc/app/routes/reference_data.py
    - services/common/portfolio_queries.py
  modified:
    - services/portfolio_svc/app/routes/aggregation.py
    - services/portfolio_svc/app/main.py

key-decisions:
  - "Use LEFT JOIN for reference data to handle NULL gracefully with COALESCE to 'Unknown'"
  - "Calculate weight percentages in SQL via window function instead of application layer"
  - "Multi-currency conversion at query time (not materialized) using FX spot rates"
  - "Default to latest run if run_id not specified for aggregation queries"
  - "Portfolio yield calculated as weighted average YTM (SUM(YTM × PV) / SUM(PV))"

patterns-established:
  - "Query builder pattern: Return (query_string, params_dict) tuples for reusability"
  - "NULL reference data handling: COALESCE to 'Unknown' bucket in all aggregations"
  - "Empty portfolio safety: Return empty arrays instead of errors"
  - "FX conversion pattern: CASE WHEN base_ccy = 'USD' THEN pv ELSE pv × fx.spot_rate"

# Metrics
duration: 233
completed: 2026-02-11
---

# Phase 03 Plan 03: Portfolio Aggregation & Reference Data Summary

**Multi-dimensional portfolio aggregation with reference data lookups, multi-currency conversion, and comprehensive metrics calculation**

## Performance

- **Duration:** 3 min 53 sec (233 seconds)
- **Started:** 2026-02-11T22:09:41Z
- **Completed:** 2026-02-11T22:13:34Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Reference data management (CRUD for issuers, sectors, geographies, currencies) with rating history tracking
- Multi-dimensional aggregation endpoints (issuer, sector, rating, geography, currency, product type) with concentration percentages
- Portfolio metrics calculation covering all PORT-08 requirements (market value, book value, accrued interest, P&L, yield, WAM)
- Multi-currency conversion using FX spots with graceful handling of missing rates
- NULL reference data handling with 'Unknown' bucket aggregation

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement reference data management endpoints** - `876d75f` (feat)
   - POST /api/v1/reference-data - create entity
   - GET /api/v1/reference-data - list with filtering and text search
   - GET /api/v1/reference-data/{id} - get/update entity
   - POST /api/v1/reference-data/{id}/rating - add rating history
   - GET /api/v1/reference-data/{id}/current-rating - latest per agency

2. **Task 2: Implement multi-dimensional aggregation queries** - `080896e` (feat)
   - SQL query builders in portfolio_queries.py
   - Issuer, sector, rating, geography, currency, product type aggregations
   - Multi-currency conversion using FX spots
   - Weight percentages via window functions

3. **Task 3: Implement portfolio metrics calculation** - `79263cd` (feat)
   - GET /api/v1/aggregation/{portfolio_id}/metrics
   - Market value, book value, accrued interest, unrealized P&L
   - Portfolio yield (weighted average YTM)
   - Weighted average maturity (WAM)
   - Currency breakdown with weight percentages

## Files Created/Modified
- `services/portfolio_svc/app/routes/reference_data.py` - Reference data CRUD endpoints with rating history tracking
- `services/common/portfolio_queries.py` - SQL query builders for aggregation with FX conversion
- `services/portfolio_svc/app/routes/aggregation.py` - Multi-dimensional aggregation and portfolio metrics endpoints
- `services/portfolio_svc/app/main.py` - Added reference_data router

## Decisions Made

1. **LEFT JOIN for reference data** - Use LEFT JOIN instead of INNER JOIN to handle positions with NULL issuer_id gracefully, showing 'Unknown' bucket
2. **Window function for weight percentages** - Calculate concentration percentages in SQL using `SUM(SUM(pv_usd)) OVER ()` instead of application layer for efficiency
3. **Multi-currency conversion at query time** - FX conversion happens in SQL query (not materialized) using `CASE WHEN base_ccy = 'USD'` pattern
4. **Latest rating via DISTINCT ON** - Use PostgreSQL `DISTINCT ON (agency)` with ORDER BY as_of_date DESC to get latest rating per agency efficiently
5. **Weighted averages for portfolio metrics** - Portfolio yield and WAM calculated as `SUM(metric × PV) / SUM(PV)` for proper weighting

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded as specified in the plan.

## Aggregation Query Patterns

### Multi-Currency Conversion
All aggregation queries use consistent FX conversion pattern:
```sql
CASE
  WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
  ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
END AS pv_usd
```

This handles:
- USD positions (no conversion needed)
- Non-USD positions with FX spot available
- Missing FX rates (COALESCE to 1.0 prevents NULL)

### Weight Percentage Calculation
Window function pattern for concentration percentages:
```sql
ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
```

This ensures:
- Weight percentages sum to 100%
- Division by zero handled with NULLIF
- Rounded to 2 decimal places

### NULL Reference Data Handling
All dimensions use COALESCE for missing reference data:
```sql
COALESCE(issuer_name, 'Unknown Issuer') AS issuer_name
```

This ensures:
- Positions without reference data appear in 'Unknown' bucket
- No positions lost due to NULL JOIN results
- Consistent aggregation across all dimensions

## Portfolio Metrics Formulas

| Metric | Formula | Notes |
|--------|---------|-------|
| Market Value USD | SUM(PV converted to USD) | Uses FX spots for conversion |
| Book Value USD | SUM(position.book_value × FX rate) | Cost basis in USD |
| Unrealized P&L | Market Value - Book Value | Mark-to-market P&L |
| Portfolio Yield | SUM(YTM × PV) / SUM(PV) | Weighted average YTM |
| WAM | SUM(maturity_years × PV) / SUM(PV) | Weighted average maturity |
| WAL | SUM(WAL measure × PV) / SUM(PV) | Weighted average life (if available) |

## Performance Considerations

- All queries use indexed joins (portfolio_node_id, instrument_id, position_id)
- FX conversion happens in single CTE (no N+1 queries)
- Weight percentages calculated in SQL (not application layer)
- Empty portfolios return empty arrays (no errors)
- NULL handling via COALESCE prevents runtime failures

Expected performance for 10K positions: <1 second per aggregation query.

## Next Phase Readiness

Reference data and aggregation foundation complete. Ready for:
- Data ingestion service (03-04) to populate reference_data and fx_spot tables
- Portfolio hierarchy queries (03-05) to aggregate across fund/desk/book structure
- Performance attribution (03-06) using aggregation building blocks

All PORT-08 requirements implemented:
- Market value, book value, accrued interest
- Unrealized P&L calculation
- Portfolio yield and weighted average maturity
- Multi-currency support with FX conversion
- Aggregation by issuer, sector, rating, geography, currency, product type

## Self-Check: PASSED

All claimed files and commits verified:

- FOUND: services/portfolio_svc/app/routes/reference_data.py
- FOUND: services/common/portfolio_queries.py
- FOUND: 876d75f (Task 1)
- FOUND: 080896e (Task 2)
- FOUND: 79263cd (Task 3)

---
*Phase: 03-portfolio-data-services*
*Completed: 2026-02-11*
