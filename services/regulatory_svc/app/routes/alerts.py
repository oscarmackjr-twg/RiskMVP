"""Alert configuration, evaluation, and notification tracking endpoints."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.common.db import db_conn
from psycopg.rows import dict_row

router = APIRouter()


class AlertConfigIn(BaseModel):
    alert_id: Optional[str] = None
    alert_type: str
    portfolio_node_id: Optional[str] = None
    threshold_value: float
    threshold_operator: str
    metric_name: str
    notification_channels: List[str] = ["email"]
    enabled: bool = True


class AlertConfigOut(BaseModel):
    alert_id: str
    alert_type: str
    portfolio_node_id: Optional[str]
    threshold_value: float
    threshold_operator: str
    metric_name: str
    notification_channels: List[str]
    enabled: bool


class AlertLogOut(BaseModel):
    log_id: str
    alert_id: str
    triggered_at: str
    metric_value: float
    threshold_value: float
    portfolio_node_id: Optional[str]
    position_id: Optional[str]
    notification_sent: bool
    resolved: bool


class EvaluateAlertsRequest(BaseModel):
    portfolio_node_id: str


@router.post("/config", response_model=AlertConfigOut, status_code=201)
def create_alert_config(config: AlertConfigIn) -> AlertConfigOut:
    """Create or update alert configuration."""

    alert_id = config.alert_id or f"alert-{uuid4()}"

    with db_conn() as conn:
        conn.execute("""
            INSERT INTO alert_config
              (alert_id, alert_type, portfolio_node_id, threshold_value, threshold_operator,
               metric_name, notification_channels, enabled)
            VALUES (%(aid)s, %(atype)s, %(pid)s, %(tval)s, %(top)s, %(mname)s, %(channels)s, %(enabled)s)
            ON CONFLICT (alert_id) DO UPDATE SET
              threshold_value = EXCLUDED.threshold_value,
              threshold_operator = EXCLUDED.threshold_operator,
              enabled = EXCLUDED.enabled
        """, {
            'aid': alert_id,
            'atype': config.alert_type,
            'pid': config.portfolio_node_id,
            'tval': config.threshold_value,
            'top': config.threshold_operator,
            'mname': config.metric_name,
            'channels': config.notification_channels,
            'enabled': config.enabled,
        })

    return AlertConfigOut(
        alert_id=alert_id,
        alert_type=config.alert_type,
        portfolio_node_id=config.portfolio_node_id,
        threshold_value=config.threshold_value,
        threshold_operator=config.threshold_operator,
        metric_name=config.metric_name,
        notification_channels=config.notification_channels,
        enabled=config.enabled,
    )


@router.get("/config", response_model=List[AlertConfigOut])
def list_alert_configs(
    portfolio_node_id: str = Query(None),
    enabled: bool = Query(None),
) -> List[AlertConfigOut]:
    """List alert configurations with optional filters."""

    filters = []
    params: dict = {}

    if portfolio_node_id:
        filters.append("portfolio_node_id = %(pid)s")
        params['pid'] = portfolio_node_id
    if enabled is not None:
        filters.append("enabled = %(enabled)s")
        params['enabled'] = enabled

    where_clause = " AND ".join(filters) if filters else "TRUE"

    with db_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(f"""
            SELECT alert_id, alert_type, portfolio_node_id, threshold_value,
                   threshold_operator, metric_name, notification_channels, enabled
            FROM alert_config
            WHERE {where_clause}
            ORDER BY created_at DESC
        """, params).fetchall()

        return [AlertConfigOut(**dict(r)) for r in rows]


@router.delete("/config/{alert_id}", status_code=204)
def delete_alert_config(alert_id: str):
    """Delete an alert configuration."""

    with db_conn() as conn:
        result = conn.execute(
            "DELETE FROM alert_config WHERE alert_id = %(aid)s", {'aid': alert_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert config not found")


@router.get("/log", response_model=List[AlertLogOut])
def list_alert_logs(
    alert_id: str = Query(None),
    portfolio_node_id: str = Query(None),
    resolved: bool = Query(None),
    limit: int = Query(50, le=200),
) -> List[AlertLogOut]:
    """List alert trigger log with filters."""

    filters = []
    params: dict = {"limit": limit}

    if alert_id:
        filters.append("alert_id = %(aid)s")
        params['aid'] = alert_id
    if portfolio_node_id:
        filters.append("portfolio_node_id = %(pid)s")
        params['pid'] = portfolio_node_id
    if resolved is not None:
        filters.append("resolved = %(resolved)s")
        params['resolved'] = resolved

    where_clause = " AND ".join(filters) if filters else "TRUE"

    with db_conn() as conn:
        conn.row_factory = dict_row
        rows = conn.execute(f"""
            SELECT log_id, alert_id, triggered_at, metric_value, threshold_value,
                   portfolio_node_id, position_id, notification_sent, resolved
            FROM alert_log
            WHERE {where_clause}
            ORDER BY triggered_at DESC
            LIMIT %(limit)s
        """, params).fetchall()

        return [
            AlertLogOut(
                log_id=r['log_id'],
                alert_id=r['alert_id'],
                triggered_at=r['triggered_at'].isoformat() if hasattr(r['triggered_at'], 'isoformat') else str(r['triggered_at']),
                metric_value=float(r['metric_value']),
                threshold_value=float(r['threshold_value']),
                portfolio_node_id=r['portfolio_node_id'],
                position_id=r['position_id'],
                notification_sent=r['notification_sent'],
                resolved=r['resolved'],
            )
            for r in rows
        ]


@router.post("/evaluate")
def evaluate_alerts(req: EvaluateAlertsRequest) -> Dict[str, Any]:
    """Evaluate all enabled alerts for a portfolio and trigger if thresholds breached."""

    triggered_alerts = []

    with db_conn() as conn:
        conn.row_factory = dict_row

        # Fetch enabled alerts for portfolio
        alerts = conn.execute("""
            SELECT alert_id, alert_type, threshold_value, threshold_operator, metric_name
            FROM alert_config
            WHERE (portfolio_node_id = %(pid)s OR portfolio_node_id IS NULL)
              AND enabled = TRUE
        """, {'pid': req.portfolio_node_id}).fetchall()

        for alert in alerts:
            # Fetch latest metric value
            metric = conn.execute("""
                SELECT metric_value, as_of_date
                FROM regulatory_metrics
                WHERE portfolio_node_id = %(pid)s
                  AND metric_type = %(mname)s
                ORDER BY as_of_date DESC
                LIMIT 1
            """, {
                'pid': req.portfolio_node_id,
                'mname': alert['metric_name'],
            }).fetchone()

            if not metric:
                continue

            metric_value = float(metric['metric_value'])
            threshold_value = float(alert['threshold_value'])
            op = alert['threshold_operator']

            # Evaluate threshold
            breached = (
                (op == 'GT' and metric_value > threshold_value) or
                (op == 'GTE' and metric_value >= threshold_value) or
                (op == 'LT' and metric_value < threshold_value) or
                (op == 'LTE' and metric_value <= threshold_value) or
                (op == 'EQ' and metric_value == threshold_value)
            )

            if breached:
                log_id = f"log-{uuid4()}"
                conn.execute("""
                    INSERT INTO alert_log
                      (log_id, alert_id, triggered_at, metric_value, threshold_value,
                       portfolio_node_id, notification_sent, resolved)
                    VALUES (%(lid)s, %(aid)s, now(), %(mval)s, %(tval)s, %(pid)s, FALSE, FALSE)
                """, {
                    'lid': log_id,
                    'aid': alert['alert_id'],
                    'mval': metric_value,
                    'tval': threshold_value,
                    'pid': req.portfolio_node_id,
                })

                triggered_alerts.append({
                    'alert_id': alert['alert_id'],
                    'alert_type': alert['alert_type'],
                    'metric_name': alert['metric_name'],
                    'metric_value': metric_value,
                    'threshold_value': threshold_value,
                    'threshold_operator': op,
                    'log_id': log_id,
                })

    return {
        'portfolio_node_id': req.portfolio_node_id,
        'evaluated_at': datetime.now(timezone.utc).isoformat(),
        'triggered_count': len(triggered_alerts),
        'triggered_alerts': triggered_alerts,
    }


@router.post("/log/{log_id}/resolve")
def resolve_alert_log(log_id: str) -> Dict[str, str]:
    """Mark alert log entry as resolved."""

    with db_conn() as conn:
        result = conn.execute("""
            UPDATE alert_log
            SET resolved = TRUE, resolved_at = now()
            WHERE log_id = %(lid)s
        """, {'lid': log_id})

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Alert log not found")

    return {'log_id': log_id, 'status': 'resolved'}
