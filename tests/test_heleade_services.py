"""
HELEADE use case: every DQR has its ODRL rule and its validation service, and the
links between them are recorded in the files.

  rule      prototype/odrl_rules/heleade/<DQR>_odrl.json, built by the prototype
  policy    services/heleade/dqvp_policy.ttl, the DQVP policy mapped from the DQRs
  checker   services/heleade/policy_checker.ttl, compiled from that policy
  service   services/policyChecker_<hash>/, exported from the DQVP check
            (tools/dqvp/operationalization-pipeline/export_services.py); its
            service.json says which DQR it validates

The services read the synthetic HELEADE data in tools/dqvp/data/heleade.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from rdflib import Graph, Namespace, RDF, URIRef

PC = Namespace("https://feed-upc.github.io/DQVP-position/pc#")

HERE     = Path(__file__).resolve().parent
CATS     = HERE.parent
REQS     = CATS / "prototype" / "requirements" / "heleade"
RULES    = CATS / "prototype" / "odrl_rules" / "heleade"
TMPL     = CATS / "prototype" / "odrl_templates"
SERVICES = {json.loads(p.read_text())["dqr"]: p.parent
            for p in (CATS / "services").glob("policyChecker_*/service.json")}

# (measured value, satisfied) on the synthetic HELEADE data
EXPECTED = {
    "DQR1HL": (100.0, True),     # every monitoring site has a location
    "DQR2HL": (99.0196, False),  # 5 of 510 observation times are not written in UTC
    "DQR3HL": (100.0, True),     # no notDetected record carries breeding evidence
    "DQR4HL": (4.0, False),      # La Mata has 4 monitoring sites, fewer than 5
}
DQRS = sorted(p.stem for p in REQS.glob("DQR*HL.json"))


def _service(dqr):
    spec = importlib.util.spec_from_file_location(f"svc_{dqr}", SERVICES[dqr] / "validation_job.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_heleade_dqr_is_covered():
    assert DQRS == sorted(EXPECTED) == sorted(SERVICES)


@pytest.mark.parametrize("dqr", DQRS)
def test_rule_is_derived_from_its_dqr(proto, dqr):
    req  = json.loads((REQS / f"{dqr}.json").read_text())
    tmpl = json.loads((TMPL / f"{req['pattern']['id']}_odrl_template.json").read_text())
    saved = json.loads((RULES / f"{dqr}_odrl.json").read_text())
    assert saved["@graph"][0]["tb:derivedFrom"] == dqr
    assert saved == proto.build_odrl_rule(req, tmpl), f"{dqr}: saved rule differs from the prototype's"


@pytest.mark.parametrize("dqr", DQRS)
def test_manifest_links_resolve(dqr):
    m   = json.loads((SERVICES[dqr] / "service.json").read_text())
    req = json.loads((CATS / m["requirement"]).read_text())
    assert m["dqr"] == req["id"] == dqr
    assert m["pattern"] == req["pattern"]
    assert (CATS / "prototype" / "patterns" / f"{m['pattern']['id']}.json").exists()
    rule = json.loads((CATS / m["odrlRule"]).read_text())
    assert rule["@graph"][0]["tb:derivedFrom"] == dqr
    assert m["dqvpCheck"] == f"c-{dqr.lower()}"
    assert (CATS / m["dqvpPolicy"]["file"]).exists()
    for path in m["dataProducts"].values():
        assert (CATS / path).exists(), path


@pytest.mark.parametrize("dqr", DQRS)
def test_policy_checker_links_the_check(dqr):
    m  = json.loads((SERVICES[dqr] / "service.json").read_text())
    pc = m["policyChecker"]
    # named like the engine's services: the MD5 of the check's IRI
    assert SERVICES[dqr].name == f"policyChecker_{hashlib.md5(pc['check'].encode()).hexdigest()[:8]}"
    assert pc["check"].endswith(m["dqvpCheck"])
    g  = Graph().parse(CATS / pc["file"], format="turtle")
    checker, workflow = URIRef(pc["checker"]), URIRef(pc["workflow"])
    assert (checker, RDF.type, PC.PolicyChecker) in g
    assert str(g.value(checker, PC.accordingTo)).endswith(m["dqvpPolicy"]["id"])
    assert (checker, PC.hasWorkflow, workflow) in g
    # filter -> measure -> compare -> report; a record-level check measures in two
    # steps, a row predicate and its aggregate
    steps = [op.rsplit("/", 1)[-1] for op in pc["operations"]]
    assert steps in (["filter", "measure", "compare", "report"],
                     ["filter", "predicate", "aggregate", "compare", "report"]), steps
    for op in map(URIRef, pc["operations"]):
        assert (workflow, PC.hasOp, op) in g
        assert (op, PC.forCheck, URIRef(pc["check"])) in g


@pytest.mark.parametrize("dqr", DQRS)
def test_service_reproduces_the_paper(dqr):
    value, ok = _service(dqr).run_validation()
    assert (value, ok) == EXPECTED[dqr]
