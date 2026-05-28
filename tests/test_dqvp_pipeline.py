"""
DQVP pipeline tests: DQR requirement → build_dqvp_turtle → plan_dqvp → plan graph.

  Stage 1 — Turtle generation  build_dqvp_turtle produces parseable DQVP Turtle
  Stage 2 — Plan generation    plan_dqvp produces a Graph with tbox:Operation nodes
                                (requires EYE reasoner; skipped if not available)
  Stage 3 — End-to-end         full pipeline for all 7 EHDS DQRs

Run all:
    pytest tests/test_dqvp_pipeline.py -v

Run without EYE (Stages 1 only):
    pytest tests/test_dqvp_pipeline.py -v -m "not requires_eye"
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, RDF, URIRef

from conftest import CATS, DATA, REPO_ROOT  # type: ignore

# ── Paths ──────────────────────────────────────────────────────────────────────
REQS_DIR   = CATS / "prototype" / "requirements"
TMPL_DIR   = CATS / "prototype" / "odrl_templates"
PLANNER_PY = CATS / "tools" / "validation-engine" / "planner" / "planner.py"
SDM_TTL    = REPO_ROOT / "FederatedComputationalGovernance" / "SemanticDataModel" / "sdm.ttl"

# DQRs that have a DQVP mapping (all 7 EHDS DQRs)
DQR_IDS = ["DQR1EH", "DQR2EH", "DQR3EH", "DQR4EH", "DQR5EH", "DQR6EH", "DQR7EH"]

# Map DQR → expected DQVP leftOperand term
DQR_LEFT_OPERAND = {
    "DQR1EH": "NonNullRate",
    "DQR2EH": "ReferenceConformance",
    "DQR3EH": "RowComparisonRate",
    "DQR4EH": "RowCount",
    "DQR5EH": "DistributionDeviation",
    "DQR6EH": "ReferenceConformance",
    "DQR7EH": "Freshness",
}

# Map DQR → expected abstract operation (for plan graph assertions)
DQR_EXPECTED_ABSTRACT = {
    "DQR1EH": "CheckCompleteness",
    "DQR2EH": "CheckValidity",
    "DQR3EH": "CheckConsistency",
    "DQR4EH": "CheckVolume",
    "DQR5EH": "CheckFairness",
    "DQR6EH": "CheckValidity",
    "DQR7EH": "CheckFreshness",
}

DQVP = Namespace("https://w3id.org/odrl/profile/dataquality#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
TB   = Namespace("http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/tbox#")
AB   = Namespace("http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/abox#")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def planner():
    """Load SemanticN3Planner from the validation-engine submodule."""
    sys.path.insert(0, str(PLANNER_PY.parent))
    spec = importlib.util.spec_from_file_location("planner", PLANNER_PY)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SemanticN3Planner(str(SDM_TTL))


@pytest.fixture(scope="session")
def eye_available():
    return shutil.which("eye") is not None


def _load_req(dqr_id: str) -> dict:
    return json.loads((REQS_DIR / f"{dqr_id}.json").read_text())


def _load_tmpl(req: dict) -> dict:
    pid = req["pattern"]["id"]
    p = TMPL_DIR / f"{pid}_odrl_template.json"
    return json.loads(p.read_text()) if p.exists() else {}


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1 — Turtle generation
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_build_dqvp_turtle_is_parseable(proto, dqr_id):
    """build_dqvp_turtle must return valid Turtle parseable by rdflib."""
    req   = _load_req(dqr_id)
    tmpl  = _load_tmpl(req)
    ttl   = proto.build_dqvp_turtle(req, tmpl)
    assert ttl.strip(), f"{dqr_id}: build_dqvp_turtle returned empty string"

    g = Graph()
    g.parse(data=ttl, format="turtle")   # raises on parse error
    assert len(g) > 0, f"{dqr_id}: Turtle parsed to empty graph"


@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_build_dqvp_turtle_has_quality_policy(proto, dqr_id):
    """Generated Turtle must declare the offer as a dqvp:QualityPolicy."""
    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    g    = Graph()
    g.parse(data=ttl, format="turtle")

    policies = list(g.subjects(RDF.type, DQVP.QualityPolicy))
    assert policies, f"{dqr_id}: no dqvp:QualityPolicy node found"


@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_build_dqvp_turtle_correct_left_operand(proto, dqr_id):
    """Generated constraint must use the expected dqvp leftOperand."""
    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    g    = Graph()
    g.parse(data=ttl, format="turtle")

    expected = DQVP[DQR_LEFT_OPERAND[dqr_id]]
    found    = list(g.subjects(ODRL.leftOperand, expected))
    assert found, (
        f"{dqr_id}: expected leftOperand dqvp:{DQR_LEFT_OPERAND[dqr_id]} not found.\n"
        f"  leftOperands present: {[str(o) for _, _, o in g.triples((None, ODRL.leftOperand, None))]}"
    )


@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_build_dqvp_turtle_has_all_checks(proto, dqr_id):
    """Permission must use dqvp:allChecks (not a bare odrl:constraint)."""
    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    assert "dqvp:allChecks" in ttl, f"{dqr_id}: dqvp:allChecks not found in Turtle output"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2 — Plan generation (requires EYE)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.requires_eye
@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_plan_dqvp_produces_operations(proto, planner, eye_available, tmp_path, dqr_id):
    """plan_dqvp must return a Graph containing at least one tbox:Operation node."""
    if not eye_available:
        pytest.skip("EYE reasoner not installed")

    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    ttl_file = tmp_path / f"{dqr_id}.ttl"
    ttl_file.write_text(ttl)

    data_csv = DATA / "Patient_Summary.csv"
    plan = planner.plan_dqvp(str(ttl_file), str(data_csv))

    ops = list(plan.subjects(RDF.type, TB.Operation))
    assert ops, f"{dqr_id}: plan_dqvp returned no tbox:Operation nodes"


@pytest.mark.requires_eye
@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_plan_dqvp_correct_abstract(proto, planner, eye_available, tmp_path, dqr_id):
    """Plan graph must contain an Operation with the expected ab:Check* abstract."""
    if not eye_available:
        pytest.skip("EYE reasoner not installed")

    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    ttl_file = tmp_path / f"{dqr_id}.ttl"
    ttl_file.write_text(ttl)

    data_csv = DATA / "Patient_Summary.csv"
    plan     = planner.plan_dqvp(str(ttl_file), str(data_csv))

    expected_abstract = AB[DQR_EXPECTED_ABSTRACT[dqr_id]]
    ops_with_abstract = list(plan.subjects(TB.hasAbstract, expected_abstract))
    assert ops_with_abstract, (
        f"{dqr_id}: no Operation with hasAbstract ab:{DQR_EXPECTED_ABSTRACT[dqr_id]}.\n"
        f"  Abstracts found: {[str(o) for _, _, o in plan.triples((None, TB.hasAbstract, None))]}"
    )


@pytest.mark.requires_eye
@pytest.mark.parametrize("dqr_id", DQR_IDS)
def test_plan_dqvp_has_terminal_constraint(proto, planner, eye_available, tmp_path, dqr_id):
    """Plan graph must include a terminal odrl:Constraint validation operation."""
    if not eye_available:
        pytest.skip("EYE reasoner not installed")

    req  = _load_req(dqr_id)
    ttl  = proto.build_dqvp_turtle(req, _load_tmpl(req))
    ttl_file = tmp_path / f"{dqr_id}.ttl"
    ttl_file.write_text(ttl)

    data_csv = DATA / "Patient_Summary.csv"
    plan     = planner.plan_dqvp(str(ttl_file), str(data_csv))

    terminal_ops = list(plan.subjects(TB.isTerminal, RDF.type))
    # isTerminal is a literal true; query differently
    terminal_ops = [s for s, p, o in plan.triples((None, TB.isTerminal, None))]
    assert terminal_ops, f"{dqr_id}: no terminal operation in plan (tb:isTerminal missing)"


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 3 — End-to-end: all 7 DQRs produce a non-empty plan
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.requires_eye
def test_all_ehds_dqrs_produce_plan(proto, planner, eye_available, tmp_path):
    """All 7 EHDS DQRs must compile to a non-empty plan graph via DQVP pipeline."""
    if not eye_available:
        pytest.skip("EYE reasoner not installed")

    results = {}
    for dqr_id in DQR_IDS:
        req      = _load_req(dqr_id)
        ttl      = proto.build_dqvp_turtle(req, _load_tmpl(req))
        ttl_file = tmp_path / f"{dqr_id}.ttl"
        ttl_file.write_text(ttl)

        data_csv = DATA / "Patient_Summary.csv"
        plan     = planner.plan_dqvp(str(ttl_file), str(data_csv))
        ops      = list(plan.subjects(RDF.type, TB.Operation))
        results[dqr_id] = len(ops)

    failures = [k for k, v in results.items() if v == 0]
    assert not failures, (
        f"DQRs produced empty plan: {failures}\n"
        f"  Operations per DQR: {results}"
    )
