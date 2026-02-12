#!/usr/bin/env python3
"""convert_assets_to_positions.py — Convert SFC loan assets CSV to IPRS position snapshot.

Reads current_assets_lmi.txt (or similar CSV) and produces a positions.json
compatible with the IPRS run orchestrator.

Usage:
    python scripts/convert_assets_to_positions.py \
        --input demo/inputs/current_assets_lmi.txt \
        --output demo/inputs/positions_lmi.json \
        [--as-of-date 2026-01-23] \
        [--portfolio-node BOOK-LMI-LOANS] \
        [--cashflow-months 6] \
        [--post http://localhost:8005/api/v1/portfolios/positions]
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, timedelta
from typing import Any


def parse_date(s: str) -> date:
    """Parse date from various formats found in the CSV."""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {s!r}")


def next_payment_date_after(anchor: date, as_of: date) -> date:
    """Find the first payment date on or after as_of, based on anchor day-of-month."""
    day = anchor.day
    # Start from the month of as_of
    year, month = as_of.year, as_of.month
    try:
        candidate = date(year, month, day)
    except ValueError:
        # Day doesn't exist in this month (e.g., 31 in Feb) — use last day
        if month == 12:
            candidate = date(year + 1, 1, day)
        else:
            candidate = date(year, month + 1, day)

    if candidate > as_of:
        return candidate

    # Move to next month
    if month == 12:
        return date(year + 1, 1, day)
    else:
        try:
            return date(year, month + 1, day)
        except ValueError:
            # Handle months with fewer days
            if month + 1 == 12:
                return date(year + 1, 1, day)
            return date(year, month + 2, day)


def add_months(d: date, months: int) -> date:
    """Add months to a date, keeping the same day-of-month where possible."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def generate_cashflows(
    current_balance: float,
    annual_rate: float,
    monthly_payment: float,
    first_pay_date: date,
    num_months: int,
) -> list[dict[str, Any]]:
    """Generate level-pay amortization cashflows.

    Uses the simple monthly amortization formula:
      interest = balance * (annual_rate / 12)
      principal = payment - interest
    """
    cashflows = []
    balance = current_balance
    monthly_rate = annual_rate / 12.0

    for i in range(num_months):
        if balance <= 0.01:
            break
        pay_date = add_months(first_pay_date, i)
        interest = balance * monthly_rate
        principal = monthly_payment - interest

        # If principal would exceed remaining balance, adjust
        if principal > balance:
            principal = balance
            interest = balance * monthly_rate
            payment = principal + interest
        else:
            payment = monthly_payment

        # Skip if payment doesn't cover interest (negative amortization guard)
        if principal < 0:
            principal = 0.0
            payment = interest

        cashflows.append({
            "pay_date": pay_date.strftime("%Y-%m-%d"),
            "interest": round(interest, 6),
            "principal": round(principal, 6),
            "amount": round(payment, 6),
        })
        balance -= principal

    return cashflows


def safe_float(val: str, default: float = 0.0) -> float:
    """Convert string to float, returning default on failure."""
    try:
        v = float(val.strip())
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except (ValueError, AttributeError):
        return default


def safe_int(val: str, default: int = 0) -> int:
    """Convert string to int, returning default on failure."""
    try:
        return int(float(val.strip()))
    except (ValueError, AttributeError):
        return default


def convert_row(row: dict[str, str], as_of: date, cashflow_months: int) -> dict[str, Any] | None:
    """Convert a single CSV row to an IPRS position dict."""
    loan_id = row.get("SELLER Loan #", "").strip()
    if not loan_id:
        return None

    current_balance = safe_float(row.get("Current Balance", "0"))
    if current_balance <= 0:
        return None

    apr = safe_float(row.get("APR", "0"))
    coupon_rate = apr / 100.0  # CSV has APR as percentage (e.g., 11.9 = 11.9%)

    term_months = safe_int(row.get("Term", "0"))
    if term_months <= 0:
        term_months = safe_int(row.get("loan_term", "120"))

    monthly_payment = safe_float(row.get("Monthly Payment", "0"))
    if monthly_payment <= 0:
        # Calculate from principal/rate/term if missing
        if coupon_rate > 0 and term_months > 0:
            r = coupon_rate / 12.0
            monthly_payment = current_balance * (r * math.pow(1 + r, term_months)) / (math.pow(1 + r, term_months) - 1)
        else:
            monthly_payment = current_balance / max(term_months, 1)

    city = row.get("Property City", row.get("City", "")).strip()
    state = row.get("Property State", row.get("State", "")).strip()
    fico = safe_int(row.get("FICO Borrower", "0"))
    loan_program = row.get("loan program", "").strip()
    platform = row.get("Platform", "PRIME").strip()
    asset_type = row.get("Asset Type", "").strip()

    # Determine payment anchor date
    pmt_date_str = row.get("Monthly Payment Date", "").strip()
    if pmt_date_str:
        try:
            anchor = parse_date(pmt_date_str)
            first_pay = next_payment_date_after(anchor, as_of)
        except ValueError:
            # Default: 23rd of next month
            first_pay = next_payment_date_after(date(as_of.year, as_of.month, 23), as_of)
    else:
        first_pay = next_payment_date_after(date(as_of.year, as_of.month, 23), as_of)

    # Compute last payment date (one month before first future payment)
    last_payment = add_months(first_pay, -1)

    # Generate cashflow schedule
    cashflows = generate_cashflows(
        current_balance, coupon_rate, monthly_payment, first_pay, cashflow_months,
    )

    # Risk modeling parameters from CSV (if available)
    cdr = safe_float(row.get("cdr", "0"))
    cpr = safe_float(row.get("constant_cpr", "0"))
    loan_type = row.get("type", "standard").strip()

    position = {
        "position_id": f"POS-{loan_id}",
        "instrument_id": loan_id,
        "product_type": "AMORT_LOAN",
        "quantity": 1.0,
        "attributes": {
            "as_of_date": as_of.strftime("%Y-%m-%d"),
            "last_payment_date": last_payment.strftime("%Y-%m-%d"),
            "current_principal": round(current_balance, 2),
            "coupon_rate": round(coupon_rate, 10),
            "monthly_payment": round(monthly_payment, 2),
            "platform": platform.upper(),
            "fico": fico,
            "state": state,
            "city": city,
            "loan_program": loan_program,
            "term_months": term_months,
            "asset_type": asset_type,
            "loan_type": loan_type,
            "cdr": round(cdr, 6),
            "cpr": round(cpr, 6),
            "instrument": {
                "instrument_type": "AMORT_LOAN",
                "terms": {
                    "currency": "USD",
                    "day_count": "30/360",
                    "payment_frequency": "MONTHLY",
                    "original_term_months": term_months,
                    "coupon_rate": round(coupon_rate, 10),
                },
                "risk_modeling": {
                    "discount_curve": "USD-OIS",
                    "spread_curve": "LOAN-SPREAD",
                },
            },
            "cashflows": cashflows,
        },
    }

    return position


def main():
    parser = argparse.ArgumentParser(
        description="Convert SFC loan asset CSV to IPRS position snapshot JSON"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to CSV file (e.g., demo/inputs/current_assets_lmi.txt)"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output JSON file (default: stdout)"
    )
    parser.add_argument(
        "--as-of-date", default=None,
        help="Valuation date YYYY-MM-DD (default: today)"
    )
    parser.add_argument(
        "--portfolio-node", default="BOOK-LMI-LOANS",
        help="Portfolio node ID (default: BOOK-LMI-LOANS)"
    )
    parser.add_argument(
        "--cashflow-months", type=int, default=6,
        help="Number of future cashflow months to generate (default: 6)"
    )
    parser.add_argument(
        "--post", default=None,
        help="POST snapshot to this URL after conversion"
    )
    parser.add_argument(
        "--summary", action="store_true",
        help="Print portfolio summary statistics"
    )
    args = parser.parse_args()

    # Parse as-of date
    if args.as_of_date:
        as_of = datetime.strptime(args.as_of_date, "%Y-%m-%d").date()
    else:
        as_of = date.today()

    # Read CSV
    print(f"Reading {args.input}...", file=sys.stderr)
    positions = []
    skipped = 0

    with open(args.input, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pos = convert_row(row, as_of, args.cashflow_months)
            if pos:
                positions.append(pos)
            else:
                skipped += 1

    print(f"Converted {len(positions)} positions ({skipped} skipped)", file=sys.stderr)

    # Build snapshot
    snapshot = {
        "as_of_time": f"{as_of.isoformat()}T00:00:00Z",
        "portfolio_node_id": args.portfolio_node,
        "positions": positions,
    }

    # Summary statistics
    if args.summary:
        total_balance = sum(p["attributes"]["current_principal"] for p in positions)
        avg_coupon = sum(p["attributes"]["coupon_rate"] for p in positions) / max(len(positions), 1)
        avg_fico = sum(p["attributes"]["fico"] for p in positions) / max(len(positions), 1)
        avg_term = sum(p["attributes"]["term_months"] for p in positions) / max(len(positions), 1)

        # Group by state
        by_state: dict[str, int] = {}
        for p in positions:
            st = p["attributes"]["state"]
            by_state[st] = by_state.get(st, 0) + 1
        top_states = sorted(by_state.items(), key=lambda x: -x[1])[:10]

        # Group by asset type
        by_type: dict[str, int] = {}
        for p in positions:
            at = p["attributes"].get("asset_type", "UNKNOWN")
            by_type[at] = by_type.get(at, 0) + 1
        top_types = sorted(by_type.items(), key=lambda x: -x[1])[:10]

        # Group by platform
        by_platform: dict[str, int] = {}
        for p in positions:
            pl = p["attributes"]["platform"]
            by_platform[pl] = by_platform.get(pl, 0) + 1

        print(f"\n=== Portfolio Summary ===", file=sys.stderr)
        print(f"  Positions:     {len(positions):,}", file=sys.stderr)
        print(f"  Total Balance: ${total_balance:,.2f}", file=sys.stderr)
        print(f"  Avg Balance:   ${total_balance / max(len(positions), 1):,.2f}", file=sys.stderr)
        print(f"  Avg Coupon:    {avg_coupon * 100:.2f}%", file=sys.stderr)
        print(f"  Avg FICO:      {avg_fico:.0f}", file=sys.stderr)
        print(f"  Avg Term:      {avg_term:.0f} months", file=sys.stderr)
        print(f"\n  By Platform:", file=sys.stderr)
        for pl, cnt in sorted(by_platform.items(), key=lambda x: -x[1]):
            print(f"    {pl}: {cnt:,}", file=sys.stderr)
        print(f"\n  Top States:", file=sys.stderr)
        for st, cnt in top_states:
            print(f"    {st}: {cnt:,}", file=sys.stderr)
        print(f"\n  Top Asset Types:", file=sys.stderr)
        for at, cnt in top_types:
            print(f"    {at}: {cnt:,}", file=sys.stderr)

    # Output
    json_str = json.dumps(snapshot, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    # Optionally POST to service
    if args.post:
        try:
            import requests
        except ImportError:
            print("ERROR: 'requests' required for --post. Install with: pip install requests",
                  file=sys.stderr)
            sys.exit(1)

        print(f"\nPOSTing {len(positions)} positions to {args.post}...", file=sys.stderr)
        resp = requests.post(args.post, json=snapshot, timeout=30)
        if resp.status_code in (200, 201):
            print(f"  Success: {resp.json()}", file=sys.stderr)
        else:
            print(f"  ERROR: HTTP {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
