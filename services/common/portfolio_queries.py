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


def build_hierarchy_tree_query(portfolio_id: str, run_id: str | None = None) -> tuple[str, dict]:
    """
    Build recursive CTE query to fetch portfolio hierarchy tree.

    Returns entire tree rooted at portfolio_id with:
    - All descendant nodes (recursive)
    - Position count per node
    - PV sum per node (if run_id provided)

    Args:
        portfolio_id: Root portfolio node ID
        run_id: Optional run ID for PV aggregation (uses BASE scenario)

    Returns:
        Tuple of (query_string, params_dict)

    Example result row:
        {
            'portfolio_node_id': 'port-123',
            'name': 'Test Fund',
            'parent_id': None,
            'node_type': 'FUND',
            'depth': 1,
            'tree_path': 'port-123',
            'position_count': 5,
            'pv_sum': 1000000.00
        }
    """
    query = """
        WITH RECURSIVE hierarchy AS (
          -- Base case: start with the root node
          SELECT portfolio_node_id, name, parent_id, node_type,
                 tags_json, metadata_json, created_at,
                 1 AS depth,
                 CAST(portfolio_node_id AS text) AS tree_path
          FROM portfolio_node
          WHERE portfolio_node_id = %(pid)s

          UNION ALL

          -- Recursive case: find children
          SELECT pn.portfolio_node_id, pn.name, pn.parent_id, pn.node_type,
                 pn.tags_json, pn.metadata_json, pn.created_at,
                 h.depth + 1,
                 h.tree_path || '/' || pn.portfolio_node_id
          FROM portfolio_node pn
          INNER JOIN hierarchy h ON pn.parent_id = h.portfolio_node_id
          WHERE h.depth < 10  -- Prevent runaway recursion
        )
        SELECT h.*,
               COUNT(DISTINCT pos.position_id) AS position_count,
               COALESCE(SUM((vr.measures_json ->> 'PV')::numeric), 0) AS pv_sum
        FROM hierarchy h
        LEFT JOIN position pos ON h.portfolio_node_id = pos.portfolio_node_id
          AND pos.status = 'ACTIVE'
        LEFT JOIN valuation_result vr ON pos.position_id = vr.position_id
          AND (%(rid)s IS NULL OR vr.run_id = %(rid)s)
          AND vr.scenario_id = 'BASE'
        GROUP BY h.portfolio_node_id, h.name, h.parent_id, h.node_type,
                 h.tags_json, h.metadata_json, h.created_at, h.depth, h.tree_path
        ORDER BY h.tree_path
    """

    params = {
        "pid": portfolio_id,
        "rid": run_id
    }

    return query, params


def build_tree_structure(rows: list[dict]) -> dict | None:
    """
    Convert flat CTE result rows into nested tree structure.

    Args:
        rows: List of dicts from build_hierarchy_tree_query result

    Returns:
        Root node dict with nested 'children' lists, or None if empty

    Example:
        Input: [
            {'portfolio_node_id': 'p1', 'parent_id': None, 'name': 'Fund', ...},
            {'portfolio_node_id': 'p2', 'parent_id': 'p1', 'name': 'Desk', ...},
        ]
        Output: {
            'portfolio_node_id': 'p1',
            'name': 'Fund',
            'children': [
                {'portfolio_node_id': 'p2', 'name': 'Desk', 'children': []}
            ]
        }
    """
    if not rows:
        return None

    # Build node lookup
    nodes = {}
    for row in rows:
        node = dict(row)
        node['children'] = []
        nodes[node['portfolio_node_id']] = node

    # Link children to parents
    root = None
    for row in rows:
        node = nodes[row['portfolio_node_id']]
        if row['parent_id'] is None:
            root = node
        else:
            parent = nodes.get(row['parent_id'])
            if parent:
                parent['children'].append(node)

    return root
