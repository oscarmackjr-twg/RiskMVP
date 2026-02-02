# compute/worker/worker.py
from __future__ import annotations

import os
import time
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

import psycopg
from psycopg.rows import dict_row

LEASE_SECONDS = int(os.getenv("WORKER_LEASE_SECONDS", "60"))
SLEEP_SECONDS = float(os.getenv("WORKER_IDLE_SLEEP_SECONDS", "0.5"))

DB_DSN = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/iprs")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

@dataclass(frozen=True)
class Task:
    task_id: str
    run_id: str
    portfolio_node_id: str
    product_type: str
    position_snapshot_id: str
    hash_mod: int
    hash_bucket: int
    max_attempts: int

CLAIM_SQL = """
WITH candidate AS (
  SELECT task_id
  FROM run_task
  WHERE (status = 'QUEUED')
     OR (status = 'RUNNING' AND leased_until < now())
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
UPDATE run_task t
SET status = 'RUNNING',
    attempt = attempt + 1,
    leased_until = now() + (%(lease_seconds)s || ' seconds')::interval,
    updated_at = now()
FROM candidate
WHERE t.task_id = candidate.task_id
RETURNING t.task_id, t.run_id, t.portfolio_node_id, t.product_type,
          t.position_snapshot_id, t.hash_mod, t.hash_bucket, t.max_attempts, t.attempt;
"""

MARK_SUCCEEDED_SQL = """
UPDATE run_task
SET status = 'SUCCEEDED', leased_until = NULL, updated_at = now(), last_error = NULL
WHERE task_id = %(task_id)s;
"""

MARK_FAILED_SQL = """
UPDATE run_task
SET status = CASE
    WHEN attempt >= max_attempts THEN 'DEAD'
    ELSE 'FAILED'
  END,
  leased_until = NULL,
  updated_at = now(),
  last_error = %(err)s
WHERE task_id = %(task_id)s;
"""

REQUEUE_FAILED_SQL = """
UPDATE run_task
SET status = 'QUEUED', updated_at = now()
WHERE task_id = %(task_id)s AND status = 'FAILED';
"""

GET_POS_SNAPSHOT_SQL = """
SELECT payload_json
FROM position_snapshot
WHERE position_snapshot_id = %(psid)s;
"""

GET_MDS_SQL = """
SELECT payload_json
FROM marketdata_snapshot
WHERE snapshot_id = %(sid)s;
"""

GET_RUN_SQL = """
SELECT market_snapshot_id, model_set_id, measures, scenarios, as_of_time
FROM run
WHERE run_id = %(rid)s;
"""

UPSERT_RESULT_SQL = """
INSERT INTO valuation_result (
  run_id, tenant_id, position_id, instrument_id, portfolio_node_id, product_type,
  base_ccy, scenario_id, measures_json, compute_meta_json, input_hash
)
VALUES (
  %(run_id)s, %(tenant_id)s, %(position_id)s, %(instrument_id)s, %(portfolio_node_id)s, %(product_type)s,
  %(base_ccy)s, %(scenario_id)s, %(measures_json)s, %(compute_meta_json)s, %(input_hash)s
)
ON CONFLICT (run_id, position_id, scenario_id)
DO UPDATE SET
  measures_json = EXCLUDED.measures_json,
  compute_meta_json = EXCLUDED.compute_meta_json,
  input_hash = EXCLUDED.input_hash,
  created_at = now();
"""

def claim_task(conn: psycopg.Connection) -> Optional[Tuple[Task, int]]:
    row = conn.execute(CLAIM_SQL, {"lease_seconds": LEASE_SECONDS}).fetchone()
    if not row:
        return None
    task = Task(
        task_id=row["task_id"],
        run_id=row["run_id"],
        portfolio_node_id=row["portfolio_node_id"],
        product_type=row["product_type"],
        position_snapshot_id=row["position_snapshot_id"],
        hash_mod=row["hash_mod"],
        hash_bucket=row["hash_bucket"],
        max_attempts=row["max_attempts"],
    )
    attempt = int(row["attempt"])
    return task, attempt

def load_run_context(conn: psycopg.Connection, run_id: str) -> Dict[str, Any]:
    row = conn.execute(GET_RUN_SQL, {"rid": run_id}).fetchone()
    if not row:
        raise RuntimeError(f"Run not found: {run_id}")
    return dict(row)

def load_position_snapshot(conn: psycopg.Connection, psid: str) -> Dict[str, Any]:
    row = conn.execute(GET_POS_SNAPSHOT_SQL, {"psid": psid}).fetchone()
    if not row:
        raise RuntimeError(f"Position snapshot not found: {psid}")
    return row["payload_json"]

def load_market_snapshot(conn: psycopg.Connection, snapshot_id: str) -> Dict[str, Any]:
    row = conn.execute(GET_MDS_SQL, {"sid": snapshot_id}).fetchone()
    if not row:
        raise RuntimeError(f"Market snapshot not found: {snapshot_id}")
    return row["payload_json"]

def mark_succeeded(conn: psycopg.Connection, task_id: str) -> None:
    conn.execute(MARK_SUCCEEDED_SQL, {"task_id": task_id})

def mark_failed(conn: psycopg.Connection, task_id: str, err: str) -> None:
    conn.execute(MARK_FAILED_SQL, {"task_id": task_id, "err": err[:5000]})

def requeue_if_failed(conn: psycopg.Connection, task_id: str) -> None:
    conn.execute(REQUEUE_FAILED_SQL, {"task_id": task_id})

def in_bucket(position_id: str, hash_mod: int, hash_bucket: int) -> bool:
    h = int(hashlib.sha256(position_id.encode("utf-8")).hexdigest(), 16)
    return (h % hash_mod) == hash_bucket

def fetch_instrument(instrument_id: str) -> Dict[str, Any]:
    # MVP strategy: embed instrument JSON inside position.attributes.instrument when building snapshots.
    raise NotImplementedError("Wire instrument lookup (DB or service)")

def price_position(
    *,
    product_type: str,
    position: Dict[str, Any],
    instrument: Dict[str, Any],
    market_snapshot: Dict[str, Any],
    measures: List[str],
    scenario_id: str,
) -> Dict[str, float]:
    from compute.pricers.fx_fwd import price_fx_fwd
    from compute.pricers.loan import price_loan
    from compute.pricers.bond import price_bond

    if product_type == "FX_FWD":
        return price_fx_fwd(position, instrument, market_snapshot, measures, scenario_id)
    if product_type == "AMORT_LOAN":
        return price_loan(position, instrument, market_snapshot, measures, scenario_id)
    if product_type == "FIXED_BOND":
        return price_bond(position, instrument, market_snapshot, measures, scenario_id)
    raise ValueError(f"Unknown product_type: {product_type}")

def worker_main() -> None:
    print(f"[worker] starting {WORKER_ID} dsn={DB_DSN}")

    with psycopg.connect(DB_DSN, row_factory=dict_row) as conn:
        conn.autocommit = False

        while True:
            task = None
            try:
                with conn.transaction():
                    claimed = claim_task(conn)

                if not claimed:
                    time.sleep(SLEEP_SECONDS)
                    continue

                task, attempt = claimed
                start = utcnow()
                print(f"[worker] claimed task={task.task_id} run={task.run_id} attempt={attempt}")

                with conn.transaction():
                    run_ctx = load_run_context(conn, task.run_id)
                    market_snapshot_id = run_ctx["market_snapshot_id"]
                    market = load_market_snapshot(conn, market_snapshot_id)
                    pos_snapshot = load_position_snapshot(conn, task.position_snapshot_id)

                measures = list(run_ctx["measures"] or [])
                scenarios = run_ctx["scenarios"] or []

                scenario_ids = []
                for s in scenarios:
                    if isinstance(s, str):
                        scenario_ids.append(s)
                    elif isinstance(s, dict) and "scenario_set_id" in s:
                        scenario_ids.append(s["scenario_set_id"])
                if not scenario_ids:
                    scenario_ids = ["BASE"]

                positions = pos_snapshot["positions"]
                shard_positions = [
                    p for p in positions
                    if p["product_type"] == task.product_type
                    and in_bucket(p["position_id"], task.hash_mod, task.hash_bucket)
                ]

                for scenario_id in scenario_ids:
                    for p in shard_positions:
                        instrument_id = p["instrument_id"]
                        instrument = p.get("attributes", {}).get("instrument")
                        if instrument is None:
                            instrument = fetch_instrument(instrument_id)

                        measures_out = price_position(
                            product_type=task.product_type,
                            position=p,
                            instrument=instrument,
                            market_snapshot=market,
                            measures=measures,
                            scenario_id=scenario_id,
                        )

                        compute_meta = {
                            "engine_version": "pricer-0.1.0",
                            "code_hash": os.getenv("CODE_HASH", "git:dev"),
                            "env_hash": os.getenv("ENV_HASH", "docker:dev"),
                            "worker_id": WORKER_ID,
                            "start_time": start.isoformat(),
                            "end_time": utcnow().isoformat(),
                            "attempt": attempt,
                        }

                        input_hash = sha256_json({
                            "run_id": task.run_id,
                            "position": p,
                            "instrument": instrument,
                            "market_snapshot_id": market_snapshot_id,
                            "scenario_id": scenario_id,
                        })

                        with conn.transaction():
                            conn.execute(
                                UPSERT_RESULT_SQL,
                                {
                                    "run_id": task.run_id,
                                    "tenant_id": "INTERNAL",
                                    "position_id": p["position_id"],
                                    "instrument_id": instrument_id,
                                    "portfolio_node_id": task.portfolio_node_id,
                                    "product_type": task.product_type,
                                    "base_ccy": "USD",
                                    "scenario_id": scenario_id,
                                    "measures_json": json.dumps(measures_out),
                                    "compute_meta_json": json.dumps(compute_meta),
                                    "input_hash": input_hash,
                                },
                            )

                with conn.transaction():
                    mark_succeeded(conn, task.task_id)

                print(f"[worker] succeeded task={task.task_id} positions={len(shard_positions)}")

            except Exception as e:
                err = repr(e)
                print(f"[worker] error: {err}")

                if task is not None:
                    try:
                        with conn.transaction():
                            mark_failed(conn, task.task_id, err)
                            requeue_if_failed(conn, task.task_id)
                    except Exception as e2:
                        print(f"[worker] failed to mark task failed: {repr(e2)}")

                time.sleep(0.2)

if __name__ == "__main__":
    worker_main()
