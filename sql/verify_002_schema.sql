-- Verification script for Phase 3 schema (002_portfolio_data_services.sql)
-- Run this after applying the migration to verify all tables and indexes exist

-- Count Phase 3 tables
SELECT
  'Phase 3 Tables' AS check_type,
  count(*) AS actual,
  9 AS expected,
  CASE WHEN count(*) = 9 THEN 'PASS' ELSE 'FAIL' END AS status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'portfolio_node',
    'position',
    'portfolio_snapshot',
    'reference_data',
    'rating_history',
    'fx_spot',
    'market_data_feed',
    'data_lineage',
    'ingestion_batch'
  );

-- List all Phase 3 tables
SELECT
  'Table existence' AS check_type,
  table_name,
  'EXISTS' AS status
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'portfolio_node',
    'position',
    'portfolio_snapshot',
    'reference_data',
    'rating_history',
    'fx_spot',
    'market_data_feed',
    'data_lineage',
    'ingestion_batch'
  )
ORDER BY table_name;

-- Count indexes on Phase 3 tables
SELECT
  'Phase 3 Indexes' AS check_type,
  count(*) AS actual,
  '>=13' AS expected,
  CASE WHEN count(*) >= 13 THEN 'PASS' ELSE 'FAIL' END AS status
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'portfolio_node',
    'position',
    'portfolio_snapshot',
    'reference_data',
    'rating_history',
    'fx_spot',
    'market_data_feed',
    'data_lineage',
    'ingestion_batch'
  );

-- List all indexes on Phase 3 tables
SELECT
  'Index existence' AS check_type,
  tablename,
  indexname
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'portfolio_node',
    'position',
    'portfolio_snapshot',
    'reference_data',
    'rating_history',
    'fx_spot',
    'market_data_feed',
    'data_lineage',
    'ingestion_batch'
  )
ORDER BY tablename, indexname;

-- Check foreign keys to Phase 1 tables
SELECT
  'Foreign Key Integrity' AS check_type,
  conname AS constraint_name,
  conrelid::regclass AS from_table,
  confrelid::regclass AS to_table
FROM pg_constraint
WHERE contype = 'f'
  AND (
    conrelid::regclass::text LIKE '%portfolio%'
    OR conrelid::regclass::text LIKE '%position%'
    OR conrelid::regclass::text LIKE '%reference%'
    OR conrelid::regclass::text LIKE '%rating%'
  );

-- Test insert into each table (and rollback to avoid side effects)
BEGIN;

-- Test portfolio_node
INSERT INTO portfolio_node (portfolio_node_id, name, node_type)
VALUES ('test-fund-1', 'Test Fund', 'FUND');

-- Test reference_data
INSERT INTO reference_data (entity_id, entity_type, name)
VALUES ('test-issuer-1', 'ISSUER', 'Test Issuer Corp');

-- Test rating_history (requires reference_data)
INSERT INTO rating_history (rating_id, entity_id, agency, rating, as_of_date)
VALUES ('test-rating-1', 'test-issuer-1', 'SP', 'AAA', now());

-- Test fx_spot
INSERT INTO fx_spot (pair, snapshot_id, spot_rate, as_of_date, source)
VALUES ('EUR/USD', 'test-snapshot-1', 1.10, now(), 'TEST');

-- Test market_data_feed
INSERT INTO market_data_feed (feed_id, feed_type, as_of_date, source, payload_json, payload_hash)
VALUES ('test-feed-1', 'YIELD_CURVE', now(), 'TEST', '{"test": true}'::jsonb, 'test-hash-1');

-- Test data_lineage
INSERT INTO data_lineage (lineage_id, feed_type, source_system, source_identifier, ingested_at, transformation_chain)
VALUES ('test-lineage-1', 'YIELD_CURVE', 'TEST', 'test-id', now(), ARRAY['RECEIVE', 'VALIDATE', 'STORE']);

-- Test ingestion_batch
INSERT INTO ingestion_batch (batch_id, batch_type)
VALUES ('test-batch-1', 'MARKET_DATA');

-- Test portfolio_snapshot
INSERT INTO portfolio_snapshot (snapshot_id, portfolio_node_id, as_of_date, payload_json, payload_hash)
VALUES ('test-snap-1', 'test-fund-1', now(), '{"positions": []}'::jsonb, 'test-hash-snap-1');

-- All inserts succeeded
SELECT 'Test Inserts' AS check_type, 'PASS' AS status;

ROLLBACK;

SELECT 'Schema Validation Complete' AS message;
