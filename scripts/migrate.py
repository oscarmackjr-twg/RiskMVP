"""Run SQL migrations against the IPRS database.

Usage (inside ECS container):
    python /app/scripts/migrate.py

Reads DATABASE_URL from environment. Executes migration files in order,
skipping any that have already been applied (tracked via a migrations table).
"""

import os
import sys
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/iprs",
)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql"

MIGRATION_FILES = [
    "001_mvp_core.sql",
    "002_portfolio_data_services.sql",
    "003_regulatory_analytics.sql",
]

TRACKING_DDL = """
CREATE TABLE IF NOT EXISTS _migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def run_migrations() -> None:
    print(f"Connecting to database...")
    with psycopg.connect(DATABASE_URL) as conn:
        conn.autocommit = False

        # Ensure tracking table exists
        with conn.cursor() as cur:
            cur.execute(TRACKING_DDL)
        conn.commit()

        for filename in MIGRATION_FILES:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM _migrations WHERE filename = %s",
                    (filename,),
                )
                if cur.fetchone():
                    print(f"  SKIP  {filename} (already applied)")
                    continue

            sql_path = MIGRATIONS_DIR / filename
            if not sql_path.exists():
                print(f"  ERROR {filename} not found at {sql_path}", file=sys.stderr)
                sys.exit(1)

            sql = sql_path.read_text(encoding="utf-8")
            print(f"  APPLY {filename} ({len(sql)} bytes)...")
            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO _migrations (filename) VALUES (%s)",
                    (filename,),
                )
            conn.commit()
            print(f"  OK    {filename}")

    print("All migrations applied successfully.")


if __name__ == "__main__":
    run_migrations()
