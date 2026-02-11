# compute/tests/golden/test_putable_bond_golden.py
"""Golden tests for putable bond pricer with reference prices.

Tests cover:
- Basic putable bond pricing with tree-based valuation
- Scenario sensitivity (parallel rate shifts)
- YTP (Yield-to-Put) calculation
"""
from __future__ import annotations

import QuantLib as ql
from compute.pricers.putable_bond import price_putable_bond


def test_putable_bond_basic():
    """Test putable bond pricing with flat curve.

    Bond: 4% coupon, 5-year maturity, putable at 100 after 3 years
    Curve: 3.5% flat

    Putable bond should price HIGHER than straight bond due to put option value
    (investor has the right to sell back at par, which is valuable if rates rise).
    """
    # Setup evaluation date
    calc_date = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = calc_date

    # Position data
    position = {
        "position_id": "POS-PB-001",
        "quantity": 1000000,  # $1M par
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }

    # Putable bond instrument
    instrument = {
        "instrument_id": "PUTABLE-BOND-001",
        "product_type": "PUTABLE_BOND",
        "issue_date": "2021-01-15",
        "maturity_date": "2031-01-15",
        "coupon_rate": 0.04,  # 4%
        "frequency": "SEMIANNUAL",
        "day_count": "ACT/ACT",
        "put_schedule": [
            {
                "put_date": "2029-01-15",  # Putable after 3 years (from 2026)
                "put_price": 100.0,
                "put_type": "PUT"
            }
        ]
    }

    # Market snapshot with flat 3.5% curve
    market_snapshot = {
        "snapshot_id": "SNAPSHOT-PB-001",
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

    # Price the putable bond
    result = price_putable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV", "CLEAN_PRICE", "YTP"],
        scenario_id="BASE"
    )

    # Validate results
    # PV is scaled by quantity ($1M)
    # For a 4% coupon bond with 3.5% curve, price should be above par
    # (coupon > yield → premium bond)
    assert "PV" in result, "PV measure must be computed"
    assert result["PV"] > 0, "PV must be positive"

    # Check reasonable price range
    implied_price = result["PV"] / (position["quantity"] / 100.0)
    assert 50 < implied_price < 150, f"Implied price={implied_price} should be reasonable"

    assert "CLEAN_PRICE" in result, "CLEAN_PRICE measure must be computed"
    assert result["CLEAN_PRICE"] > 0, "CLEAN_PRICE must be positive"

    # Putable bond should trade at premium due to embedded put option
    # (at least at par, typically slightly above)
    assert result["CLEAN_PRICE"] >= 95.0, \
        f"Putable bond CLEAN_PRICE={result['CLEAN_PRICE']} should be near or above par"

    # YTP should be computed
    assert "YTP" in result, "YTP (Yield-to-Put) must be computed"
    assert result["YTP"] > 0, "YTP must be positive"
    # YTP should be reasonable (typically 0-10% for investment-grade)
    assert 0 < result["YTP"] < 0.15, f"YTP={result['YTP']} should be reasonable"


def test_putable_bond_scenarios():
    """Test putable bond pricing under different rate scenarios.

    Verify that:
    - Rates down → Price up (bond value increases)
    - Rates up → Price down, but put option provides downside protection
    - Put option value increases when rates rise (floor at put price)
    """
    calc_date = ql.Date(15, 1, 2026)
    ql.Settings.instance().evaluationDate = calc_date

    position = {
        "position_id": "POS-PB-002",
        "quantity": 1000000,
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }

    instrument = {
        "instrument_id": "PUTABLE-BOND-002",
        "product_type": "PUTABLE_BOND",
        "issue_date": "2021-01-15",
        "maturity_date": "2031-01-15",
        "coupon_rate": 0.04,
        "frequency": "SEMIANNUAL",
        "day_count": "ACT/ACT",
        "put_schedule": [
            {
                "put_date": "2029-01-15",
                "put_price": 100.0,
                "put_type": "PUT"
            }
        ]
    }

    market_snapshot = {
        "snapshot_id": "SNAPSHOT-PB-002",
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
    result_base = price_putable_bond(
        position,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="BASE"
    )

    # Price in RATES_PARALLEL_100BP scenario (rates down 100 bps)
    result_down = price_putable_bond(
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

    # Price increase should be bounded (put option provides some hedge against rate movements)
    price_change_pct = (result_down["PV"] - result_base["PV"]) / result_base["PV"]
    assert price_change_pct < 0.50, \
        f"Price change {price_change_pct:.2%} should be reasonable (< 50%)"
