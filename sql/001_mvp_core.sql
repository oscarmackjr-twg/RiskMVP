-- MVP schema: run metadata, instruments, market data snapshots, position snapshots, results, publishing ledger, breaks
-- Base currency: USD
-- Loans valuation: accrual + DCF discounted on USD-OIS + LOAN-SPREAD
BEGIN;

CREATE TABLE IF NOT EXISTS instrument (
  instrument_id      text PRIMARY KEY,
  instrument_type    text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS instrument_version (
  instrument_id      text NOT NULL REFERENCES instrument(instrument_id),
  version            int  NOT NULL,
  status             text NOT NULL CHECK (status IN ('DRAFT','APPROVED','RETIRED')),
  terms_json         jsonb NOT NULL,
  conventions_json   jsonb NOT NULL,
  underlyings_json   jsonb,
  risk_modeling_json jsonb NOT NULL,
  governance_json    jsonb,
  created_by         text,
  created_at         timestamptz NOT NULL DEFAULT now(),
  approved_by        text,
  approved_at        timestamptz,
  PRIMARY KEY (instrument_id, version)
);

CREATE INDEX IF NOT EXISTS instrument_version_status_idx
  ON instrument_version (instrument_id, status);

CREATE TABLE IF NOT EXISTS marketdata_snapshot (
  snapshot_id    text PRIMARY KEY,
  as_of_time     timestamptz NOT NULL,
  vendor         text NOT NULL,
  universe_id    text NOT NULL,
  payload_json   jsonb NOT NULL,
  dq_status      text NOT NULL CHECK (dq_status IN ('PASS','WARN','FAIL')),
  payload_hash   text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS marketdata_snapshot_asof_idx
  ON marketdata_snapshot (as_of_time DESC);

CREATE TABLE IF NOT EXISTS position_snapshot (
  position_snapshot_id text PRIMARY KEY,
  as_of_time           timestamptz NOT NULL,
  portfolio_node_id    text NOT NULL,
  payload_json         jsonb NOT NULL,
  payload_hash         text NOT NULL,
  created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS position_snapshot_port_asof_idx
  ON position_snapshot (portfolio_node_id, as_of_time DESC);

CREATE TABLE IF NOT EXISTS run (
  run_id             text PRIMARY KEY,
  tenant_id          text NOT NULL DEFAULT 'INTERNAL',
  run_type           text NOT NULL CHECK (run_type IN ('EOD_OFFICIAL','INTRADAY','SANDBOX')),
  status             text NOT NULL CHECK (status IN ('QUEUED','RUNNING','CANCELLING','CANCELLED','FAILED','COMPLETED','PUBLISHED')),
  requested_by       text,
  requested_at       timestamptz NOT NULL DEFAULT now(),
  as_of_time         timestamptz NOT NULL,
  market_snapshot_id text NOT NULL REFERENCES marketdata_snapshot(snapshot_id),
  model_set_id       text,
  measures           text[] NOT NULL,
  scenarios          jsonb NOT NULL,
  portfolio_scope    jsonb NOT NULL,
  started_at         timestamptz,
  completed_at       timestamptz,
  summary_json       jsonb,
  error_json         jsonb
);

CREATE INDEX IF NOT EXISTS run_status_idx ON run (status, requested_at DESC);

CREATE TABLE IF NOT EXISTS run_task (
  task_id              text PRIMARY KEY,
  run_id               text NOT NULL REFERENCES run(run_id),
  portfolio_node_id    text NOT NULL,
  product_type         text NOT NULL,
  position_snapshot_id text NOT NULL REFERENCES position_snapshot(position_snapshot_id),
  hash_mod             int  NOT NULL,
  hash_bucket          int  NOT NULL,
  status               text NOT NULL CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','DEAD')),
  attempt              int  NOT NULL DEFAULT 0,
  max_attempts         int  NOT NULL DEFAULT 3,
  leased_until         timestamptz,
  last_error           text,
  created_at           timestamptz NOT NULL DEFAULT now(),
  updated_at           timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS run_task_run_idx ON run_task (run_id, status);
CREATE INDEX IF NOT EXISTS run_task_lease_idx ON run_task (status, leased_until);

CREATE TABLE IF NOT EXISTS valuation_result (
  run_id            text NOT NULL REFERENCES run(run_id),
  tenant_id         text NOT NULL DEFAULT 'INTERNAL',
  position_id       text NOT NULL,
  instrument_id     text NOT NULL,
  portfolio_node_id text NOT NULL,
  product_type      text NOT NULL,
  base_ccy          text NOT NULL DEFAULT 'USD',
  scenario_id       text NOT NULL DEFAULT 'BASE',
  measures_json     jsonb NOT NULL,
  compute_meta_json jsonb NOT NULL,
  input_hash        text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, position_id, scenario_id)
);

CREATE INDEX IF NOT EXISTS valuation_result_port_idx
  ON valuation_result (run_id, portfolio_node_id);

CREATE INDEX IF NOT EXISTS valuation_result_prod_idx
  ON valuation_result (run_id, product_type);

CREATE TABLE IF NOT EXISTS published_run (
  publish_id     text PRIMARY KEY,
  run_id         text NOT NULL UNIQUE REFERENCES run(run_id),
  published_at   timestamptz NOT NULL DEFAULT now(),
  published_by   text,
  inputs_json    jsonb NOT NULL,
  approvals_json jsonb NOT NULL,
  immutable_hash text NOT NULL
);

CREATE TABLE IF NOT EXISTS run_break (
  break_id          text PRIMARY KEY,
  run_id            text NOT NULL REFERENCES run(run_id),
  portfolio_node_id text NOT NULL,
  severity          text NOT NULL CHECK (severity IN ('LOW','MED','HIGH','CRITICAL')),
  break_type        text NOT NULL,
  description       text NOT NULL,
  metrics_json      jsonb NOT NULL,
  status            text NOT NULL CHECK (status IN ('OPEN','ASSIGNED','IN_PROGRESS','RESOLVED','WAIVED')),
  assigned_to       text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS run_break_run_idx ON run_break (run_id, status, severity);

COMMIT;
