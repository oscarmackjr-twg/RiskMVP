"""Total return calculation: total, income, price, and currency components."""
from __future__ import annotations

from typing import Dict


def total_return(begin_mv: float, end_mv: float, income: float, costs: float = 0.0) -> float:
    """Calculate total return for a period.

    TR = (End MV + Income - Costs - Begin MV) / Begin MV
    """
    if begin_mv == 0:
        raise ValueError("Beginning market value cannot be zero")
    return (end_mv + income - costs - begin_mv) / begin_mv


def decompose_return(
    total: float,
    income_return: float,
    currency_return: float = 0.0,
) -> Dict[str, float]:
    """Decompose total return into components.

    Price Return = Total - Income - Currency
    """
    price_return = total - income_return - currency_return
    return {
        "total_return": total,
        "income_return": income_return,
        "price_return": price_return,
        "currency_return": currency_return,
    }
