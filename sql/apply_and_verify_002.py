#!/usr/bin/env python3
"""
Apply Phase 3 schema migration and verify structure.

Usage:
    python sql/apply_and_verify_002.py

Requires DATABASE_URL environment variable or default localhost connection.
"""

import os
import sys
import psycopg
from pathlib import Path

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/iprs")
SQL_DIR = Path(__file__).parent

def apply_migration():
    """Apply 002_portfolio_data_services.sql migration."""
    migration_file = SQL_DIR / "002_portfolio_data_services.sql"

    print(f"Applying migration: {migration_file}")

    try:
        with psycopg.connect(DB_DSN) as conn:
            with open(migration_file, 'r') as f:
                sql = f.read()
            conn.execute(sql)
            conn.commit()
            print("✓ Migration applied successfully")
            return True
    except psycopg.Error as e:
        print(f"✗ Migration failed: {e}")
        return False
    except FileNotFoundError:
        print(f"✗ Migration file not found: {migration_file}")
        return False

def verify_tables():
    """Verify all 9 Phase 3 tables exist."""
    expected_tables = [
        'portfolio_node',
        'position',
        'portfolio_snapshot',
        'reference_data',
        'rating_history',
        'fx_spot',
        'market_data_feed',
        'data_lineage',
        'ingestion_batch'
    ]

    print("\nVerifying tables...")

    try:
        with psycopg.connect(DB_DSN) as conn:
            result = conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(%s)
                ORDER BY table_name
            """, [expected_tables]).fetchall()

            found_tables = [row[0] for row in result]

            if len(found_tables) == len(expected_tables):
                print(f"✓ All {len(expected_tables)} tables exist")
                for table in found_tables:
                    print(f"  - {table}")
                return True
            else:
                print(f"✗ Expected {len(expected_tables)} tables, found {len(found_tables)}")
                missing = set(expected_tables) - set(found_tables)
                if missing:
                    print(f"  Missing: {', '.join(missing)}")
                return False

    except psycopg.Error as e:
        print(f"✗ Verification failed: {e}")
        return False

def verify_indexes():
    """Verify indexes exist on Phase 3 tables."""
    print("\nVerifying indexes...")

    try:
        with psycopg.connect(DB_DSN) as conn:
            result = conn.execute("""
                SELECT count(*)
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
            """).fetchone()

            index_count = result[0]

            if index_count >= 13:
                print(f"✓ Found {index_count} indexes (expected >=13)")
                return True
            else:
                print(f"✗ Found {index_count} indexes (expected >=13)")
                return False

    except psycopg.Error as e:
        print(f"✗ Index verification failed: {e}")
        return False

def test_inserts():
    """Test that basic inserts work with constraints."""
    print("\nTesting inserts...")

    try:
        with psycopg.connect(DB_DSN) as conn:
            conn.autocommit = False

            # Test portfolio_node
            conn.execute("""
                INSERT INTO portfolio_node (portfolio_node_id, name, node_type)
                VALUES ('test-fund-1', 'Test Fund', 'FUND')
            """)

            # Test reference_data
            conn.execute("""
                INSERT INTO reference_data (entity_id, entity_type, name)
                VALUES ('test-issuer-1', 'ISSUER', 'Test Issuer')
            """)

            # Test rating_history (FK to reference_data)
            conn.execute("""
                INSERT INTO rating_history (rating_id, entity_id, agency, rating, as_of_date)
                VALUES ('test-rating-1', 'test-issuer-1', 'SP', 'AAA', now())
            """)

            # Rollback to avoid side effects
            conn.rollback()

            print("✓ Test inserts succeeded (rolled back)")
            return True

    except psycopg.Error as e:
        print(f"✗ Test inserts failed: {e}")
        return False

def main():
    """Run migration and verification."""
    print("=" * 60)
    print("Phase 3 Schema Migration and Verification")
    print("=" * 60)

    results = []

    # Apply migration
    results.append(("Migration", apply_migration()))

    # Verify tables
    results.append(("Tables", verify_tables()))

    # Verify indexes
    results.append(("Indexes", verify_indexes()))

    # Test inserts
    results.append(("Test Inserts", test_inserts()))

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
        all_passed = all_passed and passed

    print("=" * 60)

    if all_passed:
        print("\n✓ All checks passed - Phase 3 schema ready")
        return 0
    else:
        print("\n✗ Some checks failed - review errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
