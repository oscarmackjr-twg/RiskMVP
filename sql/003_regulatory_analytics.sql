-- Phase 4: Regulatory Analytics Schema Extension
-- Migration: 003_regulatory_analytics.sql
-- Purpose: Add regulatory analytics tables for audit trail, reference data,
--          model governance, and alerting infrastructure

BEGIN;

-- ============================================================================
-- 1. AUDIT_TRAIL - Immutable append-only log for regulatory calculations
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id text PRIMARY KEY,
    audit_type text NOT NULL CHECK (audit_type IN ('GAAP', 'IFRS', 'CECL', 'BASEL', 'MODEL_CHANGE')),
    calculation_run_id text NOT NULL,
    entity_type text NOT NULL CHECK (entity_type IN ('POSITION', 'PORTFOLIO', 'COUNTERPARTY')),
    entity_id text NOT NULL,
    calculation_method text NOT NULL,
    input_snapshot_id text NOT NULL,
    input_version text NOT NULL,
    assumptions_json jsonb NOT NULL,
    results_json jsonb NOT NULL,
    metadata_json jsonb,
    computed_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for audit_trail temporal and lookup queries
CREATE INDEX IF NOT EXISTS idx_audit_trail_calculation_run
    ON audit_trail(calculation_run_id);

CREATE INDEX IF NOT EXISTS idx_audit_trail_entity
    ON audit_trail(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_audit_trail_type_computed
    ON audit_trail(audit_type, computed_at DESC);

CREATE INDEX IF NOT EXISTS idx_audit_trail_snapshot
    ON audit_trail(input_snapshot_id);

-- Immutability trigger function
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit trail entries are immutable and cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce immutability
CREATE TRIGGER prevent_audit_modification_trigger
    BEFORE UPDATE OR DELETE ON audit_trail
    FOR EACH ROW
    EXECUTE FUNCTION prevent_audit_modification();

-- ============================================================================
-- 2. REGULATORY_REFERENCE - Risk weights, PD curves, LGD tables with versioning
-- ============================================================================

CREATE TABLE IF NOT EXISTS regulatory_reference (
    ref_id text PRIMARY KEY,
    ref_type text NOT NULL CHECK (ref_type IN ('RISK_WEIGHT', 'PD_CURVE', 'LGD_TABLE', 'Q_FACTOR')),
    entity_key text NOT NULL,
    ref_value numeric NOT NULL,
    effective_date timestamptz NOT NULL,
    expired_date timestamptz,
    source text NOT NULL,
    metadata_json jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Index for temporal lookups (get current value at as_of_date)
CREATE INDEX IF NOT EXISTS idx_regulatory_reference_temporal
    ON regulatory_reference(ref_type, entity_key, effective_date DESC);

-- ============================================================================
-- 3. MODEL_GOVERNANCE - Model versioning, backtesting, calibration tracking
-- ============================================================================

CREATE TABLE IF NOT EXISTS model_governance (
    model_version text PRIMARY KEY,
    model_type text NOT NULL CHECK (model_type IN ('CECL', 'BASEL_RWA', 'GAAP_VALUATION', 'IFRS_VALUATION')),
    git_hash text,
    deployment_date timestamptz NOT NULL,
    approval_status text NOT NULL CHECK (approval_status IN ('TESTING', 'APPROVED', 'DEPRECATED')),
    backtesting_results_json jsonb,
    calibration_date timestamptz,
    calibration_params_json jsonb,
    notes text,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Index for model type and deployment lookups
CREATE INDEX IF NOT EXISTS idx_model_governance_type_deployment
    ON model_governance(model_type, deployment_date DESC);

-- ============================================================================
-- 4. ALERT_CONFIG - Threshold configuration for monitoring
-- ============================================================================

CREATE TABLE IF NOT EXISTS alert_config (
    alert_id text PRIMARY KEY,
    alert_type text NOT NULL CHECK (alert_type IN ('DURATION_THRESHOLD', 'CONCENTRATION_LIMIT', 'CREDIT_DETERIORATION', 'LIQUIDITY_RATIO')),
    portfolio_node_id text,
    threshold_value numeric NOT NULL,
    threshold_operator text NOT NULL CHECK (threshold_operator IN ('GT', 'LT', 'EQ', 'GTE', 'LTE')),
    metric_name text NOT NULL,
    notification_channels text[],
    enabled boolean DEFAULT true,
    created_at timestamptz DEFAULT now()
);

-- Index for enabled alerts by portfolio
CREATE INDEX IF NOT EXISTS idx_alert_config_portfolio_enabled
    ON alert_config(portfolio_node_id, enabled);

-- ============================================================================
-- 5. ALERT_LOG - Alert trigger history
-- ============================================================================

CREATE TABLE IF NOT EXISTS alert_log (
    log_id text PRIMARY KEY,
    alert_id text REFERENCES alert_config(alert_id),
    triggered_at timestamptz NOT NULL DEFAULT now(),
    metric_value numeric NOT NULL,
    threshold_value numeric NOT NULL,
    portfolio_node_id text,
    position_id text,
    notification_sent boolean DEFAULT false,
    notification_sent_at timestamptz,
    resolved boolean DEFAULT false,
    resolved_at timestamptz
);

-- Indexes for alert history queries
CREATE INDEX IF NOT EXISTS idx_alert_log_alert_triggered
    ON alert_log(alert_id, triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_alert_log_portfolio_resolved
    ON alert_log(portfolio_node_id, resolved);

-- ============================================================================
-- 6. REGULATORY_METRICS - Cached regulatory calculations for query performance
-- ============================================================================

CREATE TABLE IF NOT EXISTS regulatory_metrics (
    metric_id text PRIMARY KEY,
    metric_type text NOT NULL CHECK (metric_type IN ('CECL_ALLOWANCE', 'BASEL_RWA', 'CAPITAL_RATIO', 'GAAP_VALUATION')),
    portfolio_node_id text NOT NULL,
    as_of_date timestamptz NOT NULL,
    metric_value numeric NOT NULL,
    metric_breakdown_json jsonb,
    calculation_run_id text,
    created_at timestamptz DEFAULT now(),
    UNIQUE (portfolio_node_id, metric_type, as_of_date)
);

-- Index for portfolio metrics time-series queries
CREATE INDEX IF NOT EXISTS idx_regulatory_metrics_portfolio_type_date
    ON regulatory_metrics(portfolio_node_id, metric_type, as_of_date DESC);

COMMIT;
