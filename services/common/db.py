
import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/iprs")

@contextmanager
def db_conn():
    with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
