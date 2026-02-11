"""Test registry pattern integration in worker.

Validates that:
1. All expected pricers are registered
2. Unknown product types raise descriptive errors
3. Registry bootstrap works on import
"""
from compute.pricers.registry import registered_types, get_pricer
import pytest


def test_all_pricers_registered():
    """Verify all 3 existing pricers are registered in registry."""
    types = registered_types()
    assert "FX_FWD" in types, "FX_FWD pricer not registered"
    assert "AMORT_LOAN" in types, "AMORT_LOAN pricer not registered"
    assert "FIXED_BOND" in types, "FIXED_BOND pricer not registered"
    assert len(types) == 3, f"Expected 3 pricers, got {len(types)}: {types}"


def test_unknown_product_type_raises():
    """Verify get_pricer raises ValueError for unregistered product types."""
    with pytest.raises(ValueError, match="No pricer registered"):
        get_pricer("UNKNOWN_TYPE")


def test_registry_bootstrap_on_import():
    """Verify registry bootstrap ran automatically on module import."""
    # If this test runs, bootstrap already happened (registry.py imports and calls _bootstrap())
    # Verify we have the expected pricers registered
    types = registered_types()
    assert len(types) > 0, "Registry is empty - bootstrap may have failed"
    assert "FX_FWD" in types, "Bootstrap didn't register FX_FWD"


def test_get_pricer_returns_callable():
    """Verify get_pricer returns callable pricer functions."""
    pricer = get_pricer("FX_FWD")
    assert callable(pricer), "get_pricer should return a callable"

    pricer = get_pricer("AMORT_LOAN")
    assert callable(pricer), "get_pricer should return a callable"

    pricer = get_pricer("FIXED_BOND")
    assert callable(pricer), "get_pricer should return a callable"
