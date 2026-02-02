import os, json, hashlib
from psycopg.types.json import Json


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Any, Optional, Literal

from services.common.db import db_conn


def sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def load_positions_payload() -> Dict[str, Any]:
    path = os.getenv("POSITIONS_SNAPSHOT_PATH", "demo/inputs/positions.json")

    if not os.path.exists(path):
        raise RuntimeError(f"Positions payload file not found: {path}")

    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)



app = FastAPI(title="run-orchestrator", version="0.1.0")

class ScenarioSpec(BaseModel):
    scenario_set_id: str

class PortfolioScope(BaseModel):
    node_ids: List[str]

class RunRequestedV1(BaseModel):
    run_id: str
    run_type: Literal["EOD_OFFICIAL", "INTRADAY", "SANDBOX"]
    as_of_time: datetime
    market_snapshot_id: str
    portfolio_scope: PortfolioScope
    measures: List[str]
    scenarios: List[ScenarioSpec] = Field(default_factory=lambda: [ScenarioSpec(scenario_set_id="BASE")])

@app.get("/health")
def health():
    return {"ok": True}


UPSERT_POS_SNAPSHOT_SQL = """
INSERT INTO position_snapshot
  (position_snapshot_id, as_of_time, portfolio_node_id, payload_json, payload_hash)
VALUES
  (%(psid)s, %(asof)s, %(port)s, %(payload)s::jsonb, %(phash)s)
ON CONFLICT (position_snapshot_id) DO UPDATE SET
  payload_json = EXCLUDED.payload_json,
  payload_hash = EXCLUDED.payload_hash,
  created_at = now();
"""

INSERT_TASK_SQL = """
INSERT INTO run_task
  (task_id, run_id, portfolio_node_id, product_type, position_snapshot_id,
   hash_mod, hash_bucket, status, max_attempts)
VALUES
  (%(tid)s, %(rid)s, %(port)s, %(ptype)s, %(psid)s,
   %(hmod)s, %(hbucket)s, 'QUEUED', %(max_attempts)s)
ON CONFLICT (task_id) DO NOTHING;
"""


class ScenarioSpec(BaseModel):
    scenario_set_id: str

class PortfolioScope(BaseModel):
    node_ids: List[str]

class RunRequestedV1(BaseModel):
    run_id: str
    run_type: Literal["EOD_OFFICIAL", "INTRADAY", "SANDBOX"]
    as_of_time: datetime
    market_snapshot_id: str
    portfolio_scope: PortfolioScope
    measures: List[str]
    scenarios: List[ScenarioSpec] = Field(default_factory=lambda: [ScenarioSpec(scenario_set_id="BASE")])

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/v1/runs", status_code=201)
def create_run(req: RunRequestedV1):
    # 1) Insert run
    run_sql = """
    INSERT INTO "run"
      (run_id, tenant_id, run_type, status, requested_by, as_of_time,
       market_snapshot_id, measures, scenarios, portfolio_scope)
    VALUES
      (%(rid)s, 'INTERNAL', %(rtype)s, 'QUEUED', 'api', %(asof)s,
       %(msid)s, %(measures)s, %(scenarios)s::jsonb, %(scope)s::jsonb)
    ON CONFLICT (run_id) DO NOTHING;
    """

    # 2) Load/prepare a position snapshot payload for this run
    payload = load_positions_payload()

    # Ensure payload has the expected shape the worker uses: payload["positions"]
    positions = payload.get("positions") or []
    if not isinstance(positions, list) or len(positions) == 0:
        raise HTTPException(400, "positions snapshot payload missing positions[]")

    # product types present in the snapshot (fan out tasks by product type)
    product_types = sorted({p.get("product_type") for p in positions if p.get("product_type")})
    if not product_types:
        raise HTTPException(400, "positions[] missing product_type values")

    # Position snapshot id: deterministic per run
    psid = f"POS-{req.run_id}"

    # Hash for auditing/dedup
    phash = sha256_json(payload)

    # Fanout/sharding: start with 1 bucket (simple MVP)
    hash_mod = int(os.getenv("RUN_TASK_HASH_MOD", "1"))
    max_attempts = int(os.getenv("RUN_TASK_MAX_ATTEMPTS", "3"))

    with db_conn() as conn:
        # insert run
        conn.execute(run_sql, {
            "rid": req.run_id,
            "rtype": req.run_type,
            "asof": req.as_of_time,
            "msid": req.market_snapshot_id,
            "measures": req.measures,  # <-- text[] column, pass list
            "scenarios": Json([s.model_dump() for s in req.scenarios]),
            "scope": Json(req.portfolio_scope.model_dump()),
        })

        # insert/update position snapshot
        conn.execute(UPSERT_POS_SNAPSHOT_SQL, {
            "psid": psid,
            "asof": req.as_of_time,
            "port": req.portfolio_scope.node_ids[0],
            "payload": Json(payload),
            "phash": phash,
        })

        # create tasks (one per product_type per bucket)
        for ptype in product_types:
            for bucket in range(hash_mod):
                tid = f"TASK-{req.run_id}-{ptype}-{bucket}"
                conn.execute(INSERT_TASK_SQL, {
                    "tid": tid,
                    "rid": req.run_id,
                    "port": req.portfolio_scope.node_ids[0],
                    "ptype": ptype,
                    "psid": psid,
                    "hmod": hash_mod,
                    "hbucket": bucket,
                    "max_attempts": max_attempts,
                })

    return {"run_id": req.run_id, "status": "QUEUED", "position_snapshot_id": psid, "task_product_types": product_types}
