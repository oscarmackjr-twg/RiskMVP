-- Verification queries for Phase 4 Regulatory Analytics Schema (003)
-- Run these manually to verify schema migration

-- ============================================================================
-- Table Count Verification
-- ============================================================================

SELECT count(*) as table_count FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN (
    'audit_trail',
    'regulatory_reference',
    'model_governance',
    'alert_config',
    'alert_log',
    'regulatory_metrics'
);
-- Expected: 6

-- ============================================================================
-- Index Count Verification
-- ============================================================================

SELECT count(*) as index_count FROM pg_indexes
WHERE schemaname = 'public' AND tablename IN (
    'audit_trail',
    'regulatory_reference',
    'model_governance',
    'alert_config',
    'alert_log',
    'regulatory_metrics'
);
-- Expected: >=10

-- ============================================================================
-- Trigger Verification
-- ============================================================================

SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
  AND trigger_name LIKE '%audit%';
-- Expected: prevent_audit_modification_trigger on audit_trail for UPDATE and DELETE

-- ============================================================================
-- Detailed Table Structure Verification
-- ============================================================================

-- Audit trail columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'audit_trail'
ORDER BY ordinal_position;

-- Regulatory reference columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'regulatory_reference'
ORDER BY ordinal_position;

-- Model governance columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'model_governance'
ORDER BY ordinal_position;

-- ============================================================================
-- Test Immutability Trigger (should fail)
-- ============================================================================

BEGIN;

-- Insert test audit entry
INSERT INTO audit_trail (
    audit_id,
    audit_type,
    calculation_run_id,
    entity_type,
    entity_id,
    calculation_method,
    input_snapshot_id,
    input_version,
    assumptions_json,
    results_json,
    computed_at
) VALUES (
    'test-audit-immutability-1',
    'CECL',
    'test-run-1',
    'PORTFOLIO',
    'test-port-1',
    'ASC326_MULTI_SCENARIO',
    'snap-test-1',
    'v1.0.0',
    '{"pd_table_version": "moody_2026_q1", "lgd_assumption": 0.45}'::jsonb,
    '{"allowance_amount": 125000.50, "coverage_ratio": 0.015}'::jsonb,
    now()
);

-- Try to update (should raise exception: "Audit trail entries are immutable")
UPDATE audit_trail
SET audit_type = 'BASEL'
WHERE audit_id = 'test-audit-immutability-1';

-- If we reach here, trigger failed
ROLLBACK;

-- ============================================================================
-- Test CHECK Constraints (should fail)
-- ============================================================================

BEGIN;

-- Invalid audit_type (should fail)
INSERT INTO audit_trail (
    audit_id,
    audit_type,
    calculation_run_id,
    entity_type,
    entity_id,
    calculation_method,
    input_snapshot_id,
    input_version,
    assumptions_json,
    results_json,
    computed_at
) VALUES (
    'test-invalid-type',
    'INVALID_TYPE',  -- Not in CHECK constraint
    'test-run-2',
    'PORTFOLIO',
    'test-port-2',
    'TEST',
    'snap-test-2',
    'v1',
    '{}'::jsonb,
    '{}'::jsonb,
    now()
);

ROLLBACK;

-- ============================================================================
-- Test Regulatory Reference Temporal Queries
-- ============================================================================

BEGIN;

-- Insert test reference data with versioning
INSERT INTO regulatory_reference (ref_id, ref_type, entity_key, ref_value, effective_date, source)
VALUES
    ('rw-corp-aaa-v1', 'RISK_WEIGHT', 'CORPORATE/AAA', 0.20, '2023-01-01'::timestamptz, 'BASEL_III_2023'),
    ('rw-corp-aaa-v2', 'RISK_WEIGHT', 'CORPORATE/AAA', 0.25, '2024-01-01'::timestamptz, 'BASEL_III_2024'),
    ('rw-corp-aaa-v3', 'RISK_WEIGHT', 'CORPORATE/AAA', 0.22, '2025-01-01'::timestamptz, 'BASEL_III_2025');

-- Get current risk weight (should return 0.22 from 2025-01-01)
SELECT ref_value, effective_date
FROM regulatory_reference
WHERE ref_type = 'RISK_WEIGHT'
  AND entity_key = 'CORPORATE/AAA'
  AND effective_date <= now()
ORDER BY effective_date DESC
LIMIT 1;

-- Get risk weight as of 2024-06-01 (should return 0.25 from 2024-01-01)
SELECT ref_value, effective_date
FROM regulatory_reference
WHERE ref_type = 'RISK_WEIGHT'
  AND entity_key = 'CORPORATE/AAA'
  AND effective_date <= '2024-06-01'::timestamptz
ORDER BY effective_date DESC
LIMIT 1;

ROLLBACK;

-- ============================================================================
-- Test UPSERT Idempotency on regulatory_metrics
-- ============================================================================

BEGIN;

-- First insert
INSERT INTO regulatory_metrics (
    metric_id,
    metric_type,
    portfolio_node_id,
    as_of_date,
    metric_value,
    metric_breakdown_json
) VALUES (
    'cecl-test-port-2026-02-11',
    'CECL_ALLOWANCE',
    'test-port-1',
    '2026-02-11'::timestamptz,
    125000.50,
    '{"segment_a": 50000, "segment_b": 75000.50}'::jsonb
);

-- Attempt duplicate insert (should succeed via ON CONFLICT)
INSERT INTO regulatory_metrics (
    metric_id,
    metric_type,
    portfolio_node_id,
    as_of_date,
    metric_value,
    metric_breakdown_json
) VALUES (
    'cecl-test-port-2026-02-11-v2',
    'CECL_ALLOWANCE',
    'test-port-1',
    '2026-02-11'::timestamptz,
    130000.00,
    '{"segment_a": 52000, "segment_b": 78000}'::jsonb
)
ON CONFLICT (portfolio_node_id, metric_type, as_of_date)
DO UPDATE SET
    metric_value = EXCLUDED.metric_value,
    metric_breakdown_json = EXCLUDED.metric_breakdown_json;

-- Verify only one record exists
SELECT count(*) as count FROM regulatory_metrics
WHERE portfolio_node_id = 'test-port-1'
  AND metric_type = 'CECL_ALLOWANCE'
  AND as_of_date = '2026-02-11'::timestamptz;
-- Expected: 1

ROLLBACK;

-- ============================================================================
-- Verification Complete
-- ============================================================================

SELECT 'Schema verification queries complete. Review output above for any errors.' as status;
