#!/usr/bin/env python3
"""seed-market-data.py — Fetch real market data from FRED + Frankfurter and POST to IPRS.

Free data sources:
  - FRED (Federal Reserve Economic Data): Treasury yields, SOFR, credit spreads
  - Frankfurter (ECB rates): FX spot rates

Usage:
    python scripts/seed-market-data.py --fred-key YOUR_KEY [--base-url http://localhost:8001]

Get a free FRED API key at: https://fred.stlouisfed.org/docs/api/api_key.html
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    sys.exit(1)

# FRED series for Treasury constant maturity rates
TREASURY_SERIES = {
    "DGS1MO": "1M",
    "DGS3MO": "3M",
    "DGS6MO": "6M",
    "DGS1":   "1Y",
    "DGS2":   "2Y",
    "DGS3":   "3Y",
    "DGS5":   "5Y",
    "DGS7":   "7Y",
    "DGS10":  "10Y",
    "DGS20":  "20Y",
    "DGS30":  "30Y",
}

# Additional FRED series
EXTRA_SERIES = {
    "DFF":        "Federal Funds Effective Rate",
    "SOFR":       "Secured Overnight Financing Rate",
    "BAMLC0A0CM": "ICE BofA US Corporate OAS",
}

# Frankfurter FX pairs to fetch (base=USD)
FX_CURRENCIES = ["EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]


def fetch_fred_series(series_id: str, api_key: str) -> float | None:
    """Fetch the most recent observation for a FRED series."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 5,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    observations = resp.json().get("observations", [])
    for obs in observations:
        val = obs.get("value", ".")
        if val != ".":
            return float(val)
    return None


def fetch_fx_rates() -> dict[str, float]:
    """Fetch latest FX rates from Frankfurter (ECB reference rates, USD base)."""
    url = "https://api.frankfurter.app/latest"
    params = {"from": "USD", "to": ",".join(FX_CURRENCIES)}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("rates", {})


def build_snapshot(
    treasury_rates: dict[str, float],
    sofr: float | None,
    fed_funds: float | None,
    credit_spread: float | None,
    fx_rates: dict[str, float],
) -> dict:
    """Build an IPRS MarketDataSnapshot from fetched data."""
    now = datetime.now(timezone.utc)
    as_of = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    snapshot_id = f"MKT-FRED-{now.strftime('%Y%m%d-%H%M')}"

    # OIS discount curve from Fed Funds / SOFR + Treasury rates
    ois_nodes = []
    overnight_rate = sofr if sofr is not None else fed_funds
    if overnight_rate is not None:
        ois_nodes.append({"tenor": "ON", "zero_rate": round(overnight_rate / 100, 6)})
    for series_id, tenor in TREASURY_SERIES.items():
        rate = treasury_rates.get(series_id)
        if rate is not None:
            ois_nodes.append({"tenor": tenor, "zero_rate": round(rate / 100, 6)})

    curves = [
        {
            "curve_id": "USD-OIS",
            "curve_type": "DISCOUNT",
            "nodes": ois_nodes,
        }
    ]

    # Credit spread curve from ICE BofA index
    if credit_spread is not None:
        curves.append({
            "curve_id": "CREDIT-SPREAD",
            "curve_type": "SPREAD",
            "nodes": [
                {"tenor": "1Y", "zero_rate": round(credit_spread / 10000, 6)},
                {"tenor": "3Y", "zero_rate": round(credit_spread / 10000, 6)},
                {"tenor": "5Y", "zero_rate": round(credit_spread / 10000, 6)},
                {"tenor": "10Y", "zero_rate": round(credit_spread / 10000, 6)},
            ],
        })

    # Loan spread (use credit spread + buffer, or default)
    loan_spread_bps = (credit_spread or 200) + 50
    curves.append({
        "curve_id": "LOAN-SPREAD",
        "curve_type": "SPREAD",
        "nodes": [
            {"tenor": "1M", "zero_rate": round(loan_spread_bps / 10000, 6)},
            {"tenor": "6M", "zero_rate": round(loan_spread_bps / 10000, 6)},
            {"tenor": "1Y", "zero_rate": round(loan_spread_bps / 10000, 6)},
        ],
    })

    # FI spread
    fi_spread_bps = (credit_spread or 150)
    curves.append({
        "curve_id": "FI-SPREAD",
        "curve_type": "SPREAD",
        "nodes": [
            {"tenor": "1Y", "zero_rate": round(fi_spread_bps / 10000, 6)},
        ],
    })

    # FX spots (Frankfurter gives CCY per 1 USD, IPRS uses CCYUSD convention)
    fx_spots = []
    for ccy, rate in fx_rates.items():
        # Frankfurter: 1 USD = X CCY, so CCYUSD = 1/rate
        fx_spots.append({
            "pair": f"{ccy}USD",
            "spot": round(1.0 / rate, 6),
            "ts": as_of,
        })

    return {
        "snapshot_id": snapshot_id,
        "as_of_time": as_of,
        "vendor": "FRED+Frankfurter",
        "universe_id": "USD",
        "fx_spots": fx_spots,
        "curves": curves,
        "quality": {"dq_status": "PASS", "issues": []},
    }


def main():
    parser = argparse.ArgumentParser(description="Seed IPRS with real market data from FRED + Frankfurter")
    parser.add_argument("--fred-key", required=True, help="FRED API key (free at fred.stlouisfed.org)")
    parser.add_argument("--base-url", default="http://localhost:8001", help="Marketdata service URL")
    parser.add_argument("--dry-run", action="store_true", help="Print snapshot JSON without POSTing")
    args = parser.parse_args()

    print("=== IPRS Market Data Seeder ===")

    # 1. Fetch Treasury yields from FRED
    print("\n[1/4] Fetching Treasury yield curve from FRED...")
    treasury_rates = {}
    for series_id, tenor in TREASURY_SERIES.items():
        rate = fetch_fred_series(series_id, args.fred_key)
        if rate is not None:
            treasury_rates[series_id] = rate
            print(f"  {tenor}: {rate}%")
        else:
            print(f"  {tenor}: N/A")

    # 2. Fetch SOFR + Fed Funds + credit spread
    print("\n[2/4] Fetching SOFR, Fed Funds, credit spread from FRED...")
    sofr = fetch_fred_series("SOFR", args.fred_key)
    fed_funds = fetch_fred_series("DFF", args.fred_key)
    credit_spread = fetch_fred_series("BAMLC0A0CM", args.fred_key)
    print(f"  SOFR:          {sofr}%" if sofr else "  SOFR:          N/A")
    print(f"  Fed Funds:     {fed_funds}%" if fed_funds else "  Fed Funds:     N/A")
    print(f"  Credit Spread: {credit_spread} bps" if credit_spread else "  Credit Spread: N/A")

    # 3. Fetch FX rates from Frankfurter
    print("\n[3/4] Fetching FX rates from Frankfurter (ECB)...")
    fx_rates = fetch_fx_rates()
    for ccy, rate in fx_rates.items():
        print(f"  {ccy}USD: {1.0/rate:.6f}")

    # 4. Build and POST snapshot
    print("\n[4/4] Building market data snapshot...")
    snapshot = build_snapshot(treasury_rates, sofr, fed_funds, credit_spread, fx_rates)

    if args.dry_run:
        print("\n--- Dry Run: Snapshot JSON ---")
        print(json.dumps(snapshot, indent=2))
        return

    url = f"{args.base_url}/api/v1/marketdata/snapshots"
    print(f"  POSTing to {url}...")
    resp = requests.post(url, json=snapshot, timeout=15)

    if resp.status_code in (200, 201):
        result = resp.json()
        sid = result.get("snapshot_id", snapshot["snapshot_id"])
        print(f"\n  Snapshot created: {sid}")
        print(f"\n=== Done ===")
        print(f"Use this snapshot_id in run requests: {sid}")
    else:
        print(f"\n  ERROR: HTTP {resp.status_code}")
        print(f"  {resp.text[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
