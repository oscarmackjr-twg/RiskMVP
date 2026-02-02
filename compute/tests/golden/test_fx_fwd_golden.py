# compute/tests/golden/test_fx_fwd_golden.py
from pathlib import Path
from compute.pricers.fx_fwd import price_fx_fwd
from ._golden_utils import load_json, assert_close

BASE = Path(__file__).parent
INPUTS = BASE / "inputs"
EXPECTED = BASE / "expected"

def test_fx_fwd_case1():
    market = load_json(INPUTS / "market_snapshot_case1.json")
    case = load_json(INPUTS / "fx_fwd_case1.json")
    exp = load_json(EXPECTED / "fx_fwd_case1_expected.json")

    out = price_fx_fwd(
        case["position"], case["instrument"], market,
        measures=exp["measures"], scenario_id=exp["scenario_id"]
    )

    for k, vexp in exp["expected"].items():
        assert_close(float(out[k]), float(vexp), float(exp["tolerances"][k]), k)
