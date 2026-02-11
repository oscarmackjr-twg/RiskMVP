"""Expected Loss (EL) calculation.

EL = PD * LGD * EAD
UL = EAD * LGD * sqrt(PD * (1 - PD))
"""
from __future__ import annotations
import math


def calculate_expected_loss(pd: float, lgd: float, ead: float) -> float:
    """Calculate expected loss.

    Args:
        pd: Probability of default (0-1, decimal).
        lgd: Loss given default (0-1, decimal).
        ead: Exposure at default (monetary amount).

    Returns:
        Expected loss amount in dollars.

    Raises:
        ValueError: If parameters out of valid range.

    Example:
        >>> el = calculate_expected_loss(0.02, 0.40, 100000)
        >>> print(f"Expected loss: ${el:.2f}")
        Expected loss: $800.00
    """
    # Validate inputs
    if not (0 <= pd <= 1):
        raise ValueError(f"PD must be between 0 and 1, got {pd}")
    if not (0 <= lgd <= 1):
        raise ValueError(f"LGD must be between 0 and 1, got {lgd}")
    if ead < 0:
        raise ValueError(f"EAD must be non-negative, got {ead}")

    return pd * lgd * ead


def calculate_unexpected_loss(pd: float, lgd: float, ead: float) -> float:
    """Calculate unexpected loss (volatility of credit loss distribution).

    Formula: UL = EAD × LGD × sqrt(PD × (1 - PD))

    Used for economic capital calculation.

    Args:
        pd: Probability of default (0-1, decimal).
        lgd: Loss given default (0-1, decimal).
        ead: Exposure at default (monetary amount).

    Returns:
        Unexpected loss amount in dollars.

    Raises:
        ValueError: If parameters out of valid range.
    """
    # Validate inputs
    if not (0 <= pd <= 1):
        raise ValueError(f"PD must be between 0 and 1, got {pd}")
    if not (0 <= lgd <= 1):
        raise ValueError(f"LGD must be between 0 and 1, got {lgd}")
    if ead < 0:
        raise ValueError(f"EAD must be non-negative, got {ead}")

    return ead * lgd * math.sqrt(pd * (1 - pd))


# Legacy alias for backward compatibility
def expected_loss(pd: float, lgd: float, ead: float) -> float:
    """Calculate expected loss (legacy function name).

    Args:
        pd: Probability of default (0-1).
        lgd: Loss given default (0-1).
        ead: Exposure at default (monetary amount).

    Returns:
        Expected loss amount.
    """
    return calculate_expected_loss(pd, lgd, ead)
