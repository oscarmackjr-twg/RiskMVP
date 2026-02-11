"""Golden tests for floating-rate instrument pricer.

Tests validate QuantLib FloatingRateBond pricing with multi-curve framework:
- Basic floater pricing (near par with flat curve)
- Capped floater pricing (value reduction in rising rate environment)
- Multi-curve basis spread validation
"""
from __future__ import annotations

import pytest
import QuantLib as ql
from compute.pricers.floating_rate import price_floating_rate


def test_floating_rate_basic():
    """Test basic floating-rate note pricing with flat curve.

    3M SOFR floater, quarterly resets, +150 bps spread, 3-year maturity.
    Flat 3.5% SOFR curve, 3.4% OIS curve (10 bp basis).

    Expected: PV close to par (100) since floating rate adjusts to market.
    """
    position = {
        "position_id": "POS001",
        "product_type": "FLOATING_RATE",
        "attributes": {
            "as_of_date": "2026-01-15",
        }
    }

    instrument = {
        "instrument_id": "FRN001",
        "terms": {
            "issue_date": "2024-01-15",
            "maturity_date": "2027-01-15",
            "face_value": 100.0,
            "index": "SOFR-3M",
            "spread": 0.015,  # 150 bps
            "reset_frequency": "Quarterly",
            "day_count": "ACT/360",
        }
    }

    # Flat 3.5% SOFR curve, 3.4% OIS curve
    market_snapshot = {
        "snapshot_id": "SNAP001",
        "calc_date": ql.Date(15, 1, 2026),
        "ois_instruments": [
            {"type": "DEPOSIT", "rate": 0.034, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.034, "tenor": "1Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.034, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.034, "tenor": "3Y", "fixing_days": 2},
        ],
        "sofr_instruments": [
            {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "1Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "3Y", "fixing_days": 2},
        ],
    }

    result = price_floating_rate(
        position=position,
        instrument=instrument,
        market_snapshot=market_snapshot,
        measures=["PV", "DV01"],
        scenario_id="BASE",
    )

    # Floating-rate note should trade near par with flat curve
    assert "PV" in result
    assert abs(result["PV"] - 100.0) < 2.0, f"Expected PV near 100, got {result['PV']:.4f}"

    # DV01 should be small for floaters (they reset to market)
    assert "DV01" in result
    assert abs(result["DV01"]) < 0.5, f"Expected small DV01 for floater, got {result['DV01']:.4f}"


def test_floating_rate_with_cap():
    """Test floating-rate note with embedded cap.

    Same floater but with 5% cap and steep upward-sloping curve (3% -> 6%).

    Expected: PV < par (cap reduces value in rising rate environment).
    """
    position = {
        "position_id": "POS002",
        "product_type": "FLOATING_RATE",
        "attributes": {
            "as_of_date": "2026-01-15",
        }
    }

    instrument = {
        "instrument_id": "FRN002",
        "terms": {
            "issue_date": "2024-01-15",
            "maturity_date": "2027-01-15",
            "face_value": 100.0,
            "index": "SOFR-3M",
            "spread": 0.015,  # 150 bps
            "cap": 0.05,  # 5% cap
            "reset_frequency": "Quarterly",
            "day_count": "ACT/360",
        }
    }

    # Steep upward-sloping curve: 3% short end -> 6% long end
    market_snapshot = {
        "snapshot_id": "SNAP002",
        "calc_date": ql.Date(15, 1, 2026),
        "ois_instruments": [
            {"type": "DEPOSIT", "rate": 0.030, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.040, "tenor": "1Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.050, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.060, "tenor": "3Y", "fixing_days": 2},
        ],
        "sofr_instruments": [
            {"type": "DEPOSIT", "rate": 0.031, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.041, "tenor": "1Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.051, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.061, "tenor": "3Y", "fixing_days": 2},
        ],
    }

    result = price_floating_rate(
        position=position,
        instrument=instrument,
        market_snapshot=market_snapshot,
        measures=["PV", "DV01"],
        scenario_id="BASE",
    )

    # Capped floater in rising rate environment should trade below par
    assert "PV" in result
    assert result["PV"] < 98.0, f"Expected PV < 98 for capped floater, got {result['PV']:.4f}"

    # Cap reduces upside, so value lower than uncapped floater
    assert result["PV"] < 100.0


def test_floating_rate_multi_curve():
    """Test multi-curve framework with basis spread.

    Price with and without basis spread between OIS and SOFR curves.
    Validates that multi-curve framework correctly separates discount and projection.
    """
    position = {
        "position_id": "POS003",
        "product_type": "FLOATING_RATE",
        "attributes": {
            "as_of_date": "2026-01-15",
        }
    }

    instrument = {
        "instrument_id": "FRN003",
        "terms": {
            "issue_date": "2024-01-15",
            "maturity_date": "2027-01-15",
            "face_value": 100.0,
            "index": "SOFR-3M",
            "spread": 0.010,  # 100 bps spread
            "reset_frequency": "Quarterly",
            "day_count": "ACT/360",
        }
    }

    # Market 1: No basis spread (OIS = SOFR)
    market_no_basis = {
        "snapshot_id": "SNAP003A",
        "calc_date": ql.Date(15, 1, 2026),
        "ois_instruments": [
            {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "3Y", "fixing_days": 2},
        ],
        "sofr_instruments": [
            {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "3Y", "fixing_days": 2},
        ],
    }

    # Market 2: 20bp basis spread (SOFR = OIS + 20bp)
    market_with_basis = {
        "snapshot_id": "SNAP003B",
        "calc_date": ql.Date(15, 1, 2026),
        "ois_instruments": [
            {"type": "DEPOSIT", "rate": 0.035, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.035, "tenor": "3Y", "fixing_days": 2},
        ],
        "sofr_instruments": [
            {"type": "DEPOSIT", "rate": 0.037, "tenor": "3M", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.037, "tenor": "2Y", "fixing_days": 2},
            {"type": "SWAP", "rate": 0.037, "tenor": "3Y", "fixing_days": 2},
        ],
    }

    result_no_basis = price_floating_rate(
        position=position,
        instrument=instrument,
        market_snapshot=market_no_basis,
        measures=["PV"],
        scenario_id="BASE",
    )

    result_with_basis = price_floating_rate(
        position=position,
        instrument=instrument,
        market_snapshot=market_with_basis,
        measures=["PV"],
        scenario_id="BASE",
    )

    # PV should differ when basis spread changes
    # With higher SOFR curve, coupons project higher -> PV higher
    pv_diff = abs(result_with_basis["PV"] - result_no_basis["PV"])
    assert pv_diff > 0.1, (
        f"Expected significant PV difference with basis spread, "
        f"got {result_no_basis['PV']:.4f} vs {result_with_basis['PV']:.4f}"
    )

    # Higher forward SOFR -> higher projected coupons -> higher PV
    assert result_with_basis["PV"] > result_no_basis["PV"], (
        "Expected higher PV with higher SOFR curve"
    )
