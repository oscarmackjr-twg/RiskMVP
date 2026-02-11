
from fastapi import HTTPException
from typing import Literal

from services.common.db import db_conn
from services.common.service_base import create_service_app

app = create_service_app(title="results-api", version="0.1.0")

@app.get("/api/v1/results/{runId}/summary")
def summary(runId: str, scenario_id: str = "BASE"):
    sql = '''
    SELECT COUNT(*) AS rows,
           SUM((measures_json ->> 'PV')::double precision) AS pv_sum
    FROM valuation_result
    WHERE run_id=%(rid)s AND scenario_id=%(sid)s;
    '''
    with db_conn() as conn:
        row = conn.execute(sql, {"rid": runId, "sid": scenario_id}).fetchone()
        if not row:
            raise HTTPException(404, "no results")
        return dict(row)

@app.get("/api/v1/results/{runId}/cube")
def cube(runId: str, measure: str, by: Literal["portfolio_node_id","product_type"], scenario_id: str="BASE"):
    sql = f'''
    SELECT {by} AS key,
           SUM((measures_json ->> %(m)s)::double precision) AS value
    FROM valuation_result
    WHERE run_id=%(rid)s AND scenario_id=%(sid)s
    GROUP BY {by}
    ORDER BY value DESC;
    '''
    with db_conn() as conn:
        rows = conn.execute(sql, {"rid": runId, "sid": scenario_id, "m": measure}).fetchall()
        return [{"key": r["key"], "value": r["value"]} for r in rows]
