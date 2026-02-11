# Codebase Concerns

**Analysis Date:** 2026-02-11

## Tech Debt

**Duplicate Model Definitions in Run Orchestrator:**
- Issue: Classes `ScenarioSpec`, `PortfolioScope`, and `RunRequestedV1` are defined twice in the same file
- Files: `services/run_orchestrator/app/main.py` (lines 83-96 and 206-220)
- Impact: Code duplication creates maintenance burden; changes must be made in two places; confusing for developers
- Fix approach: Remove duplicate definitions on lines 206-220, keep first definition on lines 83-96, consolidate logic

**Unimplemented Pricers Blocking Production:**
- Issue: Multiple critical pricers raise `NotImplementedError` at runtime, blocking any portfolio with these product types
- Files:
  - `compute/pricers/abs_mbs.py` - ABS/MBS pricer
  - `compute/pricers/callable_bond.py` - Callable bonds
  - `compute/pricers/putable_bond.py` - Putable bonds
  - `compute/pricers/derivatives.py` - All derivatives
  - `compute/pricers/floating_rate.py` - Floating rate instruments
- Impact: Tasks will fail when worker encounters these product types; runs cannot complete; worker retry logic will exhaust attempts
- Fix approach: Implement pricers in priority order; add product type validation at run submission time to reject unsupported types early

**Hardcoded Database Connection Strings:**
- Issue: Default DSN strings hardcoded in multiple files with embedded credentials
- Files:
  - `services/common/db.py:7` - "postgresql://postgres:postgres@localhost:5432/iprs"
  - `compute/worker/worker.py:18` - Same default
  - `scripts/db_smoke_test.py:27` - Same default
  - `shared/config/settings.py:18` - Same default
- Impact: Credentials in source code; weak default passwords; exposes production connection details if committed
- Fix approach: Remove all hardcoded credentials; ensure `DATABASE_URL` env var is always required; use secrets management for defaults in production

**Stub Instrument Lookup Not Implemented:**
- Issue: `compute/worker/worker.py:169` raises `NotImplementedError` for instrument lookup
- Files: `compute/worker/worker.py:167-169`
- Impact: Falls back to embedded instrument in position.attributes.instrument; if that's missing, worker crashes; no graceful handling
- Fix approach: Wire instrument service lookup or validate instruments are embedded in position snapshot at submission time

## Known Bugs

**Duplicate Health Check Endpoints:**
- Symptoms: `/health` endpoint defined twice in same file (lines 98 and 222)
- Files: `services/run_orchestrator/app/main.py`
- Trigger: Import or deployment will use second definition
- Workaround: Second definition overrides first; requires developer awareness

**Broad Exception Handling in Worker:**
- Symptoms: Generic `except Exception as e` at line 294 catches all errors including system failures (OOM, disk full); all errors treated as task failures
- Files: `compute/worker/worker.py:294-305`
- Trigger: Any uncaught exception in pricing loop
- Workaround: None; task gets marked failed/dead even for non-recoverable system errors

## Security Considerations

**SQL Injection Risk in Results API:**
- Risk: `by` parameter is interpolated into SQL statement as unquoted identifier
- Files: `services/results_api/app/main.py:28-36`
- Current mitigation: Parameter restricted to `Literal["portfolio_node_id","product_type"]` in type hint (client-side protection only)
- Recommendations:
  - Add server-side validation before SQL construction
  - Use parameterized identifiers (PostgreSQL reserved word quoting) or allowlist validation
  - Test with crafted SQL injection payloads
  - Add logging for unexpected `by` values

**Measure Parameter Not Validated in Results Query:**
- Risk: `measure` parameter passed to JSONB extraction without validation; attacker could request arbitrary JSON keys
- Files: `services/results_api/app/main.py:38` - `measures_json ->> %(m)s`
- Current mitigation: None
- Recommendations:
  - Add allowlist of supported measures: ["PV", "DV01", "FX_DELTA", "ACCRUED_INTEREST"]
  - Validate measure parameter against allowlist before query execution
  - Return 400 error for unsupported measures

**Default PostgreSQL Credentials in Code:**
- Risk: Username `postgres`, password `postgres` in source code defaults
- Files: Multiple DB connection modules
- Current mitigation: Environment variable override exists but not enforced
- Recommendations:
  - Remove hardcoded defaults; make DATABASE_URL required
  - Document required environment variables for all deployment targets
  - Use secrets manager (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
  - Rotate default database password immediately
  - Scan git history for leaked credentials

## Performance Bottlenecks

**Deep Copy of Market Snapshot for Every Scenario:**
- Problem: `apply_scenario` uses `copy.deepcopy()` on entire market snapshot for each scenario
- Files: `compute/quantlib/scenarios.py:6`
- Cause: Inefficient for large snapshots with many curves; repeated for all positions in task
- Improvement path:
  - Pre-compute all scenario snapshots in orchestrator
  - Pass pre-computed snapshots to worker instead of applying on-the-fly
  - Cache computed scenario snapshots in memory

**Linear Search for Curves and FX Spots:**
- Problem: Each pricer iterates through entire curves/spots list to find by ID
- Files:
  - `compute/pricers/fx_fwd.py:8-11` and `13-17`
  - `compute/pricers/bond.py:8-12`
  - `compute/pricers/loan.py:8-12`
- Cause: O(n) lookup for each position; repeated for DV01 calculation (curve looked up twice)
- Improvement path:
  - Build dict index of curves by ID at snapshot load time
  - Build dict index of FX spots by pair at snapshot load time
  - Pass indexes to pricing functions instead of raw lists
  - Cache curve interpolation objects

**DV01 Calculation Duplicates PV Computation:**
- Problem: When requesting DV01, same curves are processed twice (BASE then bumped), same discount factors computed
- Files:
  - `compute/pricers/fx_fwd.py:47-51`
  - `compute/pricers/bond.py:46-57`
  - `compute/pricers/loan.py:52-64`
- Cause: Inefficient pricer design; no intermediate caching
- Improvement path:
  - Refactor to compute DV01 incrementally from PV
  - Cache curve discount factors within pricing function
  - Consider vectorized computation for multiple scenarios

## Fragile Areas

**Pricer Code Assumes Correct Input Data Shape:**
- Files: All pricers in `compute/pricers/`
- Why fragile:
  - No validation that instrument contains required fields
  - No validation that position.attributes has expected keys
  - Date parsing expects exact format "%Y-%m-%d" (line 24, 34 in loan.py, bond.py)
  - KeyError raised if curve not found or FX spot missing
  - No bounds checking on time calculations
- Safe modification:
  - Add input validation at start of each pricer
  - Document required fields in docstrings with examples
  - Use try-catch around date parsing with informative error messages
  - Return computed results with confidence/error field rather than raising
- Test coverage: Only 3 golden test cases; one per major product type (FX_FWD, LOAN, FIXED_BOND)

**Worker Task Claim-Execute-Commit Pattern with Shared Connection:**
- Files: `compute/worker/worker.py:192-307`
- Why fragile:
  - Single psycopg connection reused across multiple transactions (line 195-307)
  - If claim succeeds but data load fails, connection state unclear
  - Market snapshot/position snapshot could be deleted between claim and execution
  - No timeout handling if snapshot load takes too long
  - Error recovery is crude: mark failed, try again
- Safe modification:
  - Use separate connections for claim vs. data load
  - Add snapshot version/etag to detect changes
  - Add explicit timeout on snapshot queries
  - Add detailed logging at each transaction boundary

**Database Schema Lacks Foreign Key Constraints:**
- Files: `sql/001_mvp_core.sql` - lines 65, 83
- Why fragile:
  - `run` table references `marketdata_snapshot` but no ON DELETE cascade
  - `run_task` table references `position_snapshot` but no ON DELETE cascade
  - Orphaned data if snapshot is deleted while run is active
  - No foreign key on `valuation_result` -> `run`
- Safe modification: Add explicit cascade policies; test deletion scenarios

## Scaling Limits

**Single Hash Bucket Default:**
- Current capacity: `RUN_TASK_HASH_MOD=1` (single bucket)
- Limit: All positions in a task processed by one worker; no horizontal scaling of position processing
- Scaling path:
  - Increase `RUN_TASK_HASH_MOD` to N (creates N tasks per product type)
  - Hash function is already implemented (`in_bucket()` line 163-165)
  - Test with varied hash_mod values (1, 4, 8, 16)
  - Monitor task completion time vs. bucket count

**Synchronous Database Operations in Worker Loop:**
- Current capacity: Worker claims one task at a time; sleeps 0.5s between claims if idle
- Limit: Under high load, database connection pool can be exhausted; no async I/O
- Scaling path:
  - Consider async worker using asyncpg instead of psycopg (blocking I/O)
  - Implement connection pooling with configurable pool size
  - Add metrics: claim time, data load time, pricing time, commit time

**In-Memory Market Snapshot Caching:**
- Current capacity: Each worker loads full snapshot from database for every task
- Limit: Large snapshots (many curves, many FX pairs) repeated across workers
- Scaling path:
  - Add L1 cache (in-process) with TTL for recently-used snapshots
  - Add L2 cache (Redis) shared across workers if multi-process
  - Implement cache invalidation on snapshot update

## Dependencies at Risk

**psycopg v3 (PostgreSQL Driver):**
- Risk: Critical dependency; pinning strategy unknown
- Impact: If version incompatibility discovered, migration required
- Migration plan: Move to asyncpg for async support; or add connection pooling layer

**Pydantic Models Without Strict Validation:**
- Risk: Models use default Pydantic behavior; no custom validators for financial data
- Impact: Invalid data silently accepted (e.g., negative prices, invalid currencies)
- Migration plan: Add field validators for business logic; use `ConfigDict(validate_default=True)`

## Missing Critical Features

**No Audit Trail for Results:**
- Problem: Results computed but no record of who requested, when, from what code version
- Blocks: Regulatory compliance; debugging stale results
- Solution: Add audit table with request_id, requester, timestamp, code_version, git_sha

**No Run Status Transitions or Completion Logic:**
- Problem: Runs stay in QUEUED or RUNNING status; no transition to COMPLETED
- Blocks: Clients don't know when run is finished; results API queries in progress runs
- Solution: Add status machine; mark COMPLETED when all tasks SUCCEEDED

**No Intermediate Result Streaming:**
- Problem: Results written per-position; client must query after full completion
- Blocks: Interactive analysis during run; drill-down during computation
- Solution: Add streaming results endpoint; WebSocket for live updates

**No Error Aggregation:**
- Problem: Task-level errors marked in `run_task.last_error` but not aggregated to run
- Blocks: Users don't see summary of what failed
- Solution: Add error summary to `run.error_json` when tasks fail; expose in API

## Test Coverage Gaps

**Untested Scenario Application:**
- What's not tested: `apply_scenario()` only tested implicitly through golden tests
- Files: `compute/quantlib/scenarios.py`
- Risk: Scenario bumps could be applied incorrectly; DV01 calculations silently wrong
- Priority: HIGH - affects all risk metrics

**Untested Worker Edge Cases:**
- What's not tested:
  - Task lease expiration and requeue
  - Snapshot not found during task execution
  - Connection loss mid-transaction
  - Poison pill payloads (missing fields)
- Files: `compute/worker/worker.py`
- Risk: Worker crashes or hangs; no way to detect without manual testing
- Priority: HIGH - affects system reliability

**No API Contract Tests:**
- What's not tested: Service contracts between orchestrator, marketdata, results
- Files: `services/*/app/main.py`
- Risk: Breaking changes between services undetected; integration failures in deployment
- Priority: MEDIUM - affects multi-service deployments

**No End-to-End Tests:**
- What's not tested: Full run lifecycle: submit snapshot → create run → worker claims → results retrieved
- Files: None (test does not exist)
- Risk: Integration bugs between components; deployment regressions
- Priority: HIGH - critical for MVP validation

**Frontend Not Tested:**
- What's not tested: React components, API calls, error handling
- Files: `frontend/src/**/*`
- Risk: UI failures, broken layouts, error states not handled
- Priority: MEDIUM - affects user experience

---

*Concerns audit: 2026-02-11*
