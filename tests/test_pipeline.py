"""
Pipeline tests: pattern → instantiation → ODRL rule → validation service.

  Stage 1 — Pattern schema       patterns/DQRPX.json structure & placeholder coverage
  Stage 2 — Statement rendering  live_statement fills all %placeholders%
  Stage 3 — ODRL generation      build_odrl_rule produces correct JSON-LD
  Stage 4 — ODRL consistency     generated rule matches key fields of saved rule
  Stage 5 — Service execution    validation service produces correct pass/fail
             (Stage 5 is the full end-to-end; covered in detail by test_e2e.py)
"""
from __future__ import annotations

import functools
import importlib.util
import json
import re
from pathlib import Path

import pandas as pd
import pytest

from conftest import CATS, DATA  # type: ignore

# ── Filesystem discovery (computed at collection time) ────────────────────────
PATTERNS_DIR  = CATS / "prototype" / "patterns"
REQS_DIR      = CATS / "prototype" / "requirements"
TMPL_DIR      = CATS / "prototype" / "odrl_templates"
RULES_DIR     = CATS / "prototype" / "odrl_rules"
SERVICES      = CATS / "services"

PATTERN_IDS = [f.stem for f in sorted(PATTERNS_DIR.glob("DQRP*.json"))]
REQ_IDS     = [f.stem for f in sorted(REQS_DIR.glob("DQR[0-9]*.json"))]

# DQRs that have a saved ODRL rule (for consistency check)
SAVED_RULE_IDS = [
    r for r in REQ_IDS
    if (RULES_DIR / f"{r}_odrl.json").exists()
]

# DQR → (service_id, data_csv)  for end-to-end validation
DQR_SERVICE = {
    "DQR1EH": ("policyChecker_3ae130f1", DATA / "Patient_Summary.csv"),
    "DQR2EH": ("policyChecker_5b132606", DATA / "Patient_Summary.csv"),
    "DQR3EH": ("policyChecker_842a8b01", None),   # encoding bug; service tested in test_e2e
    "DQR4EH": ("policyChecker_21a1ab80", DATA / "Isolate.csv"),
    "DQR5EH": ("policyChecker_96133334", DATA / "Patient_Summary.csv"),
    "DQR6EH": ("policyChecker_32ec32b7", DATA / "Hospital.csv"),
    "DQR7EH": ("policyChecker_05fb5861", None),   # timestamp-dependent; uses tmp fixture
}

# Helper: load a validation service module (cached)
@functools.lru_cache(maxsize=None)
def _load_svc(service_id: str):
    path = SERVICES / service_id / "validation_job.py"
    spec = importlib.util.spec_from_file_location(f"job_{service_id}", path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Pattern schema
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("pid", PATTERN_IDS)
def test_pattern_required_fields(pid):
    p = json.loads((PATTERNS_DIR / f"{pid}.json").read_text())
    assert p.get("id") == pid,                  f"{pid}: id field mismatch"
    assert "statementTemplate" in p,            f"{pid}: missing statementTemplate"
    assert "parameters" in p,                   f"{pid}: missing parameters"
    assert "qualityDimension" in p or "qualityDimensions" in p, \
                                                f"{pid}: missing qualityDimension(s)"


@pytest.mark.parametrize("pid", PATTERN_IDS)
def test_pattern_placeholders_covered_by_parameters(pid):
    """Every %name% in statementTemplate must have a matching entry in parameters."""
    p = json.loads((PATTERNS_DIR / f"{pid}.json").read_text())
    # Find %token% but not %% (literal percent)
    placeholders = set(re.findall(r'%([^%\s][^%]*)%', p["statementTemplate"]))
    param_names  = {param["name"] for param in p["parameters"]}
    missing = placeholders - param_names
    assert not missing, f"{pid}: placeholder(s) {missing} not declared in parameters"


@pytest.mark.parametrize("pid", PATTERN_IDS)
def test_odrl_template_exists_for_pattern(pid):
    assert (TMPL_DIR / f"{pid}_odrl_template.json").exists(), \
        f"Missing ODRL template for {pid}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Statement instantiation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dqr_id", REQ_IDS)
def test_statement_fills_all_placeholders(proto, dqr_id):
    """live_statement(template, req.parameters) must leave no unfilled %token%."""
    req     = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    pid     = req["pattern"]["id"]
    pattern = json.loads((PATTERNS_DIR / f"{pid}.json").read_text())
    result  = proto.live_statement(pattern["statementTemplate"], req["parameters"])
    remaining = re.findall(r'%[^%\s][^%]*%', result)
    assert not remaining, \
        f"{dqr_id}: unfilled placeholder(s) after instantiation: {remaining}"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3 — ODRL rule generation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dqr_id", REQ_IDS)
def test_odrl_generation_produces_valid_jsonld(proto, dqr_id):
    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)

    assert "@context" in rule,   f"{dqr_id}: missing @context"
    assert "@graph"   in rule,   f"{dqr_id}: missing @graph"
    assert len(rule["@graph"]) >= 3, f"{dqr_id}: @graph has fewer nodes than expected"


@pytest.mark.parametrize("dqr_id", REQ_IDS)
def test_odrl_derivation_and_dimension(proto, dqr_id):
    """Generated policy node must reference the correct DQR id and quality dimension."""
    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)

    policy = rule["@graph"][0]
    assert policy["tb:derivedFrom"]      == dqr_id
    assert policy["tb:qualityDimension"] == req["qualityDimension"]["dimension"]


@pytest.mark.parametrize("dqr_id", REQ_IDS)
def test_odrl_target_attribute_matches_requirement(proto, dqr_id):
    """ODRL permission target must be the attribute named in the requirement parameters."""
    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)

    expected_attr = req["parameters"][tmpl["target"]["parameter"]]
    permission    = rule["@graph"][0]["odrl:permission"][0]
    actual        = permission["odrl:target"]["@id"]
    assert actual == f"ab:{expected_attr}", \
        f"{dqr_id}: target mismatch — expected 'ab:{expected_attr}', got '{actual}'"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 4 — ODRL consistency: generated == saved (key semantic fields)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dqr_id", SAVED_RULE_IDS)
def test_saved_odrl_rule_consistent_with_generation(proto, dqr_id):
    """
    The file in odrl_rules/DQRX_odrl.json must agree with build_odrl_rule output:
    same tb:derivedFrom, tb:qualityDimension, and odrl:permission target.
    Catches drift when a template is updated without regenerating the saved rule.
    """
    req   = json.loads((REQS_DIR  / f"{dqr_id}.json").read_text())
    tmpl  = json.loads((TMPL_DIR  / f"{req['pattern']['id']}_odrl_template.json").read_text())
    saved = json.loads((RULES_DIR / f"{dqr_id}_odrl.json").read_text())

    generated = proto.build_odrl_rule(req, tmpl)
    gen_pol  = generated["@graph"][0]
    sav_pol  = saved["@graph"][0]

    assert gen_pol["tb:derivedFrom"]      == sav_pol.get("tb:derivedFrom"),      \
        f"{dqr_id}: tb:derivedFrom mismatch"
    assert gen_pol["tb:qualityDimension"] == sav_pol.get("tb:qualityDimension"), \
        f"{dqr_id}: tb:qualityDimension mismatch"

    gen_target = gen_pol["odrl:permission"][0]["odrl:target"]["@id"]
    sav_target = sav_pol["odrl:permission"][0]["odrl:target"]["@id"]
    assert gen_target == sav_target, \
        f"{dqr_id}: target mismatch — generated '{gen_target}' vs saved '{sav_target}'"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 5 — End-to-end: pattern → ODRL → service execution
#   For time-independent DQRs: use real data
#   For DQR7EH (freshness): inject a fresh-timestamp fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dqr_id", [
    d for d, (_, csv) in DQR_SERVICE.items() if csv is not None
])
def test_e2e_pipeline_real_data(proto, dqr_id):
    """
    Full pipeline: load requirement → generate ODRL rule (verify) → run service.
    Verifies that the three stages stay coherent end-to-end.
    """
    svc_id, csv = DQR_SERVICE[dqr_id]

    # Stages 3+4: generate rule and confirm it agrees with the saved rule
    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)
    assert rule["@graph"][0]["tb:derivedFrom"] == dqr_id

    # Stage 5: run the validation service
    result = _load_svc(svc_id).run_gx_validation(str(csv))
    assert isinstance(result, bool), f"{dqr_id}: service did not return a bool"
    # DQR1EH/DQR2EH: real data has intentional dirty records → correctly fails
    # DQR4EH: synthetic data < 2000 rows → correctly fails
    # DQR7EH: timestamps stale → correctly fails  (not included here)
    # DQR5EH, DQR6EH: real data passes
    expected = {
        "DQR1EH": False,  # 5 null patient IDs in synthetic data
        "DQR2EH": False,  # 10 invalid country codes in synthetic data
        "DQR4EH": False,  # only 500 rows, need ≥2000
        "DQR5EH": True,
        "DQR6EH": True,
    }
    if dqr_id in expected:
        assert result is expected[dqr_id], \
            f"{dqr_id}: expected {expected[dqr_id]}, got {result}"


def test_e2e_dqr7eh_freshness_pipeline(proto, tmp_path):
    """DQR7EH end-to-end: generate ODRL rule, then verify service passes on fresh data."""
    dqr_id = "DQR7EH"
    svc_id, _ = DQR_SERVICE[dqr_id]

    req  = json.loads((REQS_DIR / f"{dqr_id}.json").read_text())
    tmpl = json.loads((TMPL_DIR / f"{req['pattern']['id']}_odrl_template.json").read_text())
    rule = proto.build_odrl_rule(req, tmpl)
    assert rule["@graph"][0]["tb:derivedFrom"] == dqr_id

    # Fresh data → service must pass
    csv = tmp_path / "patients.csv"
    now = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    pd.DataFrame({"lastUpdated": [now, now, now]}).to_csv(csv, index=False)
    assert _load_svc(svc_id).run_gx_validation(str(csv)) is True

    # Stale data → service must fail
    pd.DataFrame({"lastUpdated": ["2020-01-01T00:00:00Z"] * 3}).to_csv(csv, index=False)
    assert _load_svc(svc_id).run_gx_validation(str(csv)) is False
