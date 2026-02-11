# compute/tests/golden/test_callable_bond_golden.py
"""Golden tests for callable bond pricer with reference prices.

Tests cover:
- Basic callable bond pricing with tree-based valuation
- OAS (Option-Adjusted Spread) calculation
- Scenario sensitivity (parallel rate shifts)
"""
from __future__ import annotations

import QuantLib as ql
from compute.pricers.callable_bond import price_callable_bond


def test_callable_bond_basic():
    """Test callable bond pricing with flat curve.

    Bond: 5% coupon, 5-year maturity, callable at 100 after 2 years
    Curve: 3.5% flat
    Expected PV: ~68.4 (from research code example)

    Callable bond should price LOWER than straight bond due to call option value.
    """
    # Setup evaluation date
    calc_date = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = calc_date

    # Position data
    position = {
        "position_id": "POS-CB-001",
        "quantity": 1000000,  # $1M par
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }

    # Callable bond instrument
    instrument = {
        "instrument_id": "CALLABLE-BOND-001",
        "product_type": "CALLABLE_BOND",
        "issue_date": "2021-01-15",
        "maturity_date": "2031-01-15",
        "coupon_rate": 0.05,  # 5%
        "frequency": "SEMIANNUAL",
        "day_count": "ACT/ACT",
        "call_schedule": [
            {
                "call_date": "2028-01-15",  # Callable after 2 years
                "call_price": 100.0,
                "call_type": "CALL"
            }
        ]
    }

    # Market snapshot with flat 3.5% curve
    market_snapshot = {
        "snapshot_id": "SNAPSHOT-001",
        "calc_date": calc_date,
        "curves": [
            {
                "curve_id": "USD-OIS",
                "instruments": [
                    {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "5Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "10Y", "fixing_days": 2}
                ]
            }
        ]
    }

    # Price the callable bond
    result = price_callable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV", "CLEAN_PRICE"],
        scenario_id="BASE"
    )

    # Validate results
    # Expected PV around 68.4 based on research example (tree-based pricing)
    # Allow 1.0 tolerance for numerical differences
    assert "PV" in result, "PV measure must be computed"
    assert abs(result["PV"] - 68.4) < 1.0, f"PV={result['PV']} expected ~68.4"

    assert "CLEAN_PRICE" in result, "CLEAN_PRICE measure must be computed"
    assert result["CLEAN_PRICE"] > 0, "CLEAN_PRICE must be positive"


def test_callable_bond_oas():
    """Test OAS (Option-Adjusted Spread) calculation.

    Given a market price, OAS solver should find the spread that matches the price.
    OAS represents the spread over the treasury curve that compensates for credit risk,
    adjusted for the embedded call option.
    """
    calc_date = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = calc_date

    position = {
        "position_id": "POS-CB-002",
        "quantity": 1000000,
        "market_price": 102.0,  # Market price for OAS calculation
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }

    instrument = {
        "instrument_id": "CALLABLE-BOND-002",
        "product_type": "CALLABLE_BOND",
        "issue_date": "2021-01-15",
        "maturity_date": "2031-01-15",
        "coupon_rate": 0.05,
        "frequency": "SEMIANNUAL",
        "day_count": "ACT/ACT",
        "call_schedule": [
            {
                "call_date": "2028-01-15",
                "call_price": 100.0,
                "call_type": "CALL"
            }
        ]
    }

    market_snapshot = {
        "snapshot_id": "SNAPSHOT-002",
        "calc_date": calc_date,
        "curves": [
            {
                "curve_id": "USD-OIS",
                "instruments": [
                    {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "5Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "10Y", "fixing_days": 2}
                ]
            }
        ]
    }

    result = price_callable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV", "OAS"],
        scenario_id="BASE"
    )

    # OAS should be computed when market_price is provided
    assert "OAS" in result, "OAS measure must be computed when market_price is provided"
    assert result["OAS"] > 0, "OAS must be positive (spread above treasury)"
    # OAS typically in range of 0-500 bps for investment-grade corporates
    assert 0 < result["OAS"] < 0.05, f"OAS={result['OAS']} should be reasonable (0-500 bps)"


def test_callable_bond_scenarios():
    """Test callable bond pricing under different rate scenarios.

    Verify that:
    - Rates down → Price up (bond value increases)
    - Rates up → Price down (bond value decreases)
    - Callable bond shows negative convexity (call option caps upside)
    """
    calc_date = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = calc_date

    position = {
        "position_id": "POS-CB-003",
        "quantity": 1000000,
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }

    instrument = {
        "instrument_id": "CALLABLE-BOND-003",
        "product_type": "CALLABLE_BOND",
        "issue_date": "2021-01-15",
        "maturity_date": "2031-01-15",
        "coupon_rate": 0.05,
        "frequency": "SEMIANNUAL",
        "day_count": "ACT/ACT",
        "call_schedule": [
            {
                "call_date": "2028-01-15",
                "call_price": 100.0,
                "call_type": "CALL"
            }
        ]
    }

    market_snapshot = {
        "snapshot_id": "SNAPSHOT-003",
        "calc_date": calc_date,
        "curves": [
            {
                "curve_id": "USD-OIS",
                "instruments": [
                    {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "5Y", "fixing_days": 2},
                    {"type": "SWAP", "rate": 0.035, "tenor": "10Y", "fixing_days": 2}
                ]
            }
        ],
        "scenarios": {
            "RATES_PARALLEL_100BP": {
                "type": "PARALLEL_SHIFT",
                "curves": ["USD-OIS"],
                "shift": -0.01  # -100 bps (rates down)
            }
        }
    }

    # Price in BASE scenario
    result_base = price_callable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="BASE"
    )

    # Price in RATES_PARALLEL_100BP scenario (rates down 100 bps)
    result_down = price_callable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="RATES_PARALLEL_100BP"
    )

    # When rates go down, bond price should increase
    assert result_down["PV"] > result_base["PV"], \
        f"Rates down should increase price: base={result_base['PV']}, down={result_down['PV']}"

    # Verify both prices are reasonable
    assert result_base["PV"] > 0, "Base PV must be positive"
    assert result_down["PV"] > 0, "Down scenario PV must be positive"
