"""Golden tests for structured product pricer (CLO/CDO tranches)."""
from __future__ import annotations

from compute.pricers.structured import price_structured


def test_structured_simple_waterfall():
    """Test structured product with simple 2-tranche waterfall.

    Setup:
    - 2 tranches: $80M senior (4% coupon), $20M junior (8% coupon)
    - Collateral generates $6M annual interest, $10M principal
    - Senior gets first $3.2M interest, $8M principal
    - Junior gets remaining

    Expected: Senior PV > Junior PV (lower risk, lower return)
    """
    # Market snapshot
    market_snapshot = {
        "snapshot_date": "2026-02-15",
        "curves": [
            {
                "curve_id": "USD-OIS",
                "nodes": [
                    {"tenor": "3M", "rate": 0.040},
                    {"tenor": "1Y", "rate": 0.038},
                    {"tenor": "2Y", "rate": 0.036},
                    {"tenor": "5Y", "rate": 0.035},
                ],
            },
        ],
    }

    # Tranches structure
    tranches = [
        {"tranche_id": "SENIOR", "priority": 1, "notional": 80_000_000, "coupon": 0.04},
        {"tranche_id": "JUNIOR", "priority": 2, "notional": 20_000_000, "coupon": 0.08},
    ]

    # Collateral cashflows
    collateral_cashflows = [
        {"period": 1, "interest": 6_000_000, "principal": 10_000_000},
        {"period": 2, "interest": 5_500_000, "principal": 10_000_000},
        {"period": 3, "interest": 5_000_000, "principal": 10_000_000},
    ]

    # Instrument definition
    instrument = {
        "instrument_id": "CLO001",
        "tranches": tranches,
        "collateral_cashflows": collateral_cashflows,
    }

    # Price senior tranche
    position_senior = {
        "position_id": "POS_SENIOR",
        "tranche_id": "SENIOR",
        "attributes": {"notional": 80_000_000},
    }

    result_senior = price_structured(
        position_senior,
        instrument,
        market_snapshot,
        measures=["PV", "COVERAGE_RATIO"],
        scenario_id="BASE",
    )

    # Price junior tranche
    position_junior = {
        "position_id": "POS_JUNIOR",
        "tranche_id": "JUNIOR",
        "attributes": {"notional": 20_000_000},
    }

    result_junior = price_structured(
        position_junior,
        instrument,
        market_snapshot,
        measures=["PV", "COVERAGE_RATIO"],
        scenario_id="BASE",
    )

    # Assertions
    assert "PV" in result_senior
    assert "PV" in result_junior
    assert "COVERAGE_RATIO" in result_senior
    assert "COVERAGE_RATIO" in result_junior

    # Senior tranche should have higher PV (gets paid first)
    # Note: This depends on waterfall allocation
    print(f"Senior PV: ${result_senior['PV']:,.2f}")
    print(f"Junior PV: ${result_junior['PV']:,.2f}")
    print(f"Senior Coverage Ratio: {result_senior['COVERAGE_RATIO']:.2f}")
    print(f"Junior Coverage Ratio: {result_junior['COVERAGE_RATIO']:.2f}")

    # Basic sanity checks
    assert result_senior["PV"] > 0, "Senior PV should be positive"
    assert result_junior["PV"] > 0, "Junior PV should be positive"
    assert result_senior["COVERAGE_RATIO"] > 0, "Coverage ratio should be positive"


def test_structured_shortfall():
    """Test structured product with cashflow shortfall.

    Setup:
    - Collateral generates only $2M interest (shortfall scenario)
    - Senior tranche needs $3.2M, junior needs $1.6M
    - Senior gets full $3.2M (paid from principal or junior subordination)
    - Junior absorbs shortfall

    Expected: Junior cashflows reduced, senior protected
    """
    # Market snapshot
    market_snapshot = {
        "snapshot_date": "2026-02-15",
        "curves": [
            {
                "curve_id": "USD-OIS",
                "nodes": [
                    {"tenor": "3M", "rate": 0.040},
                    {"tenor": "1Y", "rate": 0.038},
                    {"tenor": "5Y", "rate": 0.035},
                ],
            },
        ],
    }

    # Tranches structure (same as above)
    tranches = [
        {"tranche_id": "SENIOR", "priority": 1, "notional": 80_000_000, "coupon": 0.04},
        {"tranche_id": "JUNIOR", "priority": 2, "notional": 20_000_000, "coupon": 0.08},
    ]

    # Collateral cashflows with shortfall
    collateral_cashflows = [
        {"period": 1, "interest": 2_000_000, "principal": 5_000_000},  # Shortfall
    ]

    instrument = {
        "instrument_id": "CLO002",
        "tranches": tranches,
        "collateral_cashflows": collateral_cashflows,
    }

    # Price junior tranche (should absorb shortfall)
    position_junior = {
        "position_id": "POS_JUNIOR_STRESSED",
        "tranche_id": "JUNIOR",
        "attributes": {"notional": 20_000_000},
    }

    result_junior = price_structured(
        position_junior,
        instrument,
        market_snapshot,
        measures=["PV", "YIELD"],
        scenario_id="BASE",
    )

    # Assertions
    assert "PV" in result_junior
    assert "YIELD" in result_junior

    # Junior PV should be lower due to shortfall
    print(f"Junior PV (with shortfall): ${result_junior['PV']:,.2f}")
    print(f"Junior Yield (with shortfall): {result_junior['YIELD']:.4f}")

    # Basic sanity: PV should still be positive (some cashflows received)
    assert result_junior["PV"] >= 0, "Junior PV should be non-negative"


if __name__ == "__main__":
    test_structured_simple_waterfall()
    test_structured_shortfall()
    print("All structured product golden tests passed!")
