"""
Shared fixtures.

Mocks Streamlit before loading dqr_prototype2.py so the pure-Python
functions (build_odrl_rule, live_statement, load_patterns, …) are
importable without a running Streamlit server.
"""
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

HERE      = Path(__file__).resolve().parent
CATS      = HERE.parent
REPO_ROOT = CATS.parent.parent
DATA      = REPO_ROOT / "DataProductLayer" / "DataProduct_EHDS_AMR" / "Data"

# ── Mock Streamlit once per process ──────────────────────────────────────────
if "streamlit" not in sys.modules:
    _st = MagicMock()
    # @st.cache_data(ttl=N) → pass-through decorator; @st.cache_data(fn) → fn unchanged
    _st.cache_data = lambda *a, **kw: a[0] if (a and callable(a[0])) else (lambda f: f)
    sys.modules["streamlit"] = _st


# ── Prototype module (loaded once per test session) ───────────────────────────
@pytest.fixture(scope="session")
def proto():
    spec = importlib.util.spec_from_file_location(
        "_dqr_prototype2",
        CATS / "prototype" / "dqr_prototype2.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Pattern and requirement maps (session-scoped for speed) ──────────────────
@pytest.fixture(scope="session")
def patterns(proto):
    return {p["id"]: p for p in proto.load_patterns()}


@pytest.fixture(scope="session")
def requirements(proto):
    return {r["id"]: r for r in proto.load_requirements()}
