#!/usr/bin/env python3
"""
DB Smoke Test – MVP Risk Platform

Verifies that required tables exist in the configured Postgres database.

Usage (PowerShell):
  $env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/iprs"
  python scripts/db_smoke_test.py

Exit codes:
  0 = success
  2 = missing tables
  3 = connection / auth error
"""

from __future__ import annotations

import os
import sys
from typing import Iterable, List, Set, Tuple

import psycopg
from psycopg.rows import dict_row


DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5432/iprs"

# ✅ Adjust this list if your schema names differ
REQUIRED_TABLES: List[Tuple[str, str]] = [
    ("public", "marketdata_snapshot"),
    ("public", "position_snapshot"),
    ("public", "run"),
    ("public", "run_task"),
    ("public", "valuation_result"),
]


def print_ok(msg: str) -> None:
    print(f"✅ PASS: {msg}")


def print_fail(msg: str) -> None:
    print(f"❌ FAIL: {msg}")


def print_warn(msg: str) -> None:
    print(f"⚠️  WARN: {msg}")


def fetch_existing_tables(conn) -> Set[Tuple[str, str]]:
    sql = """
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
      AND table_schema NOT IN ('pg_catalog', 'information_schema')
    """
    rows = conn.execute(sql).fetchall()
    return {(r["table_schema"], r["table_name"]) for r in rows}


def main() -> int:
    dsn = os.getenv("DATABASE_URL", DEFAULT_DSN)

    print("============================================================")
    print("DB Smoke Test – Required MVP Tables")
    print("============================================================")
    print(f"DATABASE_URL: {dsn}")
    print("")

    try:
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            # Quick connectivity check
            ver = conn.execute("SELECT version() AS v").fetchone()
            print_ok("Connected to Postgres")
            print(f"   {ver['v']}")
            print("")

            existing = fetch_existing_tables(conn)

            missing = []
            for schema, table in REQUIRED_TABLES:
                if (schema, table) in existing:
                    print_ok(f"Table exists: {schema}.{table}")
                else:
                    print_fail(f"Missing table: {schema}.{table}")
                    missing.append((schema, table))

            print("")
            if missing:
                print_fail(f"{len(missing)} required tables are missing.")
                print("Suggested next steps:")
                print(" - Run your DB migration / schema SQL scripts")
                print(" - Confirm DATABASE_URL points to the right DB")
                print(" - If using a non-public schema, update REQUIRED_TABLES in this script")
                return 2

            print_ok("All required MVP tables are present.")
            return 0

    except psycopg.OperationalError as e:
        print_fail("Could not connect to Postgres (OperationalError).")
        print("Details:")
        print(f"  {e}")
        print("")
        print("Suggested next steps:")
        print(" - Ensure Postgres is running")
        print(" - Verify DATABASE_URL user/password/host/port/dbname")
        print(" - If using SSL or special auth, ensure psycopg is configured accordingly")
        return 3

    except Exception as e:
        print_fail("Unexpected error during DB smoke test.")
        print(f"  {type(e).__name__}: {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
