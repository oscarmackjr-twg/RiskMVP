# compute/tests/golden/test_loan_golden.py
from pathlib import Path
from compute.pricers.loan import price_loan
from ._golden_utils import load_json, assert_close

BASE = Path(__file__).parent
INPUTS = BASE / "inputs"
EXPECTED = BASE / "expected"

def test_loan_case1():
    market = load_json(INPUTS / "market_snapshot_case1.json")
    case = load_json(INPUTS / "loan_case1.json")
    exp = load_json(EXPECTED / "loan_case1_expected.json")

    out = price_loan(case["position"], case["instrument"], market, exp["measures"], exp["scenario_id"])
    for k, vexp in exp["expected"].items():
        assert_close(float(out[k]), float(vexp), float(exp["tolerances"][k]), k)
