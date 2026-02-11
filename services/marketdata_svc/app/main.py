
from fastapi import HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Literal
from psycopg.types.json import Json

from services.common.db import db_conn
from services.common.hash import sha256_json
from services.common.service_base import create_service_app
from shared.models.market_data import CurveNode, Curve, FxSpot

app = create_service_app(title="marketdata-svc", version="0.1.0")

class Quality(BaseModel):
    """Data quality metadata for market data snapshots."""
    dq_status: Literal["PASS", "WARN", "FAIL"]
    issues: List[str] = Field(default_factory=list)


class MarketDataSnapshotV1(BaseModel):
    """Market data snapshot request/response model."""
    snapshot_id: str
    as_of_time: datetime
    vendor: str
    universe_id: str
    fx_spots: List[FxSpot]
    curves: List[Curve]
    quality: Quality

@app.post("/api/v1/marketdata/snapshots", status_code=201)
def create_snapshot(snap: MarketDataSnapshotV1):
    payload = snap.model_dump(mode="json")
    payload_hash = sha256_json(payload)

    sql = """
    INSERT INTO marketdata_snapshot
      (snapshot_id, as_of_time, vendor, universe_id, payload_json, dq_status, payload_hash)
    VALUES
      (%(sid)s, %(asof)s, %(vendor)s, %(uid)s, %(payload)s::jsonb, %(dq)s, %(phash)s)
    ON CONFLICT (snapshot_id) DO UPDATE SET
      payload_json=EXCLUDED.payload_json,
      dq_status=EXCLUDED.dq_status,
      payload_hash=EXCLUDED.payload_hash,
      created_at=now();
    """

    with db_conn() as conn:
        conn.execute(sql, {
            "sid": snap.snapshot_id,
            "asof": snap.as_of_time,
            "vendor": snap.vendor,
            "uid": snap.universe_id,
            "payload": Json(payload),          
            "dq": snap.quality.dq_status,
            "phash": payload_hash,
        })

    return {"snapshot_id": snap.snapshot_id}

@app.get("/api/v1/marketdata/snapshots/{snapshotId}")
def get_snapshot(snapshotId: str):
    sql = "SELECT payload_json FROM marketdata_snapshot WHERE snapshot_id=%(sid)s"
    with db_conn() as conn:
        row = conn.execute(sql, {"sid": snapshotId}).fetchone()
        if not row:
            raise HTTPException(404, "snapshot not found")
        return row["payload_json"]
