import os, json, hashlib
from psycopg.types.json import Json

from fastapi import HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from uuid import uuid4
from psycopg.rows import dict_row

from services.common.db import db_conn
from services.common.service_base import create_service_app

# --- Position Snapshot API models ---

class PositionSnapshotIn(BaseModel):
    # Either supply as_of_time+portfolio_node_id here,
    # or they can be inside payload_json; we'll prefer explicit fields.
    as_of_time: Optional[datetime] = None
    portfolio_node_id: Optional[str] = None

    # The raw positions payload your demo uses
    payload: Dict[str, Any] = Field(..., description="Positions snapshot payload JSON")

class PositionSnapshotOut(BaseModel):
    position_snapshot_id: str
    as_of_time: datetime
    portfolio_node_id: str
    payload_hash: str

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def _normalize_asof(dt: datetime) -> datetime:
    # Ensure timezone-aware
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def _extract_required_fields(payload: Dict[str, Any], explicit_asof: Optional[datetime], explicit_port: Optional[str]) -> tuple[datetime, str]:
    # Prefer explicit fields, fallback to payload fields
    as_of_time = explicit_asof or payload.get("as_of_time")
    portfolio_node_id = explicit_port or payload.get("portfolio_node_id")

    if not as_of_time:
        raise HTTPException(status_code=400, detail="Missing as_of_time (provide in body or payload.as_of_time)")
    if not portfolio_node_id:
        raise HTTPException(status_code=400, detail="Missing portfolio_node_id (provide in body or payload.portfolio_node_id)")

    # payload.as_of_time might be string; allow that
    if isinstance(as_of_time, str):
        # Accept both "2026-01-23T00:00:00Z" and full ISO
        try:
            as_of_time = datetime.fromisoformat(as_of_time.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid as_of_time string: {as_of_time}")

    return _normalize_asof(as_of_time), str(portfolio_node_id)


def sha256_json(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()



def load_positions_payload() -> Dict[str, Any]:
    path = os.getenv("POSITIONS_SNAPSHOT_PATH", "demo/inputs/positions.json")

    if not os.path.exists(path):
        raise RuntimeError(f"Positions payload file not found: {path}")

    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)




app = create_service_app(title="run-orchestrator", version="0.1.0")

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
    position_snapshot_id: Optional[str] = None
    measures: List[str]
    scenarios: List[ScenarioSpec] = Field(default_factory=lambda: [ScenarioSpec(scenario_set_id="BASE")])


UPSERT_POSITION_SNAPSHOT_SQL = """
INSERT INTO position_snapshot (
  position_snapshot_id, as_of_time, portfolio_node_id, payload_json, payload_hash, created_at
)
VALUES (
  %(position_snapshot_id)s,
  %(as_of_time)s,
  %(portfolio_node_id)s,
  %(payload_json)s,
  %(payload_hash)s,
  now()
)
ON CONFLICT (position_snapshot_id)
DO UPDATE SET
  as_of_time = EXCLUDED.as_of_time,
  portfolio_node_id = EXCLUDED.portfolio_node_id,
  payload_json = EXCLUDED.payload_json,
  payload_hash = EXCLUDED.payload_hash;
"""

GET_POSITION_SNAPSHOT_SQL = """
SELECT position_snapshot_id, as_of_time, portfolio_node_id, payload_hash, payload_json
FROM position_snapshot
WHERE position_snapshot_id = %(psid)s;
"""

@app.post("/api/v1/position-snapshots", response_model=PositionSnapshotOut, status_code=201)
def create_position_snapshot(req: PositionSnapshotIn):
    payload = req.payload
    as_of_time, portfolio_node_id = _extract_required_fields(payload, req.as_of_time, req.portfolio_node_id)

    # Deterministic hash of payload JSON for idempotency checks
    payload_hash = sha256_json(payload)

    # Choose an id:
    # - If caller provides payload.position_snapshot_id, use it
    # - else generate one that is stable-ish for demos
    psid = payload.get("position_snapshot_id")
    if not psid:
        # Friendly predictable id for demo runs; still unique enough
        ts = as_of_time.strftime("%Y%m%d")
        psid = f"PS-{portfolio_node_id}-{ts}-{uuid4().hex[:8]}"

    try:
        with db_conn() as conn:
            conn.row_factory = dict_row
            conn.execute(
                UPSERT_POSITION_SNAPSHOT_SQL,
                {
                    "position_snapshot_id": psid,
                    "as_of_time": as_of_time,
                    "portfolio_node_id": portfolio_node_id,
                    "payload_json": Json(payload),
                    "payload_hash": payload_hash,
                },
            )
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error writing position_snapshot: {repr(e)}")

    return PositionSnapshotOut(
        position_snapshot_id=psid,
        as_of_time=as_of_time,
        portfolio_node_id=portfolio_node_id,
        payload_hash=payload_hash,
    )

@app.get("/api/v1/position-snapshots/{position_snapshot_id}")
def get_position_snapshot(position_snapshot_id: str):
    try:
        with db_conn() as conn:
            conn.row_factory = dict_row
            row = conn.execute(GET_POSITION_SNAPSHOT_SQL, {"psid": position_snapshot_id}).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Position snapshot not found")
            return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error reading position_snapshot: {repr(e)}")


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
    def _load_positions_by_id(psid: str) -> Dict[str, Any]:
       with db_conn() as conn:
        conn.row_factory = dict_row
        row = conn.execute(
            "SELECT payload_json FROM position_snapshot WHERE position_snapshot_id = %(psid)s",
            {"psid": psid},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=400, detail=f"position_snapshot_id not found: {psid}")
        return row["payload_json"]

        # inside create_run(...)
        if getattr(req, "position_snapshot_id", None):
            payload = _load_positions_by_id(req.position_snapshot_id)
        else:
        # fallback for legacy demo flow
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
