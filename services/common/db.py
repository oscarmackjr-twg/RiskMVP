
import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/iprs")

@contextmanager
def db_conn():
    """
    Database connection context manager with automatic commit/rollback.

    Creates a new connection per request. For MVP with <10K positions and <100
    concurrent requests, this pattern is sufficient. Connection pooling can be
    added later if load testing shows need (e.g., psycopg_pool.ConnectionPool).

    Phase 3 services (Portfolio, Data Ingestion) will use this pattern for:
    - Portfolio hierarchy queries (recursive CTEs)
    - Multi-table joins (position + valuation_result + reference_data)
    - Complex aggregations (issuer, sector, geography)

    All queries should complete in <1s for 10K positions. If performance
    degrades, consider:
    - Adding connection pooling (psycopg_pool)
    - Database query optimization (indexes, EXPLAIN ANALYZE)
    - Caching frequently-accessed aggregations

    Usage:
        with db_conn() as conn:
            rows = conn.execute("SELECT * FROM portfolio_node").fetchall()
    """
    with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
