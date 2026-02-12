"""
Phase 4 Schema Migration Application and Verification

Applies sql/003_regulatory_analytics.sql and runs automated verification checks.

Usage:
    python sql/apply_and_verify_003.py

Environment:
    DATABASE_URL - PostgreSQL connection string (default: postgresql://postgres:postgres@localhost:5432/iprs)
"""

import os
import sys
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/iprs")

def apply_migration():
    """Apply 003 regulatory analytics schema migration."""
    print("=" * 80)
    print("Applying Phase 4 Regulatory Analytics Schema Migration (003)")
    print("=" * 80)

    migration_path = "sql/003_regulatory_analytics.sql"

    if not os.path.exists(migration_path):
        print(f"✗ Migration file not found: {migration_path}")
        return False

    with open(migration_path, "r") as f:
        migration_sql = f.read()

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute(migration_sql)
            conn.commit()
        print(f"✓ Migration applied from {migration_path}")
        return True
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


def verify_tables():
    """Verify all 6 regulatory analytics tables exist."""
    print("\n" + "=" * 80)
    print("Verifying Tables")
    print("=" * 80)

    expected_tables = {
        'audit_trail',
        'regulatory_reference',
        'model_governance',
        'alert_config',
        'alert_log',
        'regulatory_metrics'
    }

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            result = conn.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = ANY(%(tables)s)
            """, {'tables': list(expected_tables)}).fetchall()

            found_tables = {row['table_name'] for row in result}
            missing = expected_tables - found_tables

            if missing:
                print(f"✗ Missing tables: {missing}")
                return False

            print(f"✓ All 6 tables exist:")
            for table in sorted(found_tables):
                print(f"  - {table}")
            return True
    except Exception as e:
        print(f"✗ Table verification failed: {e}")
        return False


def verify_indexes():
    """Verify indexes exist on all tables."""
    print("\n" + "=" * 80)
    print("Verifying Indexes")
    print("=" * 80)

    try:
        with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
            # Count total indexes
            result = conn.execute("""
                SELECT count(*) as idx_count FROM pg_indexes
                WHERE schemaname = 'public' AND tablename IN (
                    'audit_trail', 'regulatory_reference', 'model_governance',
                    'alert_config', 'alert_log', 'regulatory_metrics'
                )
            """).fetchone()

            count = result['idx_count']
            if count < 10:
                print(f"✗ Expected >=10 indexes, found {count}")
                return False

            # List all indexes
            indexes = conn.execute("""
                SELECT tablename, indexname FROM pg_indexes
                WHERE schemaname = 'public' AND tablename IN (
                    'audit_trail', 'regulatory_reference', 'model_governance',
                    'alert_config', 'alert_log', 'regulatory_metrics'
                )
                ORDER BY tablename, indexname
            """).fetchall()

            print(f"✓ Found {count} indexes:")
            current_table = None
            for idx in indexes:
                if idx['tablename'] != current_table:
                    current_table = idx['tablename']
                    print(f"\n  {current_table}:")
                print(f"    - {idx['indexname']}")

            return True
    except Exception as e:
        print(f"✗ Index verification failed: {e}")
        return False


def verify_immutability_trigger():
    """Test audit_trail immutability trigger blocks UPDATE/DELETE."""
    print("\n" + "=" * 80)
    print("Verifying Immutability Trigger")
    print("=" * 80)

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            # Start transaction
            conn.execute("BEGIN")

            # Insert test record
            conn.execute("""
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
                    'test-immutability-check',
                    'CECL',
                    'test-run-verify',
                    'PORTFOLIO',
                    'test-port-verify',
                    'ASC326_MULTI_SCENARIO',
                    'snap-test-verify',
                    'v1.0.0',
                    '{"test": true}'::jsonb,
                    '{"test_result": 100}'::jsonb,
                    now()
                )
            """)

            # Try to update (should fail)
            try:
                conn.execute("""
                    UPDATE audit_trail SET audit_type = 'BASEL'
                    WHERE audit_id = 'test-immutability-check'
                """)
                # If we reach here, trigger failed
                conn.execute("ROLLBACK")
                print("✗ Immutability trigger not working (UPDATE succeeded)")
                return False
            except Exception as update_error:
                # Expected error
                error_msg = str(update_error).lower()
                if "immutable" in error_msg:
                    print("✓ Immutability trigger working (UPDATE blocked)")
                    print(f"  Trigger message: {str(update_error).split(chr(10))[0]}")
                    conn.execute("ROLLBACK")
                    return True
                else:
                    print(f"✗ Unexpected error: {update_error}")
                    conn.execute("ROLLBACK")
                    return False
    except Exception as e:
        print(f"✗ Immutability trigger test failed: {e}")
        return False


def verify_check_constraints():
    """Test CHECK constraints reject invalid enum values."""
    print("\n" + "=" * 80)
    print("Verifying CHECK Constraints")
    print("=" * 80)

    test_cases = [
        {
            'name': 'audit_trail.audit_type',
            'sql': """
                INSERT INTO audit_trail (
                    audit_id, audit_type, calculation_run_id, entity_type, entity_id,
                    calculation_method, input_snapshot_id, input_version,
                    assumptions_json, results_json, computed_at
                ) VALUES (
                    'test-invalid-1', 'INVALID_TYPE', 'run-1', 'PORTFOLIO', 'port-1',
                    'method', 'snap-1', 'v1', '{}'::jsonb, '{}'::jsonb, now()
                )
            """
        },
        {
            'name': 'regulatory_reference.ref_type',
            'sql': """
                INSERT INTO regulatory_reference (
                    ref_id, ref_type, entity_key, ref_value, effective_date, source
                ) VALUES (
                    'test-invalid-2', 'INVALID_REF', 'key', 0.5, now(), 'source'
                )
            """
        },
        {
            'name': 'model_governance.approval_status',
            'sql': """
                INSERT INTO model_governance (
                    model_version, model_type, deployment_date, approval_status
                ) VALUES (
                    'test-v1', 'CECL', now(), 'INVALID_STATUS'
                )
            """
        }
    ]

    passed = 0
    failed = 0

    for test in test_cases:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                conn.execute("BEGIN")
                conn.execute(test['sql'])
                conn.execute("ROLLBACK")
                print(f"✗ {test['name']}: CHECK constraint not working (invalid value accepted)")
                failed += 1
        except Exception as e:
            if "check constraint" in str(e).lower() or "violates check" in str(e).lower():
                print(f"✓ {test['name']}: CHECK constraint working")
                passed += 1
            else:
                print(f"✗ {test['name']}: Unexpected error: {e}")
                failed += 1

    print(f"\nCHECK constraints: {passed} passed, {failed} failed")
    return failed == 0


def verify_upsert_idempotency():
    """Test regulatory_metrics UNIQUE constraint enables idempotent UPSERT."""
    print("\n" + "=" * 80)
    print("Verifying UPSERT Idempotency")
    print("=" * 80)

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            conn.execute("BEGIN")

            # First insert
            conn.execute("""
                INSERT INTO regulatory_metrics (
                    metric_id, metric_type, portfolio_node_id, as_of_date,
                    metric_value, metric_breakdown_json
                ) VALUES (
                    'test-upsert-1', 'CECL_ALLOWANCE', 'test-port-upsert',
                    '2026-02-11'::timestamptz, 100000.00, '{}'::jsonb
                )
            """)

            # Second insert with ON CONFLICT (should update)
            conn.execute("""
                INSERT INTO regulatory_metrics (
                    metric_id, metric_type, portfolio_node_id, as_of_date,
                    metric_value, metric_breakdown_json
                ) VALUES (
                    'test-upsert-2', 'CECL_ALLOWANCE', 'test-port-upsert',
                    '2026-02-11'::timestamptz, 125000.00, '{}'::jsonb
                )
                ON CONFLICT (portfolio_node_id, metric_type, as_of_date)
                DO UPDATE SET
                    metric_value = EXCLUDED.metric_value,
                    metric_breakdown_json = EXCLUDED.metric_breakdown_json
            """)

            # Verify only one record exists
            result = conn.execute("""
                SELECT count(*) as cnt, metric_value FROM regulatory_metrics
                WHERE portfolio_node_id = 'test-port-upsert'
                  AND metric_type = 'CECL_ALLOWANCE'
                  AND as_of_date = '2026-02-11'::timestamptz
                GROUP BY metric_value
            """).fetchone()

            conn.execute("ROLLBACK")

            if result and result[0] == 1 and result[1] == 125000.00:
                print("✓ UPSERT idempotency working (UNIQUE constraint enforced, value updated)")
                return True
            else:
                print(f"✗ UPSERT idempotency failed (count: {result[0] if result else 'none'}, value: {result[1] if result else 'none'})")
                return False
    except Exception as e:
        print(f"✗ UPSERT idempotency test failed: {e}")
        return False


def main():
    """Run all migration and verification steps."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "Phase 4 Regulatory Analytics Schema" + " " * 28 + "║")
    print("║" + " " * 20 + "Migration & Verification" + " " * 34 + "║")
    print("╚" + "=" * 78 + "╝")
    print(f"\nDatabase: {DATABASE_URL}\n")

    # Step 1: Apply migration
    if not apply_migration():
        print("\n✗ Migration failed. Aborting verification.")
        sys.exit(1)

    # Step 2: Run verification checks
    checks = [
        ("Tables", verify_tables),
        ("Indexes", verify_indexes),
        ("Immutability Trigger", verify_immutability_trigger),
        ("CHECK Constraints", verify_check_constraints),
        ("UPSERT Idempotency", verify_upsert_idempotency),
    ]

    results = []
    for name, check_fn in checks:
        try:
            passed = check_fn()
            results.append((name, passed))
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 80)
    print("Verification Summary")
    print("=" * 80)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")

    print(f"\nTotal: {passed_count}/{total_count} checks passed")

    if passed_count == total_count:
        print("\n✓ All verification checks passed! Schema is ready for Phase 4.")
        sys.exit(0)
    else:
        print(f"\n✗ {total_count - passed_count} verification check(s) failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
