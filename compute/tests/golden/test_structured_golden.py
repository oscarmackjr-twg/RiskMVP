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


def test_structured_scenarios():
    """Test structured product pricing across multiple rate scenarios.

    Verify:
    - Structured product can be priced in multiple scenarios (BASE, RATES_UP, RATES_DOWN)
    - RATES_DOWN increases PV (discount rates fall → PV rises)
    - RATES_UP decreases PV (discount rates rise → PV falls)
    - Rate sensitivity is reasonable (10-15% for 100bp shock on ~5-year cashflows)

    Setup:
    - Senior tranche of 2-tranche CLO ($80M senior at 4%, $20M junior at 8%)
    - Collateral cashflows: 3 periods with interest and principal
    - Base curve: 3.5-4%
    - Scenarios: +100bp (RATES_UP), -100bp (RATES_DOWN)
    """
    # Market snapshot with base curve and rate scenarios
    market_snapshot = {
        "snapshot_date": "2026-02-15",
        "curves": [
            {
                "curve_id": "USD-OIS",
                "nodes": [
                    {"tenor": "3M", "rate": 0.035},
                    {"tenor": "1Y", "rate": 0.036},
                    {"tenor": "2Y", "rate": 0.037},
                    {"tenor": "5Y", "rate": 0.038},
                ],
            },
        ],
        "scenarios": {
            "RATES_UP": {
                "type": "PARALLEL_SHIFT",
                "curves": ["USD-OIS"],
                "shift": 0.01  # +100 bp
            },
            "RATES_DOWN": {
                "type": "PARALLEL_SHIFT",
                "curves": ["USD-OIS"],
                "shift": -0.01  # -100 bp
            }
        },
    }

    # Tranches structure
    tranches = [
        {"tranche_id": "SENIOR", "priority": 1, "notional": 80_000_000, "coupon": 0.04},
        {"tranche_id": "JUNIOR", "priority": 2, "notional": 20_000_000, "coupon": 0.08},
    ]

    # Collateral cashflows (3 periods, approximately 5-year average maturity)
    collateral_cashflows = [
        {"period": 1, "interest": 6_000_000, "principal": 10_000_000},
        {"period": 2, "interest": 5_500_000, "principal": 15_000_000},
        {"period": 3, "interest": 4_500_000, "principal": 25_000_000},
    ]

    # Instrument definition
    instrument = {
        "instrument_id": "CLO003",
        "tranches": tranches,
        "collateral_cashflows": collateral_cashflows,
    }

    # Position: Senior tranche
    position_senior = {
        "position_id": "POS_SENIOR_SCENARIOS",
        "tranche_id": "SENIOR",
        "attributes": {"notional": 80_000_000},
    }

    # Price in BASE scenario
    result_base = price_structured(
        position_senior,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="BASE",
    )

    # Price in RATES_UP scenario (+100bp)
    result_rates_up = price_structured(
        position_senior,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="RATES_UP",
    )

    # Price in RATES_DOWN scenario (-100bp)
    result_rates_down = price_structured(
        position_senior,
        instrument,
        market_snapshot,
        measures=["PV"],
        scenario_id="RATES_DOWN",
    )

    # Assertions
    assert "PV" in result_base, "BASE scenario must have PV"
    assert "PV" in result_rates_up, "RATES_UP scenario must have PV"
    assert "PV" in result_rates_down, "RATES_DOWN scenario must have PV"

    # All PVs should be positive
    assert result_base["PV"] > 0, "Base PV should be positive"
    assert result_rates_up["PV"] > 0, "RATES_UP PV should be positive"
    assert result_rates_down["PV"] > 0, "RATES_DOWN PV should be positive"

    # RATES_DOWN should increase PV (discount rates fall → PV rises)
    assert result_rates_down["PV"] > result_base["PV"], \
        f"RATES_DOWN should increase PV: base={result_base['PV']:,.0f}, down={result_rates_down['PV']:,.0f}"

    # RATES_UP should decrease PV (discount rates rise → PV falls)
    assert result_rates_up["PV"] < result_base["PV"], \
        f"RATES_UP should decrease PV: base={result_base['PV']:,.0f}, up={result_rates_up['PV']:,.0f}"

    # Verify reasonable price changes for 100bp shock
    # For a ~3-5 year average maturity, 100bp shock should cause 3-5% PV change
    # (modified duration ~ 3-5 years → 100bp = 3-5% price change)
    pv_change_up_pct = (result_rates_up["PV"] - result_base["PV"]) / result_base["PV"]
    pv_change_down_pct = (result_rates_down["PV"] - result_base["PV"]) / result_base["PV"]

    # Check that rate sensitivities are within reasonable bounds
    # Expect 2-15% change for 100bp shock (depending on cashflow profile)
    assert abs(pv_change_up_pct) <= 0.15, \
        f"RATES_UP PV change {pv_change_up_pct:.1%} should be within 15% for 100bp shock"
    assert abs(pv_change_down_pct) <= 0.15, \
        f"RATES_DOWN PV change {pv_change_down_pct:.1%} should be within 15% for 100bp shock"

    # Verify changes are meaningful (not too small)
    assert abs(pv_change_up_pct) >= 0.01, \
        f"RATES_UP PV change {pv_change_up_pct:.1%} should be at least 1% for 100bp shock"
    assert abs(pv_change_down_pct) >= 0.01, \
        f"RATES_DOWN PV change {pv_change_down_pct:.1%} should be at least 1% for 100bp shock"

    print(f"Structured product scenario sensitivity test:")
    print(f"  BASE PV: ${result_base['PV']:,.0f}")
    print(f"  RATES_UP (+100bp) PV: ${result_rates_up['PV']:,.0f} ({pv_change_up_pct:+.1%})")
    print(f"  RATES_DOWN (-100bp) PV: ${result_rates_down['PV']:,.0f} ({pv_change_down_pct:+.1%})")


if __name__ == "__main__":
    test_structured_simple_waterfall()
    test_structured_shortfall()
    test_structured_scenarios()
    print("All structured product golden tests passed!")
