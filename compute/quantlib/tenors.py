# compute/quantlib/tenors.py
TENOR_YEARS = {
    "1W": 1/52,
    "1M": 1/12,
    "3M": 3/12,
    "6M": 6/12,
    "9M": 9/12,
    "1Y": 1.0,
    "2Y": 2.0,
    "3Y": 3.0,
    "5Y": 5.0,
    "7Y": 7.0,
    "10Y": 10.0,
    "20Y": 20.0,
    "30Y": 30.0,
}

def tenor_to_years(tenor: str) -> float:
    if tenor not in TENOR_YEARS:
        raise ValueError(f"Unsupported tenor: {tenor}")
    return float(TENOR_YEARS[tenor])
