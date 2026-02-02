# compute/tests/golden/test_bond_golden.py
from pathlib import Path
from compute.pricers.bond import price_bond
from ._golden_utils import load_json, assert_close

BASE = Path(__file__).parent
INPUTS = BASE / "inputs"
EXPECTED = BASE / "expected"

def test_bond_case1():
    market = load_json(INPUTS / "market_snapshot_case1.json")
    case = load_json(INPUTS / "bond_case1.json")
    exp = load_json(EXPECTED / "bond_case1_expected.json")

    out = price_bond(case["position"], case["instrument"], market, exp["measures"], exp["scenario_id"])
    for k, vexp in exp["expected"].items():
        assert_close(float(out[k]), float(vexp), float(exp["tolerances"][k]), k)
