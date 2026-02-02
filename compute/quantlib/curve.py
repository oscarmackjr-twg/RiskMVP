# compute/quantlib/curve.py
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple
from compute.quantlib.tenors import tenor_to_years

@dataclass(frozen=True)
class ZeroCurve:
    """Simple zero-rate curve with linear interpolation on zero rates."""
    nodes: List[Tuple[float, float]]  # (t_years, zero_rate)

    @staticmethod
    def from_market_nodes(nodes: list[dict]) -> "ZeroCurve":
        pts = sorted([(tenor_to_years(n["tenor"]), float(n["zero_rate"])) for n in nodes], key=lambda x: x[0])
        return ZeroCurve(nodes=pts)

    def zero(self, t: float) -> float:
        pts = self.nodes
        if t <= pts[0][0]:
            return pts[0][1]
        if t >= pts[-1][0]:
            return pts[-1][1]
        for (t0, r0), (t1, r1) in zip(pts, pts[1:]):
            if t0 <= t <= t1:
                w = (t - t0) / (t1 - t0)
                return r0 + w * (r1 - r0)
        return pts[-1][1]

    def df(self, t: float) -> float:
        r = self.zero(t)
        return math.exp(-r * t)

def effective_df(df_ois: float, spread: float, t: float) -> float:
    # df_eff(t) = df_ois(t) * exp(-spread(t)*t)
    return df_ois * math.exp(-spread * t)
