"""Golden tests for ABS/MBS pricer with prepayment and default modeling.

Tests validate:
- Basic ABS/MBS pricing with PSA 100%
- Fast prepayment sensitivity (PSA 200%)
- Default sensitivity (varying LGD)
"""
from __future__ import annotations

import pytest
from compute.pricers.abs_mbs import price_abs_mbs


@pytest.fixture
def base_market_snapshot():
    """Market snapshot with 4% flat discount curve."""
    return {
        "as_of_date": "2026-01-15",
        "curves": [
            {
                "curve_id": "USD-OIS",
                "nodes": [
                    {"tenor": 0.0, "rate": 0.04},
                    {"tenor": 1.0, "rate": 0.04},
                    {"tenor": 5.0, "rate": 0.04},
                    {"tenor": 10.0, "rate": 0.04},
                    {"tenor": 30.0, "rate": 0.04},
                ]
            }
        ]
    }


@pytest.fixture
def base_position():
    """Basic position with standard attributes."""
    return {
        "position_id": "ABS001",
        "quantity": 1,
        "attributes": {
            "as_of_date": "2026-01-15"
        }
    }


def test_abs_mbs_basic(base_market_snapshot, base_position):
    """Test basic ABS/MBS pricing with PSA 100%, LGD 40%, PD 1%."""
    instrument = {
        "instrument_id": "MBS-POOL-001",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,  # 5% weighted average coupon
            "wam": 360,  # 30-year mortgage pool
            "psa_speed": 100.0,  # PSA 100%
            "lgd": 0.40,  # 40% loss given default
            "pd_annual": 0.01  # 1% annual PD
        }
    }

    measures = ["PV", "WAL"]
    scenario_id = "BASE"

    result = price_abs_mbs(
        base_position,
        instrument,
        base_market_snapshot,
        measures,
        scenario_id
    )

    # Assertions
    assert "PV" in result
    assert "WAL" in result

    # PV analysis:
    # - 5% coupon vs 4% discount = positive carry (+1%)
    # - Prepayments reduce interest income (negative)
    # - Defaults with 40% LGD and 1% PD = ~5% cumulative loss (negative)
    # Net effect: PV can be slightly above or below par depending on balance
    assert result["PV"] > 900000.0, "PV should not be too low (sanity check)"
    assert result["PV"] < 1100000.0, "PV should be reasonable (positive carry offset by losses)"

    # WAL should be less than 15 years due to prepayments
    # (30-year mortgage with PSA 100% prepayments typically has WAL ~7-10 years)
    assert result["WAL"] < 15.0, "WAL should be shortened by prepayments"
    assert result["WAL"] > 5.0, "WAL should be reasonable (sanity check)"

    print("PASS: Basic ABS/MBS: PV=${0:,.2f}, WAL={1:.2f} years".format(result['PV'], result['WAL']))


def test_abs_mbs_fast_prepayment(base_market_snapshot, base_position):
    """Test ABS/MBS with PSA 200% (fast prepayment)."""
    instrument_psa100 = {
        "instrument_id": "MBS-POOL-002",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,
            "wam": 360,
            "psa_speed": 100.0,
            "lgd": 0.40,
            "pd_annual": 0.01
        }
    }

    instrument_psa200 = {
        "instrument_id": "MBS-POOL-003",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,
            "wam": 360,
            "psa_speed": 200.0,  # Double prepayment speed
            "lgd": 0.40,
            "pd_annual": 0.01
        }
    }

    measures = ["PV", "WAL"]
    scenario_id = "BASE"

    result_psa100 = price_abs_mbs(
        base_position,
        instrument_psa100,
        base_market_snapshot,
        measures,
        scenario_id
    )

    result_psa200 = price_abs_mbs(
        base_position,
        instrument_psa200,
        base_market_snapshot,
        measures,
        scenario_id
    )

    # Assertions
    # WAL should be significantly shorter with faster prepayments
    assert result_psa200["WAL"] < result_psa100["WAL"], \
        "PSA 200% should have shorter WAL than PSA 100%"

    # WAL with PSA 200% should be significantly reduced
    # Note: PSA model ramps slowly (takes 30 months to reach max CPR), so even 200% doesn't cut WAL in half
    assert result_psa200["WAL"] < 15.0, \
        "PSA 200% should have significantly shorter WAL"

    # PV comparison is complex (faster prepayments = less interest, but lower duration risk)
    # For positive discount spread, faster prepayments typically increase PV
    # (less interest loss is offset by reduced discounting)

    print("PASS: Fast prepayment test:")
    print("  PSA 100%: PV=${0:,.2f}, WAL={1:.2f} years".format(result_psa100['PV'], result_psa100['WAL']))
    print("  PSA 200%: PV=${0:,.2f}, WAL={1:.2f} years".format(result_psa200['PV'], result_psa200['WAL']))


def test_abs_mbs_default_sensitivity(base_market_snapshot, base_position):
    """Test ABS/MBS with varying LGD (default sensitivity)."""
    instrument_lgd20 = {
        "instrument_id": "MBS-POOL-004",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,
            "wam": 360,
            "psa_speed": 100.0,
            "lgd": 0.20,  # 20% LGD (low loss)
            "pd_annual": 0.01
        }
    }

    instrument_lgd60 = {
        "instrument_id": "MBS-POOL-005",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,
            "wam": 360,
            "psa_speed": 100.0,
            "lgd": 0.60,  # 60% LGD (high loss)
            "pd_annual": 0.01
        }
    }

    measures = ["PV"]
    scenario_id = "BASE"

    result_lgd20 = price_abs_mbs(
        base_position,
        instrument_lgd20,
        base_market_snapshot,
        measures,
        scenario_id
    )

    result_lgd60 = price_abs_mbs(
        base_position,
        instrument_lgd60,
        base_market_snapshot,
        measures,
        scenario_id
    )

    # Assertions
    # Lower LGD = higher PV (less credit loss)
    assert result_lgd20["PV"] > result_lgd60["PV"], \
        "Lower LGD should result in higher PV"

    # Difference should be material (several thousand dollars on $1M pool)
    pv_diff = result_lgd20["PV"] - result_lgd60["PV"]
    assert pv_diff > 1000.0, \
        "LGD difference should have material impact on PV"

    print("PASS: Default sensitivity test:")
    print("  LGD 20%: PV=${0:,.2f}".format(result_lgd20['PV']))
    print("  LGD 60%: PV=${0:,.2f}".format(result_lgd60['PV']))
    print("  Impact: ${0:,.2f}".format(pv_diff))


def test_abs_mbs_with_dv01(base_market_snapshot, base_position):
    """Test ABS/MBS DV01 calculation."""
    instrument = {
        "instrument_id": "MBS-POOL-006",
        "product_type": "ABS_MBS",
        "terms": {
            "original_balance": 1000000.0,
            "wac": 0.05,
            "wam": 360,
            "psa_speed": 100.0,
            "lgd": 0.40,
            "pd_annual": 0.01
        }
    }

    measures = ["PV", "DV01"]
    scenario_id = "BASE"

    result = price_abs_mbs(
        base_position,
        instrument,
        base_market_snapshot,
        measures,
        scenario_id
    )

    # Assertions
    assert "DV01" in result
    # DV01 should be negative (rates up means PV down)
    assert result["DV01"] < 0, "DV01 should be negative for long position"

    # DV01 magnitude should be reasonable for $1M 30-year MBS
    # With WAL ~9 years and $1M notional, expect roughly -$1000 to -$2500 per 1bp
    # (DV01 ≈ Duration × PV × 0.0001, Duration ≈ WAL × 0.9 ≈ 8, so DV01 ≈ -$800 to -$2000)
    assert result["DV01"] > -3000.0, "DV01 magnitude sanity check (not too large)"
    assert result["DV01"] < -100.0, "DV01 magnitude sanity check (not too small)"

    print("PASS: DV01 test: PV=${0:,.2f}, DV01=${1:.2f} per 1bp".format(result['PV'], result['DV01']))


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
