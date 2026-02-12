"""Regulatory report generation and export endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Response

from services.common.db import db_conn
from services.common.export import export_to_csv, export_to_excel
from psycopg.rows import dict_row

router = APIRouter()


@router.get("/regulatory/{portfolio_id}/export")
def export_regulatory_report(
    portfolio_id: str,
    format: str = Query("xlsx", pattern="^(csv|xlsx)$"),
    include_audit_trail: bool = Query(True),
    start_date: str = Query(None),
    end_date: str = Query(None),
) -> Response:
    """Export regulatory report with CECL, Basel, and optional audit trail."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        # Regulatory metrics summary
        metrics = conn.execute("""
            SELECT metric_type, metric_value, as_of_date, metric_breakdown_json
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s
              AND (%(start)s IS NULL OR as_of_date >= %(start)s::timestamptz)
              AND (%(end)s IS NULL OR as_of_date <= %(end)s::timestamptz)
            ORDER BY as_of_date DESC, metric_type
        """, {'pid': portfolio_id, 'start': start_date, 'end': end_date}).fetchall()

        if not metrics:
            raise HTTPException(status_code=404, detail="No regulatory metrics found")

        summary_data = []
        for m in metrics:
            as_of = m['as_of_date']
            summary_data.append({
                "Metric Type": m['metric_type'],
                "Value": float(m['metric_value']),
                "As Of Date": as_of.isoformat() if hasattr(as_of, 'isoformat') else str(as_of),
            })

        # Audit trail if requested
        audit_data = []
        if include_audit_trail:
            entries = conn.execute("""
                SELECT audit_id, audit_type, calculation_method, computed_at,
                       assumptions_json, results_json
                FROM audit_trail
                WHERE entity_id = %(pid)s
                  AND (%(start)s IS NULL OR computed_at >= %(start)s::timestamptz)
                  AND (%(end)s IS NULL OR computed_at <= %(end)s::timestamptz)
                ORDER BY computed_at DESC
                LIMIT 100
            """, {'pid': portfolio_id, 'start': start_date, 'end': end_date}).fetchall()

            for e in entries:
                ct = e['computed_at']
                audit_data.append({
                    "Audit ID": e['audit_id'],
                    "Type": e['audit_type'],
                    "Method": e['calculation_method'],
                    "Computed At": ct.isoformat() if hasattr(ct, 'isoformat') else str(ct),
                    "Assumptions": str(e['assumptions_json']),
                    "Results": str(e['results_json']),
                })

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")

    if format == "csv":
        csv_rows = []
        csv_rows.append({"Section": "Regulatory Metrics Summary"})
        csv_rows.extend([{"Section": "", **row} for row in summary_data])

        if include_audit_trail and audit_data:
            csv_rows.append({"Section": ""})
            csv_rows.append({"Section": "Audit Trail"})
            csv_rows.extend([{"Section": "", **row} for row in audit_data])

        all_columns = ["Section"]
        if summary_data:
            all_columns.extend(summary_data[0].keys())
        if audit_data and include_audit_trail:
            for col in audit_data[0].keys():
                if col not in all_columns:
                    all_columns.append(col)

        csv_content = export_to_csv(csv_rows, all_columns)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="regulatory-{portfolio_id}-{now_str}.csv"'
            },
        )

    # Excel format
    sheets = {
        "Summary": {
            "headers": ["Metric Type", "Value", "As Of Date"],
            "data": summary_data,
            "formats": {"Value": "$#,##0.00"},
        }
    }

    if include_audit_trail and audit_data:
        sheets["Audit Trail"] = {
            "headers": ["Audit ID", "Type", "Method", "Computed At", "Assumptions", "Results"],
            "data": audit_data,
        }

    excel_buffer = export_to_excel(sheets, title=f"Regulatory Report - {portfolio_id}")
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="regulatory-{portfolio_id}-{now_str}.xlsx"'
        },
    )


@router.get("/cecl/{portfolio_id}/export")
def export_cecl_report(
    portfolio_id: str,
    format: str = Query("xlsx", pattern="^(csv|xlsx)$"),
) -> Response:
    """Export CECL allowance report by segment."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        cecl_metric = conn.execute("""
            SELECT metric_value, metric_breakdown_json, as_of_date
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s
              AND metric_type = 'CECL_ALLOWANCE'
            ORDER BY as_of_date DESC LIMIT 1
        """, {'pid': portfolio_id}).fetchone()

        if not cecl_metric:
            raise HTTPException(status_code=404, detail="No CECL allowance found")

        total_allowance = float(cecl_metric['metric_value'])
        by_segment = (cecl_metric['metric_breakdown_json'] or {}).get('by_segment', {})

        segment_data = []
        for segment_id, allowance in by_segment.items():
            segment_data.append({
                "Segment": segment_id,
                "Allowance": float(allowance),
                "% of Total": (float(allowance) / total_allowance * 100) if total_allowance > 0 else 0.0,
            })

        segment_data.append({
            "Segment": "TOTAL",
            "Allowance": total_allowance,
            "% of Total": 100.0,
        })

    as_of = cecl_metric['as_of_date']

    if format == "csv":
        csv_content = export_to_csv(segment_data, ["Segment", "Allowance", "% of Total"])
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="cecl-{portfolio_id}-{as_of}.csv"'
            },
        )

    sheets = {
        "CECL Allowance": {
            "headers": ["Segment", "Allowance", "% of Total"],
            "data": segment_data,
            "formats": {"Allowance": "$#,##0.00", "% of Total": "0.00%"},
        }
    }
    excel_buffer = export_to_excel(sheets, title=f"CECL Allowance - {portfolio_id}")
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="cecl-{portfolio_id}-{as_of}.xlsx"'
        },
    )


@router.get("/basel/{portfolio_id}/export")
def export_basel_report(
    portfolio_id: str,
    format: str = Query("xlsx", pattern="^(csv|xlsx)$"),
) -> Response:
    """Export Basel III RWA report."""

    with db_conn() as conn:
        conn.row_factory = dict_row

        metric = conn.execute("""
            SELECT metric_value, metric_breakdown_json, as_of_date
            FROM regulatory_metrics
            WHERE portfolio_node_id = %(pid)s
              AND metric_type = 'BASEL_RWA'
            ORDER BY as_of_date DESC LIMIT 1
        """, {'pid': portfolio_id}).fetchone()

        if not metric:
            raise HTTPException(status_code=404, detail="No Basel metrics found")

        breakdown = metric['metric_breakdown_json'] or {}
        by_type = breakdown.get('by_counterparty_type', {})
        ratios = breakdown.get('capital_ratios', {})

        rwa_data = []
        for ctype, rwa in by_type.items():
            rwa_data.append({
                "Counterparty Type": ctype,
                "RWA": float(rwa),
            })
        rwa_data.append({"Counterparty Type": "TOTAL", "RWA": float(metric['metric_value'])})

        ratio_data = [
            {"Ratio": "CET1", "Value": ratios.get('cet1_ratio', 0.0) * 100, "Minimum": 4.5},
            {"Ratio": "Tier 1", "Value": ratios.get('tier1_ratio', 0.0) * 100, "Minimum": 6.0},
            {"Ratio": "Total Capital", "Value": ratios.get('total_capital_ratio', 0.0) * 100, "Minimum": 8.0},
        ]

    if format == "csv":
        csv_content = export_to_csv(rwa_data, ["Counterparty Type", "RWA"])
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="basel-{portfolio_id}.csv"'
            },
        )

    sheets = {
        "RWA by Type": {
            "headers": ["Counterparty Type", "RWA"],
            "data": rwa_data,
            "formats": {"RWA": "$#,##0.00"},
        },
        "Capital Ratios": {
            "headers": ["Ratio", "Value", "Minimum"],
            "data": ratio_data,
            "formats": {"Value": "0.00%", "Minimum": "0.00%"},
        },
    }
    excel_buffer = export_to_excel(sheets, title=f"Basel III Report - {portfolio_id}")
    return Response(
        content=excel_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="basel-{portfolio_id}.xlsx"'
        },
    )
