-- Phase 3: Portfolio & Data Services Schema Extension
-- Extends 001_mvp_core.sql with portfolio hierarchy, reference data, and data ingestion tables
-- All tables use text IDs, timestamptz for timestamps, jsonb for flexible metadata
BEGIN;

-- ============================================================================
-- PORTFOLIO DOMAIN TABLES
-- ============================================================================

-- Portfolio node: Hierarchical structure for FUND -> DESK -> BOOK -> STRATEGY
CREATE TABLE IF NOT EXISTS portfolio_node (
  portfolio_node_id  text PRIMARY KEY,
  parent_id          text REFERENCES portfolio_node(portfolio_node_id),
  name               text NOT NULL,
  node_type          text NOT NULL CHECK (node_type IN ('FUND', 'DESK', 'BOOK', 'STRATEGY')),
  tags_json          jsonb,
  metadata_json      jsonb,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS portfolio_node_parent_idx
  ON portfolio_node (parent_id);

-- Position: Links portfolio nodes to instruments with quantity, cost basis, and status
CREATE TABLE IF NOT EXISTS position (
  position_id        text PRIMARY KEY,
  portfolio_node_id  text NOT NULL REFERENCES portfolio_node(portfolio_node_id),
  instrument_id      text NOT NULL REFERENCES instrument(instrument_id),
  quantity           numeric NOT NULL,
  base_ccy           text NOT NULL DEFAULT 'USD',
  cost_basis         numeric,
  book_value         numeric,
  tags_json          jsonb,
  status             text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED', 'DELETED')),
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS position_portfolio_instrument_idx
  ON position (portfolio_node_id, instrument_id);

CREATE INDEX IF NOT EXISTS position_instrument_idx
  ON position (instrument_id);

-- Portfolio snapshot: Point-in-time position snapshots with deduplication via hash
CREATE TABLE IF NOT EXISTS portfolio_snapshot (
  snapshot_id        text PRIMARY KEY,
  portfolio_node_id  text NOT NULL REFERENCES portfolio_node(portfolio_node_id),
  as_of_date         timestamptz NOT NULL,
  payload_json       jsonb NOT NULL,
  payload_hash       text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  UNIQUE (portfolio_node_id, payload_hash)
);

CREATE INDEX IF NOT EXISTS portfolio_snapshot_portfolio_date_idx
  ON portfolio_snapshot (portfolio_node_id, as_of_date DESC);

-- ============================================================================
-- REFERENCE DATA TABLES
-- ============================================================================

-- Reference data: Issuers, sectors, geographies, currencies
CREATE TABLE IF NOT EXISTS reference_data (
  entity_id          text PRIMARY KEY,
  entity_type        text NOT NULL CHECK (entity_type IN ('ISSUER', 'SECTOR', 'GEOGRAPHY', 'CURRENCY')),
  name               text NOT NULL,
  ticker             text,
  cusip              text,
  isin               text,
  sector             text,
  geography          text,
  currency           text,
  parent_entity_id   text REFERENCES reference_data(entity_id),
  metadata_json      jsonb,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reference_data_type_name_idx
  ON reference_data (entity_type, name);

CREATE INDEX IF NOT EXISTS reference_data_ticker_idx
  ON reference_data (ticker);

CREATE INDEX IF NOT EXISTS reference_data_cusip_idx
  ON reference_data (cusip);

CREATE INDEX IF NOT EXISTS reference_data_isin_idx
  ON reference_data (isin);

-- Rating history: Time-series credit ratings from agencies
CREATE TABLE IF NOT EXISTS rating_history (
  rating_id          text PRIMARY KEY,
  entity_id          text NOT NULL REFERENCES reference_data(entity_id),
  agency             text NOT NULL CHECK (agency IN ('SP', 'MOODYS', 'FITCH', 'DBRS')),
  rating             text NOT NULL,
  outlook            text,
  as_of_date         timestamptz NOT NULL,
  effective_date     timestamptz,
  metadata_json      jsonb,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rating_history_entity_date_idx
  ON rating_history (entity_id, as_of_date DESC);

-- FX spot rates: Multi-currency exchange rates by snapshot
CREATE TABLE IF NOT EXISTS fx_spot (
  pair               text NOT NULL,
  snapshot_id        text NOT NULL,
  spot_rate          numeric NOT NULL,
  as_of_date         timestamptz NOT NULL,
  source             text NOT NULL,
  created_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (pair, snapshot_id)
);

CREATE INDEX IF NOT EXISTS fx_spot_snapshot_idx
  ON fx_spot (snapshot_id);

-- ============================================================================
-- DATA INGESTION TABLES
-- ============================================================================

-- Market data feed: Uploaded yield curves, credit spreads, FX spots, ratings
CREATE TABLE IF NOT EXISTS market_data_feed (
  feed_id            text PRIMARY KEY,
  feed_type          text NOT NULL CHECK (feed_type IN ('YIELD_CURVE', 'CREDIT_SPREAD', 'FX_SPOT', 'RATING')),
  as_of_date         timestamptz NOT NULL,
  source             text NOT NULL,
  payload_json       jsonb NOT NULL,
  payload_hash       text NOT NULL,
  validation_status  text NOT NULL DEFAULT 'PENDING' CHECK (validation_status IN ('PENDING', 'PASS', 'WARN', 'FAIL')),
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS market_data_feed_type_date_idx
  ON market_data_feed (feed_type, as_of_date DESC);

-- Data lineage: Tracks source system, transformation chain, quality checks
CREATE TABLE IF NOT EXISTS data_lineage (
  lineage_id         text PRIMARY KEY,
  feed_type          text NOT NULL,
  feed_id            text,
  source_system      text NOT NULL,
  source_identifier  text NOT NULL,
  ingested_at        timestamptz NOT NULL,
  transformation_chain text[] NOT NULL,
  quality_checks_passed boolean NOT NULL DEFAULT false,
  metadata_json      jsonb,
  created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS data_lineage_feed_idx
  ON data_lineage (feed_id);

-- Ingestion batch: Tracks bulk uploads with validation errors
CREATE TABLE IF NOT EXISTS ingestion_batch (
  batch_id           text PRIMARY KEY,
  batch_type         text NOT NULL CHECK (batch_type IN ('LOAN_SERVICING', 'MARKET_DATA', 'POSITION_UPLOAD')),
  source_file        text,
  record_count       int NOT NULL DEFAULT 0,
  validation_errors_json jsonb,
  status             text NOT NULL DEFAULT 'STARTED' CHECK (status IN ('STARTED', 'VALIDATING', 'COMPLETED', 'FAILED')),
  started_at         timestamptz NOT NULL DEFAULT now(),
  completed_at       timestamptz,
  created_by         text
);

CREATE INDEX IF NOT EXISTS ingestion_batch_type_started_idx
  ON ingestion_batch (batch_type, started_at DESC);

COMMIT;
