"""
HELEADE use case: every DQR has its ODRL rule and its validation service, and the
links between them are recorded in the files.

  rule      prototype/odrl_rules/heleade/<DQR>_odrl.json, built by the prototype
  service   services/heleade/<DQR>/, exported from the DQVP check
            (tools/dqvp/operationalization-pipeline/export_services.py)

The services read the synthetic HELEADE data in tools/dqvp/data/heleade.
"""
import importlib.util
import json
from pathlib import Path

import pytest

HERE     = Path(__file__).resolve().parent
CATS     = HERE.parent
REQS     = CATS / "prototype" / "requirements" / "heleade"
RULES    = CATS / "prototype" / "odrl_rules" / "heleade"
TMPL     = CATS / "prototype" / "odrl_templates"
SERVICES = CATS / "services" / "heleade"

# (measured value, satisfied) on the synthetic HELEADE data
EXPECTED = {
    "DQR1HL": (100.0, True),     # every monitoring site has a location
    "DQR2HL": (99.0196, False),  # 5 of 510 observation times are not written in UTC
    "DQR3HL": (100.0, True),     # no notDetected record carries breeding evidence
    "DQR4HL": (4.0, False),      # La Mata has 4 monitoring sites, fewer than 5
}
DQRS = sorted(p.stem for p in REQS.glob("DQR*HL.json"))


def _service(dqr):
    spec = importlib.util.spec_from_file_location(f"svc_{dqr}", SERVICES / dqr / "validation_job.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_heleade_dqr_is_covered():
    assert DQRS == sorted(EXPECTED)


@pytest.mark.parametrize("dqr", DQRS)
def test_rule_is_derived_from_its_dqr(proto, dqr):
    req  = json.loads((REQS / f"{dqr}.json").read_text())
    tmpl = json.loads((TMPL / f"{req['pattern']['id']}_odrl_template.json").read_text())
    saved = json.loads((RULES / f"{dqr}_odrl.json").read_text())
    assert saved["@graph"][0]["tb:derivedFrom"] == dqr
    assert saved == proto.build_odrl_rule(req, tmpl), f"{dqr}: saved rule differs from the prototype's"


@pytest.mark.parametrize("dqr", DQRS)
def test_manifest_links_resolve(dqr):
    m   = json.loads((SERVICES / dqr / "service.json").read_text())
    req = json.loads((CATS / m["requirement"]).read_text())
    assert m["dqr"] == req["id"] == dqr
    assert m["pattern"] == req["pattern"]
    assert (CATS / "prototype" / "patterns" / f"{m['pattern']['id']}.json").exists()
    rule = json.loads((CATS / m["odrlRule"]).read_text())
    assert rule["@graph"][0]["tb:derivedFrom"] == dqr
    assert m["dqvpCheck"] == f"c-{dqr.lower()}"
    for path in m["dataProducts"].values():
        assert (CATS / path).exists(), path


@pytest.mark.parametrize("dqr", DQRS)
def test_service_reproduces_the_paper(dqr):
    value, ok = _service(dqr).run_validation()
    assert (value, ok) == EXPECTED[dqr]
