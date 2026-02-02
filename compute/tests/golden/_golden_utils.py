# compute/tests/golden/_golden_utils.py
from __future__ import annotations
import json
from pathlib import Path

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def assert_close(actual: float, expected: float, tol: float, name: str):
    if abs(actual - expected) > tol:
        raise AssertionError(f"{name} actual={actual} expected={expected} tol={tol}")
