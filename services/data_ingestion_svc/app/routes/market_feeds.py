"""Market feeds ingestion -- yield curves, credit spreads, FX spots, and ratings."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from psycopg.types.json import Json

from services.common.db import db_conn
from services.common.hash import sha256_json
from services.data_ingestion_svc.app.models import (
    YieldCurveUpload,
    YieldCurveOut,
    YieldCurveNode,
    CreditSpreadUpload,
    CreditSpreadOut,
    RatingChange,
    RatingHistoryOut,
    FXSpotUpload,
    FXSpotOut,
    FXSpotStatus,
    MarketFeedStatus,
)

router = APIRouter()


@router.post("/yield-curves", response_model=MarketFeedStatus, status_code=201)
def ingest_yield_curve(req: YieldCurveUpload):
    """Ingest a yield curve (discount, forecast, basis, or spread) from a market data source."""
    # Validate curve_type
    if req.curve_type not in ("DISCOUNT", "FORECAST", "BASIS", "SPREAD"):
        raise HTTPException(status_code=400, detail=f"Invalid curve_type: {req.curve_type}")

    # Validate nodes
    if len(req.nodes) < 2:
        raise HTTPException(status_code=400, detail="Yield curve must have at least 2 nodes")

    # Prepare data
    feed_id = req.curve_id
    payload = req.model_dump()
    payload_hash = sha256_json(payload)

    # Lineage metadata
    lineage_id = f"curve-{req.curve_id}-{datetime.utcnow().isoformat()}"
    metadata_json = {
        "record_count": len(req.nodes),
        "vendor": req.source,
        "currency": req.currency
    }

    with db_conn() as conn:
        # UPSERT into market_data_feed
        conn.execute("""
            INSERT INTO market_data_feed
              (feed_id, feed_type, as_of_date, source, payload_json, payload_hash, validation_status, created_at, updated_at)
            VALUES (%(fid)s, 'YIELD_CURVE', %(aof)s, %(src)s, %(pl)s::jsonb, %(ph)s, 'PASS', now(), now())
            ON CONFLICT (feed_id) DO UPDATE SET
              payload_json = EXCLUDED.payload_json,
              payload_hash = EXCLUDED.payload_hash,
              validation_status = EXCLUDED.validation_status,
              updated_at = now()
        """, {
            "fid": feed_id,
            "aof": req.as_of_date,
            "src": req.source,
            "pl": Json(payload),
            "ph": payload_hash
        })

        # Record lineage
        conn.execute("""
            INSERT INTO data_lineage
              (lineage_id, feed_type, feed_id, source_system, source_identifier,
               ingested_at, transformation_chain, quality_checks_passed, metadata_json)
            VALUES (%(lid)s, 'YIELD_CURVE', %(fid)s, %(src)s, %(src)s,
                    now(), %(tc)s, true, %(meta)s::jsonb)
            ON CONFLICT (lineage_id) DO NOTHING
        """, {
            "lid": lineage_id,
            "fid": feed_id,
            "src": req.source,
            "tc": ['RECEIVE', 'VALIDATE', 'PARSE', 'STORE'],
            "meta": Json(metadata_json)
        })

    return MarketFeedStatus(
        feed_id=feed_id,
        feed_type="YIELD_CURVE",
        status="PASS",
        record_count=len(req.nodes),
        ingested_at=datetime.utcnow()
    )


@router.get("/yield-curves/{curve_id}")
def get_yield_curve(curve_id: str, as_of_date: str | None = None):
    """Retrieve the latest (or as-of-date) yield curve by ID."""
    with db_conn() as conn:
        if as_of_date:
            rows = conn.execute("""
                SELECT * FROM market_data_feed
                WHERE feed_id = %(cid)s AND as_of_date = %(aof)s
            """, {"cid": curve_id, "aof": as_of_date}).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM market_data_feed
                WHERE feed_id = %(cid)s
                ORDER BY as_of_date DESC
                LIMIT 1
            """, {"cid": curve_id}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Yield curve not found: {curve_id}")

        row = rows[0]
        payload = row["payload_json"]

        return YieldCurveOut(
            curve_id=payload["curve_id"],
            curve_type=payload["curve_type"],
            currency=payload["currency"],
            as_of_date=payload["as_of_date"],
            source=payload["source"],
            nodes=[YieldCurveNode(**n) for n in payload["nodes"]]
        )


@router.post("/credit-spreads", response_model=MarketFeedStatus, status_code=201)
def ingest_credit_spreads(req: CreditSpreadUpload):
    """Ingest credit spread curves for an issuer/sector."""
    # Prepare data
    feed_id = f"{req.issuer_id}-{req.rating}-{req.as_of_date.date()}"
    payload = req.model_dump()
    payload_hash = sha256_json(payload)

    # Lineage metadata
    lineage_id = f"spread-{req.issuer_id}-{datetime.utcnow().isoformat()}"
    metadata_json = {
        "record_count": len(req.spreads),
        "vendor": req.source,
        "issuer_id": req.issuer_id,
        "rating": req.rating
    }

    with db_conn() as conn:
        # UPSERT into market_data_feed
        conn.execute("""
            INSERT INTO market_data_feed
              (feed_id, feed_type, as_of_date, source, payload_json, payload_hash, validation_status, created_at, updated_at)
            VALUES (%(fid)s, 'CREDIT_SPREAD', %(aof)s, %(src)s, %(pl)s::jsonb, %(ph)s, 'PASS', now(), now())
            ON CONFLICT (feed_id) DO UPDATE SET
              payload_json = EXCLUDED.payload_json,
              payload_hash = EXCLUDED.payload_hash,
              validation_status = EXCLUDED.validation_status,
              updated_at = now()
        """, {
            "fid": feed_id,
            "aof": req.as_of_date,
            "src": req.source,
            "pl": Json(payload),
            "ph": payload_hash
        })

        # Record lineage
        conn.execute("""
            INSERT INTO data_lineage
              (lineage_id, feed_type, feed_id, source_system, source_identifier,
               ingested_at, transformation_chain, quality_checks_passed, metadata_json)
            VALUES (%(lid)s, 'CREDIT_SPREAD', %(fid)s, %(src)s, %(src)s,
                    now(), %(tc)s, true, %(meta)s::jsonb)
            ON CONFLICT (lineage_id) DO NOTHING
        """, {
            "lid": lineage_id,
            "fid": feed_id,
            "src": req.source,
            "tc": ['RECEIVE', 'VALIDATE', 'PARSE', 'STORE'],
            "meta": Json(metadata_json)
        })

    return MarketFeedStatus(
        feed_id=feed_id,
        feed_type="CREDIT_SPREAD",
        status="PASS",
        record_count=len(req.spreads),
        ingested_at=datetime.utcnow()
    )


@router.get("/credit-spreads/{issuer_id}")
def get_credit_spreads(issuer_id: str, as_of_date: str | None = None):
    """Retrieve credit spreads for a given issuer."""
    with db_conn() as conn:
        if as_of_date:
            rows = conn.execute("""
                SELECT * FROM market_data_feed
                WHERE feed_id LIKE %(pattern)s AND as_of_date = %(aof)s
                ORDER BY as_of_date DESC
            """, {"pattern": f"{issuer_id}-%", "aof": as_of_date}).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM market_data_feed
                WHERE feed_id LIKE %(pattern)s
                ORDER BY as_of_date DESC
                LIMIT 1
            """, {"pattern": f"{issuer_id}-%"}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"Credit spreads not found: {issuer_id}")

        row = rows[0]
        payload = row["payload_json"]

        return CreditSpreadOut(
            issuer_id=payload["issuer_id"],
            rating=payload["rating"],
            sector=payload["sector"],
            currency=payload["currency"],
            as_of_date=payload["as_of_date"],
            source=payload["source"],
            spreads=[YieldCurveNode(**n) for n in payload["spreads"]]
        )


@router.post("/fx-spots", response_model=FXSpotStatus, status_code=201)
def ingest_fx_spots(req: FXSpotUpload):
    """Ingest FX spot rates for a market snapshot (PRIMARY ENDPOINT for multi-currency)."""
    # Validate pairs
    for spot in req.spots:
        if "/" not in spot.pair:
            raise HTTPException(status_code=400, detail=f"Invalid FX pair format: {spot.pair}")
        if spot.spot_rate <= 0:
            raise HTTPException(status_code=400, detail=f"Invalid spot rate: {spot.spot_rate}")

    # Lineage metadata
    lineage_id = f"fx-{req.snapshot_id}-{datetime.utcnow().isoformat()}"
    metadata_json = {
        "pair_count": len(req.spots),
        "snapshot_id": req.snapshot_id
    }

    with db_conn() as conn:
        # UPSERT into fx_spot table (dedicated table, not market_data_feed)
        for spot in req.spots:
            conn.execute("""
                INSERT INTO fx_spot (pair, snapshot_id, spot_rate, as_of_date, source, created_at)
                VALUES (%(pair)s, %(sid)s, %(rate)s, %(aof)s, %(src)s, now())
                ON CONFLICT (pair, snapshot_id) DO UPDATE SET
                  spot_rate = EXCLUDED.spot_rate,
                  as_of_date = EXCLUDED.as_of_date,
                  source = EXCLUDED.source
            """, {
                "pair": spot.pair,
                "sid": req.snapshot_id,
                "rate": spot.spot_rate,
                "aof": req.as_of_date,
                "src": req.source
            })

        # Record lineage
        conn.execute("""
            INSERT INTO data_lineage
              (lineage_id, feed_type, feed_id, source_system, source_identifier,
               ingested_at, transformation_chain, quality_checks_passed, metadata_json)
            VALUES (%(lid)s, 'FX_SPOT', %(sid)s, %(src)s, %(src)s,
                    now(), %(tc)s, true, %(meta)s::jsonb)
        """, {
            "lid": lineage_id,
            "sid": req.snapshot_id,
            "src": req.source,
            "tc": ['RECEIVE', 'VALIDATE', 'PARSE', 'STORE'],
            "meta": Json(metadata_json)
        })

    return FXSpotStatus(
        snapshot_id=req.snapshot_id,
        pair_count=len(req.spots),
        ingested_at=datetime.utcnow()
    )


@router.get("/fx-spots/{snapshot_id}")
def get_fx_spots(snapshot_id: str):
    """Get FX spots for a market snapshot."""
    with db_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM fx_spot WHERE snapshot_id = %(sid)s
        """, {"sid": snapshot_id}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"FX spots not found for snapshot: {snapshot_id}")

        return [
            FXSpotOut(
                pair=row["pair"],
                snapshot_id=row["snapshot_id"],
                spot_rate=float(row["spot_rate"]),
                as_of_date=row["as_of_date"],
                source=row["source"]
            )
            for row in rows
        ]


@router.post("/ratings", response_model=MarketFeedStatus, status_code=201)
def ingest_rating_change(req: RatingChange):
    """Record a credit rating change event from an agency."""
    # Validate agency
    if req.agency not in ('SP', 'MOODYS', 'FITCH', 'DBRS'):
        raise HTTPException(status_code=400, detail=f"Invalid agency: {req.agency}")

    rating_id = f"{req.entity_id}-{req.agency}-{req.effective_date.date()}"

    # Lineage metadata
    lineage_id = f"rating-{req.entity_id}-{datetime.utcnow().isoformat()}"
    metadata_json = {
        "entity_id": req.entity_id,
        "agency": req.agency,
        "rating": req.rating
    }

    with db_conn() as conn:
        # Insert into rating_history
        conn.execute("""
            INSERT INTO rating_history
              (rating_id, entity_id, agency, rating, outlook, as_of_date, effective_date, metadata_json, created_at)
            VALUES (%(rid)s, %(eid)s, %(ag)s, %(rt)s, %(ol)s, %(aof)s, %(ef)s, %(meta)s::jsonb, now())
            ON CONFLICT (rating_id) DO UPDATE SET
              rating = EXCLUDED.rating,
              outlook = EXCLUDED.outlook,
              as_of_date = EXCLUDED.as_of_date,
              metadata_json = EXCLUDED.metadata_json
        """, {
            "rid": rating_id,
            "eid": req.entity_id,
            "ag": req.agency,
            "rt": req.rating,
            "ol": req.outlook,
            "aof": req.as_of_date,
            "ef": req.effective_date,
            "meta": Json({})
        })

        # Record lineage
        conn.execute("""
            INSERT INTO data_lineage
              (lineage_id, feed_type, feed_id, source_system, source_identifier,
               ingested_at, transformation_chain, quality_checks_passed, metadata_json)
            VALUES (%(lid)s, 'RATING', %(rid)s, %(src)s, %(eid)s,
                    now(), %(tc)s, true, %(meta)s::jsonb)
        """, {
            "lid": lineage_id,
            "rid": rating_id,
            "src": req.source,
            "eid": req.entity_id,
            "tc": ['RECEIVE', 'VALIDATE', 'PARSE', 'STORE'],
            "meta": Json(metadata_json)
        })

    return MarketFeedStatus(
        feed_id=rating_id,
        feed_type="RATING",
        status="PASS",
        record_count=1,
        ingested_at=datetime.utcnow()
    )


@router.get("/ratings/{entity_id}")
def get_ratings_history(entity_id: str, agency: str | None = None):
    """Retrieve the rating history for an entity, optionally filtered by agency."""
    with db_conn() as conn:
        if agency:
            rows = conn.execute("""
                SELECT * FROM rating_history
                WHERE entity_id = %(eid)s AND agency = %(ag)s
                ORDER BY as_of_date DESC
            """, {"eid": entity_id, "ag": agency}).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM rating_history
                WHERE entity_id = %(eid)s
                ORDER BY as_of_date DESC
            """, {"eid": entity_id}).fetchall()

        if not rows:
            raise HTTPException(status_code=404, detail=f"No rating history found for entity: {entity_id}")

        return [
            RatingHistoryOut(
                entity_id=row["entity_id"],
                agency=row["agency"],
                rating=row["rating"],
                outlook=row["outlook"],
                as_of_date=row["as_of_date"],
                effective_date=row["effective_date"]
            )
            for row in rows
        ]


@router.get("/status", response_model=list[MarketFeedStatus])
def list_feed_statuses(feed_type: str | None = None, limit: int = 50):
    """List recent market feed ingestion statuses."""
    with db_conn() as conn:
        if feed_type:
            rows = conn.execute("""
                SELECT feed_id, feed_type, as_of_date, source, validation_status, created_at
                FROM market_data_feed
                WHERE feed_type = %(ft)s
                ORDER BY created_at DESC
                LIMIT %(lim)s
            """, {"ft": feed_type, "lim": limit}).fetchall()
        else:
            rows = conn.execute("""
                SELECT feed_id, feed_type, as_of_date, source, validation_status, created_at
                FROM market_data_feed
                ORDER BY created_at DESC
                LIMIT %(lim)s
            """, {"lim": limit}).fetchall()

        return [
            MarketFeedStatus(
                feed_id=row["feed_id"],
                feed_type=row["feed_type"],
                status=row["validation_status"],
                record_count=0,  # Could query payload_json to get actual count
                ingested_at=row["created_at"]
            )
            for row in rows
        ]
