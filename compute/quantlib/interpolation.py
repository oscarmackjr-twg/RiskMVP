"""Interpolation methods for curve construction.

Defines interpolation method constants used with QuantLib curve bootstrapping.
QuantLib handles actual interpolation internally; this module provides
standardized method identifiers and documentation.
"""
from __future__ import annotations

from enum import Enum


class InterpolationMethod(str, Enum):
    """Interpolation methods for yield curve construction.

    These correspond to QuantLib's interpolation schemes used in
    PiecewiseYieldCurve constructors.
    """

    # LogCubic - Log-cubic interpolation on discount factors
    # Best for: Discount curves (maintains positivity, smooth forward rates)
    # QuantLib: PiecewiseLogCubicDiscount
    LOG_CUBIC = "LOG_CUBIC"

    # Linear - Linear interpolation on zero rates
    # Best for: Simple curves, debugging, when smoothness not critical
    # QuantLib: PiecewiseLinearZero
    LINEAR = "LINEAR"

    # Cubic Spline - Natural cubic spline on zero rates
    # Best for: Smooth zero rate curves
    # QuantLib: PiecewiseCubicZero
    CUBIC_SPLINE = "CUBIC_SPLINE"

    # LogLinear - Linear interpolation on log of discount factors
    # Best for: Forward curves, simple discount interpolation
    # QuantLib: PiecewiseLogLinearDiscount
    LOGLINEAR = "LOGLINEAR"

    # Monotone Convex (Hagan-West)
    # Best for: Preventing negative forward rates, structured products
    # Note: Not directly available in standard QuantLib PiecewiseYieldCurve
    MONOTONE_CONVEX = "MONOTONE_CONVEX"


def get_interpolation_name(method: InterpolationMethod | str) -> str:
    """Get human-readable name for an interpolation method.

    Args:
        method: InterpolationMethod enum or string.

    Returns:
        Descriptive name of the interpolation method.

    Example:
        >>> name = get_interpolation_name(InterpolationMethod.LOG_CUBIC)
        >>> print(name)  # "Log-Cubic on Discount Factors"
    """
    if isinstance(method, str):
        method = InterpolationMethod(method)

    _NAMES = {
        InterpolationMethod.LOG_CUBIC: "Log-Cubic on Discount Factors",
        InterpolationMethod.LINEAR: "Linear on Zero Rates",
        InterpolationMethod.CUBIC_SPLINE: "Cubic Spline on Zero Rates",
        InterpolationMethod.LOGLINEAR: "Log-Linear on Discount Factors",
        InterpolationMethod.MONOTONE_CONVEX: "Monotone Convex (Hagan-West)",
    }

    return _NAMES.get(method, str(method))


def get_interpolation_description(method: InterpolationMethod | str) -> str:
    """Get detailed description of when to use an interpolation method.

    Args:
        method: InterpolationMethod enum or string.

    Returns:
        Description of appropriate use cases.

    Example:
        >>> desc = get_interpolation_description(InterpolationMethod.LOG_CUBIC)
        >>> print(desc)
    """
    if isinstance(method, str):
        method = InterpolationMethod(method)

    _DESCRIPTIONS = {
        InterpolationMethod.LOG_CUBIC:
            "Standard choice for discount curves. Interpolates log of discount "
            "factors using cubic splines, ensuring positive discount factors and "
            "smooth forward rates. Recommended for institutional-grade pricing.",

        InterpolationMethod.LINEAR:
            "Simple linear interpolation on zero rates. Fast and stable but produces "
            "discontinuous forward rates. Use for debugging or when curve smoothness "
            "is not critical.",

        InterpolationMethod.CUBIC_SPLINE:
            "Natural cubic spline on zero rates. Produces smooth zero rate curves but "
            "may result in slightly non-monotonic discount factors. Good for visualization.",

        InterpolationMethod.LOGLINEAR:
            "Linear interpolation on log of discount factors. Simpler than log-cubic, "
            "ensures positive discount factors but forward rates are piecewise constant. "
            "Suitable for simple OIS curves.",

        InterpolationMethod.MONOTONE_CONVEX:
            "Advanced method preventing negative forward rates. Essential for long-dated "
            "structured products and callable bonds. Requires custom implementation in "
            "QuantLib (not in standard PiecewiseYieldCurve).",
    }

    return _DESCRIPTIONS.get(method, "No description available.")


# Default method for different curve types
DEFAULT_DISCOUNT_INTERPOLATION = InterpolationMethod.LOG_CUBIC
DEFAULT_FORWARD_INTERPOLATION = InterpolationMethod.LOG_CUBIC
DEFAULT_ZERO_INTERPOLATION = InterpolationMethod.LINEAR
