"""
End-to-end tests: DQR pattern → ODRL rule → validation service.

Each DQR has a synthetic pass case, a synthetic fail case, and (where applicable)
a test against the real EHDS AMR synthetic CSV data.

Service mapping:
  DQR1EH → policyChecker_3ae130f1  DQRP2 Completeness  local_patient_id not null
  DQR2EH → policyChecker_5b132606  DQRP3 Compliance    countryOfAffiliation in ISO 3166
  DQR3EH → policyChecker_842a8b01  DQRP4 Consistency   male patients have no pregnancy
  DQR4EH → policyChecker_21a1ab80  DQRP5 Completeness  dataset >= 2000 records
  DQR5EH → policyChecker_96133334  DQRP6 Fairness      gender KL-divergence < 0.05
  DQR6EH → policyChecker_32ec32b7  DQRP3 Compliance    hospital country in ISO 3166
  DQR7EH → policyChecker_05fb5861  DQRP1 Currentness   lastUpdated age <= 1440 min
  DQR1LS → policyChecker_69b7c656  DQRP1 Currentness   insertionTime age <= 30 min
"""
from __future__ import annotations

import functools
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

# ── Paths ─────────────────────────────────────────────────────
HERE      = Path(__file__).resolve().parent
CATS      = HERE.parent                                   # ComputationalCatalogues/
SERVICES  = CATS / "services"
REPO_ROOT = CATS.parent.parent                            # Fdatavalidation-1/
DATA      = REPO_ROOT / "DataProductLayer" / "DataProduct_EHDS_AMR" / "Data"


# ── Service loader (cached per service_id) ────────────────────
@functools.lru_cache(maxsize=None)
def _load(service_id: str):
    path = SERVICES / service_id / "validation_job.py"
    spec = importlib.util.spec_from_file_location(f"job_{service_id}", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(service_id: str, csv_path) -> bool:
    return _load(service_id).run_gx_validation(str(csv_path))


# ═══════════════════════════════════════════════════════════════
# DQR1EH — DQRP2 Completeness
# local_patient_id must not be null  →  policyChecker_3ae130f1
# ═══════════════════════════════════════════════════════════════
SVC_DQR1EH = "policyChecker_3ae130f1"


def test_dqr1eh_passes_complete_ids(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"local_patient_id": ["P001", "P002", "P003"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR1EH, csv) is True


def test_dqr1eh_fails_null_id(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"local_patient_id": ["P001", None, "P003"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR1EH, csv) is False


def test_dqr1eh_real_data_flags_dirty_records():
    """Synthetic data has 5 rows with null local_patient_id — service correctly fails."""
    assert validate(SVC_DQR1EH, DATA / "Patient_Summary.csv") is False


# ═══════════════════════════════════════════════════════════════
# DQR2EH — DQRP3 Compliance
# countryOfAffiliation in ISO 3166 alpha-2  →  policyChecker_5b132606
# ═══════════════════════════════════════════════════════════════
SVC_DQR2EH = "policyChecker_5b132606"


def test_dqr2eh_passes_valid_countries(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"countryOfAffiliation": ["ES", "FR", "DE", "SE"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR2EH, csv) is True


def test_dqr2eh_fails_invalid_country(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"countryOfAffiliation": ["ES", "QQ", "DE"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR2EH, csv) is False


def test_dqr2eh_real_data_flags_dirty_records():
    """Synthetic data has 10 rows with invalid/null countryOfAffiliation (XX, ZZ, 123…) — service correctly fails."""
    assert validate(SVC_DQR2EH, DATA / "Patient_Summary.csv") is False


# ═══════════════════════════════════════════════════════════════
# DQR3EH — DQRP4 Consistency
# Male patients must not have pregnancy history  →  policyChecker_842a8b01
#
# KNOWN BUG: service row_condition is 'gender == "male"' but the EHDS data
# encodes male as "M". The filter never matches "M" rows, so the expectation
# passes vacuously for any M/F dataset, even with male+pregnancy violations.
# ═══════════════════════════════════════════════════════════════
SVC_DQR3EH = "policyChecker_842a8b01"


def test_dqr3eh_passes_no_male_pregnancy(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({
        "gender":            ["M",    "F",   "F"  ],
        "pregnancyHistory":  [None,   "1",   "2"  ],
    }).to_csv(csv, index=False)
    assert validate(SVC_DQR3EH, csv) is True


@pytest.mark.xfail(
    reason=(
        "Bug: row_condition 'gender == \"male\"' never matches 'M' encoding. "
        "Male patient with pregnancy slips through undetected."
    )
)
def test_dqr3eh_fails_male_M_with_pregnancy(tmp_path):
    """Documents the encoding bug: 'M' males with pregnancy are not caught."""
    csv = tmp_path / "p.csv"
    pd.DataFrame({
        "gender":           ["M",  "F"  ],
        "pregnancyHistory": ["1",  None ],   # male has pregnancy — should fail
    }).to_csv(csv, index=False)
    assert validate(SVC_DQR3EH, csv) is False  # actually returns True due to bug


def test_dqr3eh_fails_male_str_with_pregnancy(tmp_path):
    """With 'male'/'female' encoding the filter works correctly."""
    csv = tmp_path / "p.csv"
    pd.DataFrame({
        "gender":           ["male",   "female"],
        "pregnancyHistory": ["1",      None    ],
    }).to_csv(csv, index=False)
    assert validate(SVC_DQR3EH, csv) is False


def test_dqr3eh_passes_male_str_no_pregnancy(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({
        "gender":           ["male",   "female"],
        "pregnancyHistory": [None,     "1"     ],
    }).to_csv(csv, index=False)
    assert validate(SVC_DQR3EH, csv) is True


# ═══════════════════════════════════════════════════════════════
# DQR4EH — DQRP5 Completeness
# Dataset must contain >= 2000 records  →  policyChecker_21a1ab80
#
# NOTE: real synthetic CSVs have 500 rows — documented expected failure below.
# ═══════════════════════════════════════════════════════════════
SVC_DQR4EH = "policyChecker_21a1ab80"


def test_dqr4eh_passes_large_dataset(tmp_path):
    csv = tmp_path / "isolates.csv"
    pd.DataFrame({"isolateID": [f"ISO-{i:05d}" for i in range(2000)]}).to_csv(csv, index=False)
    assert validate(SVC_DQR4EH, csv) is True


def test_dqr4eh_passes_exactly_at_threshold(tmp_path):
    csv = tmp_path / "isolates.csv"
    pd.DataFrame({"isolateID": [f"ISO-{i:05d}" for i in range(2000)]}).to_csv(csv, index=False)
    assert validate(SVC_DQR4EH, csv) is True


def test_dqr4eh_fails_small_dataset(tmp_path):
    csv = tmp_path / "isolates.csv"
    pd.DataFrame({"isolateID": [f"ISO-{i:05d}" for i in range(499)]}).to_csv(csv, index=False)
    assert validate(SVC_DQR4EH, csv) is False


def test_dqr4eh_real_data_fails_synthetic_limitation():
    """Synthetic Isolate.csv has 500 rows; real AMR study needs >= 2000."""
    assert validate(SVC_DQR4EH, DATA / "Isolate.csv") is False


# ═══════════════════════════════════════════════════════════════
# DQR5EH — DQRP6 Fairness
# Gender distribution imbalance <= 5% (KL divergence < 0.05 vs 50/50)
# policyChecker_96133334
# ═══════════════════════════════════════════════════════════════
SVC_DQR5EH = "policyChecker_96133334"


def test_dqr5eh_passes_balanced_gender(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"gender": ["M"] * 500 + ["F"] * 500}).to_csv(csv, index=False)
    assert validate(SVC_DQR5EH, csv) is True


def test_dqr5eh_fails_heavily_imbalanced_gender(tmp_path):
    csv = tmp_path / "p.csv"
    # 90/10 split → KL divergence ≈ 0.37 >> 0.05
    pd.DataFrame({"gender": ["M"] * 900 + ["F"] * 100}).to_csv(csv, index=False)
    assert validate(SVC_DQR5EH, csv) is False


def test_dqr5eh_real_data(tmp_path):
    """Real data should have roughly balanced gender; result documents actual distribution."""
    result = validate(SVC_DQR5EH, DATA / "Patient_Summary.csv")
    # Not asserting a specific value — just ensures the service runs without error.
    assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════
# DQR6EH — DQRP3 Compliance
# Hospital country in ISO 3166 alpha-2  →  policyChecker_32ec32b7
# ═══════════════════════════════════════════════════════════════
SVC_DQR6EH = "policyChecker_32ec32b7"


def test_dqr6eh_passes_valid_hospital_countries(tmp_path):
    csv = tmp_path / "h.csv"
    pd.DataFrame({"country": ["ES", "FR", "DE", "PT", "IT"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR6EH, csv) is True


def test_dqr6eh_fails_invalid_hospital_country(tmp_path):
    csv = tmp_path / "h.csv"
    pd.DataFrame({"country": ["ES", "QQ", "DE"]}).to_csv(csv, index=False)
    assert validate(SVC_DQR6EH, csv) is False


def test_dqr6eh_real_data_passes():
    assert validate(SVC_DQR6EH, DATA / "Hospital.csv") is True


# ═══════════════════════════════════════════════════════════════
# DQR7EH — DQRP1 Currentness
# lastUpdated age <= 1440 min (24 h)  →  policyChecker_05fb5861
#
# NOTE: real synthetic data has 2024–2025 timestamps → all stale.
# ═══════════════════════════════════════════════════════════════
SVC_DQR7EH = "policyChecker_05fb5861"


def test_dqr7eh_passes_fresh_timestamps(tmp_path):
    csv = tmp_path / "p.csv"
    now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    pd.DataFrame({"lastUpdated": [now, now, now]}).to_csv(csv, index=False)
    assert validate(SVC_DQR7EH, csv) is True


def test_dqr7eh_fails_stale_timestamps(tmp_path):
    csv = tmp_path / "p.csv"
    pd.DataFrame({"lastUpdated": [
        "2020-01-01T00:00:00Z",
        "2019-06-15T12:00:00Z",
    ]}).to_csv(csv, index=False)
    assert validate(SVC_DQR7EH, csv) is False


def test_dqr7eh_real_data_fails_stale():
    """Synthetic data timestamps are from 2024-2025 — all exceed the 1440-min threshold."""
    assert validate(SVC_DQR7EH, DATA / "Patient_Summary.csv") is False


# ═══════════════════════════════════════════════════════════════
# DQR1LS — DQRP1 Currentness (Live Stocks use case)
# insertionTime age <= 30 min  →  policyChecker_69b7c656
#
# No real Live Stocks data file exists; synthetic fixtures only.
# ═══════════════════════════════════════════════════════════════
SVC_DQR1LS = "policyChecker_69b7c656"


def test_dqr1ls_passes_fresh_prices(tmp_path):
    csv = tmp_path / "prices.csv"
    now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    pd.DataFrame({"insertionTime": [now, now, now]}).to_csv(csv, index=False)
    assert validate(SVC_DQR1LS, csv) is True


def test_dqr1ls_fails_stale_prices(tmp_path):
    csv = tmp_path / "prices.csv"
    pd.DataFrame({"insertionTime": [
        "2020-01-01T00:00:00Z",
        "2019-06-15T12:00:00Z",
    ]}).to_csv(csv, index=False)
    assert validate(SVC_DQR1LS, csv) is False
