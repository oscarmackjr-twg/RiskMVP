"""Unexpected Loss (UL) calculation."""
from __future__ import annotations

import math


def unexpected_loss(pd: float, lgd: float, ead: float, lgd_vol: float = 0.0) -> float:
    """Calculate single-name unexpected loss.

    UL = EAD * sqrt(PD * LGD_vol^2 + LGD^2 * PD * (1-PD))

    Simplified: UL = EAD * LGD * sqrt(PD * (1 - PD))  when LGD_vol = 0
    """
    if lgd_vol > 0:
        return ead * math.sqrt(pd * lgd_vol**2 + lgd**2 * pd * (1 - pd))
    return ead * lgd * math.sqrt(pd * (1 - pd))
