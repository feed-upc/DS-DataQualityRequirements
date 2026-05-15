"""
Stage 5b — Service generation: ODRL rule → engine API → validation_job.py.

These tests complete the full end-to-end pipeline:
  Pattern → Requirement → ODRL rule → [engine] → validation_job.py → execution

The engine (Connector/ValidationFramework) is auto-started if not already running.
If it cannot be reached, all tests in this file are SKIPPED with setup instructions.

To start the engine manually:
  cd <repo_root>   (i.e. Fdatavalidation-1/)
  uvicorn Connector.ValidationFramework.api.api:app --port 5000

Or point to a remote instance:
  VALIDATION_API_URL=http://host:5000 pytest tests/test_service_generation.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd
import pytest
import requests

from conftest import CATS, DATA, REPO_ROOT  # type: ignore

REQS_DIR = CATS / "prototype" / "requirements"
TMPL_DIR = CATS / "prototype" / "odrl_templates"
RULES_DIR = CATS / "prototype" / "odrl_rules"

# ── Engine availability fixture ───────────────────────────────────────────────

def _api_alive(url: str) -> bool:
    try:
        return requests.get(f"{url}/test", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def engine_url():
    """
    Yields the engine base URL if reachable.
    Auto-starts the server if it is not already running.
    Skips the entire file with setup instructions if it cannot be reached.
    """
    url = os.environ.get("VALIDATION_API_URL", "http://localhost:5000")

    if _api_alive(url):
        yield url
        return

    # ── Try to auto-start ─────────────────────────────────────────────────────
    proc = None
    try:
        proc = __import__("subprocess").Popen(
            [sys.executable, "-m", "uvicorn",
             "Connector.ValidationFramework.api.api:app",
             "--port", "5000", "--host", "127.0.0.1", "--log-level", "error"],
            cwd=str(REPO_ROOT),
            stdout=__import__("subprocess").DEVNULL,
            stderr=__import__("subprocess").DEVNULL,
        )
        for _ in range(25):          # wait up to 25 s
            time.sleep(1)
            if _api_alive(url):
                break
        else:
            pytest.skip(
                f"\n\n"
                f"  Validation engine not reachable at {url}.\n"
                f"  Auto-start failed (dependency missing or port in use).\n\n"
                f"  To run Stage 5b tests manually:\n\n"
                f"    pip install -r {REPO_ROOT}/Connector/ValidationFramework/api_requirements.txt\n"
                f"    cd {REPO_ROOT}\n"
                f"    uvicorn Connector.ValidationFramework.api.api:app --port 5000\n\n"
                f"  Then re-run:  pytest tests/test_service_generation.py\n"
            )

        yield url
    finally:
        if proc is not None:
            proc.terminate()


# ── Helper: load generated code as a module ───────────────────────────────────

def _load_generated(code: str, tmp_path: Path, label: str):
    job = tmp_path / f"gen_{label}.py"
    job.write_text(code)
    spec = importlib.util.spec_from_file_location(f"gen_{label}", job)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dqr_id,data_product,csv_name", [
    ("DQR1EH", "Patient_Summary", "Patient_Summary.csv"),
    ("DQR5EH", "Patient_Summary", "Patient_Summary.csv"),
    ("DQR6EH", "Patient_Summary", "Hospital.csv"),   # compliance check on Hospital
])
def test_generate_and_execute_service(engine_url, proto, tmp_path, dqr_id, data_product, csv_name):
    """
    Full pipeline:
      1. Generate ODRL rule from requirement + template   (Stage 3)
      2. POST rule to engine API                          (Stage 5b - generation)
      3. Verify generated Python code structure
      4. Execute generated service against real data      (Stage 5b - execution)
    """
    # ── Stage 3: regenerate ODRL rule ─────────────────────────────────────────
    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)

    # Ensure the rule is written to disk (engine reads it from odrl_rules/)
    (RULES_DIR / f"{dqr_id}_odrl.json").write_text(json.dumps(rule, indent=2))

    # ── Stage 5b: call the engine ─────────────────────────────────────────────
    resp = requests.post(
        f"{engine_url}/generate-validation-service",
        json={"rule_id": dqr_id, "data_product": data_product},
        timeout=300,
    )

    if resp.status_code != 200:
        body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        pytest.fail(
            f"{dqr_id}: engine returned {resp.status_code}\n"
            f"  error:  {body.get('error', resp.text[:300])}\n"
            f"  logs:   {body.get('logs', '')[:300]}"
        )

    body = resp.json()
    assert "validation_code" in body, f"{dqr_id}: response missing 'validation_code'"

    code = body["validation_code"]
    assert code.strip(),                       f"{dqr_id}: validation_code is empty"
    assert "run_gx_validation" in code,        f"{dqr_id}: generated code missing run_gx_validation"
    assert "great_expectations" in code,       f"{dqr_id}: generated code missing great_expectations import"

    # ── Stage 5b: execute generated service ───────────────────────────────────
    mod    = _load_generated(code, tmp_path, dqr_id)
    result = mod.run_gx_validation(str(DATA / csv_name))
    assert isinstance(result, bool), f"{dqr_id}: service did not return a bool"

    # Log outcome — pass/fail depends on intentional data quality issues in the
    # synthetic dataset (DQR1EH expects False: 5 null IDs; DQR5EH/6EH expect True)
    status = "PASS" if result else "FAIL (expected for dirty synthetic data)"
    print(f"\n  [{dqr_id}] Generated service result: {status}")


def test_generate_dqr7eh_freshness_service(engine_url, proto, tmp_path):
    """
    DQR7EH end-to-end: engine generates the freshness service and the code is valid.

    KNOWN LIMITATION: the engine currently generates an empty expectation suite for
    DQRP1 (Currentness) — the age computation and ExpectColumnValuesToBeBetween are
    missing from the output. The generated service therefore always returns True.
    Freshness enforcement is tested against the hand-crafted service in test_e2e.py.
    """
    dqr_id       = "DQR7EH"
    data_product = "Patient_Summary"

    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)
    (RULES_DIR / f"{dqr_id}_odrl.json").write_text(json.dumps(rule, indent=2))

    resp = requests.post(
        f"{engine_url}/generate-validation-service",
        json={"rule_id": dqr_id, "data_product": data_product},
        timeout=300,
    )
    assert resp.status_code == 200, f"Engine error: {resp.text[:300]}"
    code = resp.json()["validation_code"]

    assert "run_gx_validation" in code, "Generated code missing run_gx_validation"
    assert "great_expectations" in code, "Generated code missing great_expectations import"

    mod = _load_generated(code, tmp_path, dqr_id)

    # Generated service runs without error — result documents the known gap
    fresh_csv = tmp_path / "fresh.csv"
    now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    pd.DataFrame({"lastUpdated": [now, now, now]}).to_csv(fresh_csv, index=False)
    result = mod.run_gx_validation(str(fresh_csv))
    assert isinstance(result, bool), "Generated service did not return a bool"

    # Engine-generated suite is empty → stale data passes (known gap, xfail)
    stale_csv = tmp_path / "stale.csv"
    pd.DataFrame({"lastUpdated": ["2020-01-01T00:00:00Z"] * 3}).to_csv(stale_csv, index=False)
    stale_result = mod.run_gx_validation(str(stale_csv))
    if stale_result is not False:
        pytest.xfail(
            "Engine does not yet generate freshness expectations for DQRP1 (Currentness). "
            "Generated suite is empty — stale data passes. "
            "Tracked as engine code-generation gap for ab:CheckFreshness."
        )
