"""SQL query builders for portfolio aggregation with FX conversion and reference data."""
from __future__ import annotations

from typing import Optional


def build_issuer_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for issuer aggregation with multi-currency conversion.

    Returns: (query_string, params_dict)
    """
    query = """
    WITH position_pv AS (
      SELECT
        ref.entity_id AS issuer_id,
        ref.name AS issuer_name,
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(issuer_id, 'UNKNOWN') AS issuer_id,
      COALESCE(issuer_name, 'Unknown Issuer') AS issuer_name,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      COUNT(DISTINCT base_ccy) AS ccy_count,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY issuer_id, issuer_name
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params


def build_sector_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for sector aggregation with multi-currency conversion.

    Returns: (query_string, params_dict)
    """
    query = """
    WITH position_pv AS (
      SELECT
        ref.sector,
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(sector, 'Unknown') AS sector,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY sector
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params


def build_rating_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for rating aggregation with latest rating per issuer.

    Returns: (query_string, params_dict)
    """
    query = """
    WITH latest_ratings AS (
      SELECT DISTINCT ON (entity_id, agency)
        entity_id,
        agency,
        rating
      FROM rating_history
      ORDER BY entity_id, agency, as_of_date DESC
    ),
    position_pv AS (
      SELECT
        lr.rating,
        lr.agency,
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN latest_ratings lr ON ref.entity_id = lr.entity_id AND lr.agency = 'SP'
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(rating, 'NR') AS rating,
      COALESCE(agency, 'N/A') AS agency,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY rating, agency
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params


def build_geography_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for geography aggregation.

    Returns: (query_string, params_dict)
    """
    query = """
    WITH position_pv AS (
      SELECT
        ref.geography,
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN instrument_version iv ON instr.instrument_id = iv.instrument_id AND iv.status = 'APPROVED'
      LEFT JOIN reference_data ref ON (iv.terms_json ->> 'issuer_id') = ref.entity_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(geography, 'Unknown') AS geography,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY geography
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params


def build_currency_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for currency aggregation (both local and USD-converted).

    Returns: (query_string, params_dict)
    """
    query = """
    WITH position_pv AS (
      SELECT
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd,
        COALESCE(fx.spot_rate, 1.0) AS fx_rate
      FROM position pos
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      base_ccy AS currency,
      COALESCE(SUM(pv_local), 0) AS pv_local,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      AVG(fx_rate) AS avg_fx_rate,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY base_ccy
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params


def build_product_type_aggregation_query(
    portfolio_id: str,
    run_id: Optional[str] = None,
    snapshot_id: Optional[str] = None
) -> tuple[str, dict]:
    """
    Build SQL query for product type aggregation.

    Returns: (query_string, params_dict)
    """
    query = """
    WITH position_pv AS (
      SELECT
        instr.instrument_type,
        pos.base_ccy,
        (vr.measures_json ->> 'PV')::numeric AS pv_local,
        CASE
          WHEN pos.base_ccy = 'USD' THEN (vr.measures_json ->> 'PV')::numeric
          ELSE (vr.measures_json ->> 'PV')::numeric * COALESCE(fx.spot_rate, 1.0)
        END AS pv_usd
      FROM position pos
      LEFT JOIN instrument instr ON pos.instrument_id = instr.instrument_id
      LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
        AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
        AND vr.scenario_id = 'BASE'
      LEFT JOIN fx_spot fx ON fx.pair = pos.base_ccy || '/USD'
        AND (%(sid)s IS NULL OR fx.snapshot_id = %(sid)s)
      WHERE pos.portfolio_node_id = %(port_id)s AND pos.status = 'ACTIVE'
    )
    SELECT
      COALESCE(instrument_type, 'Unknown') AS product_type,
      COALESCE(SUM(pv_usd), 0) AS pv_usd,
      COUNT(*) AS position_count,
      ROUND(100.0 * SUM(pv_usd) / NULLIF(SUM(SUM(pv_usd)) OVER (), 0), 2) AS weight_pct
    FROM position_pv
    GROUP BY instrument_type
    HAVING SUM(pv_usd) IS NOT NULL
    ORDER BY pv_usd DESC;
    """

    params = {
        "port_id": portfolio_id,
        "rid": run_id,
        "sid": snapshot_id,
    }

    return query, params
