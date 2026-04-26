"""
End-to-end test: verify that every requirement (DQR1EH–DQR6EH) can be
turned into an ODRL rule via its pattern's template, and that the generated
rule matches the expected file stored in odrl_rules/.

Also checks that every pattern (DQRP1–DQRP6) has an active ODRL template.
"""

import json
import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve directories relative to this test file
# ---------------------------------------------------------------------------
PROTO_DIR = Path(__file__).resolve().parent
PATTERNS_DIR = PROTO_DIR / "patterns"
REQUIREMENTS_DIR = PROTO_DIR / "requirements"
ODRL_TEMPLATES_DIR = PROTO_DIR / "odrl_templates"
ODRL_RULES_DIR = PROTO_DIR / "odrl_rules"

# ---------------------------------------------------------------------------
# Import build_odrl_rule from the Streamlit app without launching Streamlit.
# We monkey-patch 'streamlit' with a stub so the module can be imported.
# ---------------------------------------------------------------------------
import types
import unittest.mock as _mock

# Build a comprehensive Streamlit stub that returns itself for any attribute/call
class _StStub(types.ModuleType):
    """A mock that swallows every Streamlit call at import time."""
    class _Obj:
        def __getattr__(self, _):
            return self
        def __call__(self, *a, **kw):
            return self
        def __iter__(self):
            return iter([])
        def __bool__(self):
            return False
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass

    class _SessionState(dict):
        def __getattr__(self, name):
            try:
                return self[name]
            except KeyError:
                raise AttributeError(name)
        def __setattr__(self, name, value):
            self[name] = value

    def __init__(self):
        super().__init__("streamlit")
        self.session_state = self._SessionState()

    def __getattr__(self, name):
        if name == "session_state":
            return self.__dict__["session_state"]
        return self._Obj()

sys.modules["streamlit"] = _StStub()

# Now import the builder
sys.path.insert(0, str(PROTO_DIR))
from dqr_prototype_gui import build_odrl_rule  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sorted_json(obj):
    """Return a canonical JSON string for comparison (sorted keys, consistent indent)."""
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class Results:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, label: str):
        self.passed += 1
        print(f"  ✓ {label}")

    def fail(self, label: str, detail: str = ""):
        self.failed += 1
        msg = f"  ✗ {label}"
        if detail:
            msg += f"\n    {detail}"
        print(msg)
        self.errors.append(label)

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed, {self.failed} failed")
        if self.errors:
            print("Failed tests:")
            for e in self.errors:
                print(f"  - {e}")
        print(f"{'='*60}")
        return self.failed == 0


def test_all_patterns_have_templates(res: Results):
    """Every pattern DQRP1–DQRP6 should have an active ODRL template."""
    print("\n--- Test: every pattern has an active ODRL template ---")
    for pfile in sorted(PATTERNS_DIR.glob("*.json")):
        pattern = load_json(pfile)
        pid = pattern["id"]
        tmpl_path = ODRL_TEMPLATES_DIR / f"{pid}_odrl_template.json"
        if tmpl_path.exists():
            res.ok(f"{pid} has template")
        else:
            # Check if it's in old/
            old_path = ODRL_TEMPLATES_DIR / "old" / f"{pid}_odrl_template.json"
            if old_path.exists():
                res.fail(f"{pid} template only in old/ (not active)",
                         f"Found at {old_path.relative_to(PROTO_DIR)}")
            else:
                res.fail(f"{pid} has NO template at all")


def test_all_requirements_have_templates(res: Results):
    """Every requirement should reference a pattern that has an active template."""
    print("\n--- Test: every requirement's pattern has an active template ---")
    for rfile in sorted(REQUIREMENTS_DIR.glob("*.json")):
        req = load_json(rfile)
        rid = req["id"]
        pid = req["pattern"]["id"]
        tmpl_path = ODRL_TEMPLATES_DIR / f"{pid}_odrl_template.json"
        if tmpl_path.exists():
            res.ok(f"{rid} → {pid} template exists")
        else:
            res.fail(f"{rid} → {pid} template MISSING")


def deep_compare(generated, expected, path=""):
    """Recursively compare two JSON structures and return a list of differences."""
    diffs = []
    if type(generated) != type(expected):
        diffs.append(f"{path}: type mismatch: {type(generated).__name__} vs {type(expected).__name__}")
        return diffs
    if isinstance(generated, dict):
        all_keys = set(generated.keys()) | set(expected.keys())
        for k in sorted(all_keys):
            kpath = f"{path}.{k}" if path else k
            if k not in generated:
                diffs.append(f"{kpath}: MISSING in generated")
            elif k not in expected:
                diffs.append(f"{kpath}: EXTRA in generated")
            else:
                diffs.extend(deep_compare(generated[k], expected[k], kpath))
    elif isinstance(generated, list):
        if len(generated) != len(expected):
            diffs.append(f"{path}: list length {len(generated)} vs {len(expected)}")
        for i in range(min(len(generated), len(expected))):
            diffs.extend(deep_compare(generated[i], expected[i], f"{path}[{i}]"))
    else:
        if generated != expected:
            diffs.append(f"{path}: '{generated}' != '{expected}'")
    return diffs


def test_odrl_rule_generation(res: Results):
    """
    For each requirement with an active template, generate the ODRL rule
    and compare it to the expected output in odrl_rules/.
    """
    print("\n--- Test: ODRL rule generation matches expected output ---")
    for rfile in sorted(REQUIREMENTS_DIR.glob("*.json")):
        req = load_json(rfile)
        rid = req["id"]
        pid = req["pattern"]["id"]

        tmpl_path = ODRL_TEMPLATES_DIR / f"{pid}_odrl_template.json"
        if not tmpl_path.exists():
            res.fail(f"{rid}: cannot generate (no template for {pid})")
            continue

        expected_path = ODRL_RULES_DIR / f"{rid}_odrl.json"
        if not expected_path.exists():
            res.fail(f"{rid}: no expected output file {expected_path.name}")
            continue

        template = load_json(tmpl_path)
        expected = load_json(expected_path)

        try:
            generated = build_odrl_rule(req, template)
        except Exception as e:
            res.fail(f"{rid}: build_odrl_rule raised {type(e).__name__}: {e}")
            continue

        diffs = deep_compare(generated, expected)
        if not diffs:
            res.ok(f"{rid}: generated rule matches expected")
        else:
            detail = "\n    ".join(diffs[:10])
            if len(diffs) > 10:
                detail += f"\n    ... and {len(diffs) - 10} more differences"
            res.fail(f"{rid}: generated rule differs from expected ({len(diffs)} diffs)", detail)


def test_odrl_rule_structure(res: Results):
    """
    For each generated ODRL rule, verify it has the mandatory JSON-LD
    structure: @context, @graph, and required node types.
    """
    print("\n--- Test: generated ODRL rules have valid structure ---")
    for rfile in sorted(REQUIREMENTS_DIR.glob("*.json")):
        req = load_json(rfile)
        rid = req["id"]
        pid = req["pattern"]["id"]

        tmpl_path = ODRL_TEMPLATES_DIR / f"{pid}_odrl_template.json"
        if not tmpl_path.exists():
            continue

        template = load_json(tmpl_path)
        try:
            rule = build_odrl_rule(req, template)
        except Exception:
            continue  # already reported in previous test

        # Check @context
        if "@context" not in rule:
            res.fail(f"{rid}: missing @context")
        else:
            ctx = rule["@context"]
            for ns in ["odrl", "dqv", "rdf", "rdfs", "xsd"]:
                if ns not in ctx and f"{ns}:" not in str(ctx):
                    res.fail(f"{rid}: @context missing namespace '{ns}'")

        # Check @graph
        if "@graph" not in rule:
            res.fail(f"{rid}: missing @graph")
            continue

        graph = rule["@graph"]
        if not isinstance(graph, list) or len(graph) == 0:
            res.fail(f"{rid}: @graph is empty or not a list")
            continue

        # First node should be the rule node
        rule_node = graph[0]
        if rule_node.get("@type") != "dqv:QualityPolicy":
            res.fail(f"{rid}: first graph node type is '{rule_node.get('@type')}', expected 'dqv:QualityPolicy'")
        else:
            res.ok(f"{rid}: structure valid (QualityPolicy + {len(graph)} graph nodes)")

        # Check the rule has permission or duty
        has_permission = "odrl:permission" in rule_node
        has_duty = any("odrl:duty" in p for p in rule_node.get("odrl:permission", []))
        if not has_permission:
            res.fail(f"{rid}: rule node missing odrl:permission")

        # Check derivedFrom
        if rule_node.get("tb:derivedFrom") != rid:
            res.fail(f"{rid}: tb:derivedFrom is '{rule_node.get('tb:derivedFrom')}', expected '{rid}'")


def test_round_trip_all_templates(res: Results):
    """
    Verify each template can handle its pattern's parameters by
    constructing a synthetic requirement and generating a rule without errors.
    """
    print("\n--- Test: round-trip with synthetic requirements for each template ---")
    for tmpl_file in sorted(ODRL_TEMPLATES_DIR.glob("*.json")):
        template = load_json(tmpl_file)
        pid = template["patternId"]

        pattern_path = PATTERNS_DIR / f"{pid}.json"
        if not pattern_path.exists():
            res.fail(f"{pid}: pattern file not found")
            continue

        pattern = load_json(pattern_path)
        dim = pattern["qualityDimension"]["dimension"]

        # Build synthetic parameters from pattern definition
        params = {}
        for p in pattern.get("parameters", []):
            name = p["name"]
            dtype = p.get("domainType", "String")
            if "Float" in dtype or "Integer" in dtype or "Value" in dtype:
                params[name] = "42"
            elif "Set" in dtype:
                params[name] = "{testValue}"
            elif "TimeUnit" in dtype:
                params[name] = "Days"
            elif p.get("invariants") and "operator" in name.lower():
                # Pick first invariant option
                inv = p["invariants"]
                if isinstance(inv, str) and "OR" in inv:
                    first = inv.split('"')[1] if '"' in inv else "at least"
                    params[name] = first
                else:
                    params[name] = "at least"
            else:
                params[name] = f"Test{name}"

        # Build a synthetic requirement
        synthetic_req = {
            "id": f"SYNTHETIC_{pid}",
            "goal": pattern["goal"],
            "description": pattern["description"],
            "qualityDimension": pattern["qualityDimension"],
            "pattern": {"id": pid, "version": pattern["version"]},
            "parameters": params,
            "statement": "Synthetic test statement",
            "sourceEntity": "TestAuthority",
        }

        try:
            rule = build_odrl_rule(synthetic_req, template)
            if "@context" in rule and "@graph" in rule and len(rule["@graph"]) > 0:
                res.ok(f"{pid}: synthetic requirement → valid ODRL rule ({len(rule['@graph'])} nodes)")
            else:
                res.fail(f"{pid}: generated rule is structurally incomplete")
        except Exception as e:
            res.fail(f"{pid}: build_odrl_rule raised {type(e).__name__}: {e}")


def test_operator_mappings(res: Results):
    """
    Verify that operator values in requirements correctly map to ODRL operators.
    """
    print("\n--- Test: operator mappings ---")
    test_cases = [
        ("DQR1EH", "at least", "odrl:gteq"),   # DQRP2 completeness
        ("DQR4EH", "at least", "odrl:gteq"),   # DQRP5 volume
        ("DQR5EH", "not exceed", "odrl:lt"),    # DQRP6 fairness
    ]

    for rid, operator_val, expected_odrl_op in test_cases:
        rpath = REQUIREMENTS_DIR / f"{rid}.json"
        if not rpath.exists():
            res.fail(f"{rid}: requirement file not found")
            continue
        req = load_json(rpath)
        pid = req["pattern"]["id"]
        tmpl_path = ODRL_TEMPLATES_DIR / f"{pid}_odrl_template.json"
        if not tmpl_path.exists():
            res.fail(f"{rid}: template not found for {pid}")
            continue

        template = load_json(tmpl_path)
        rule = build_odrl_rule(req, template)

        # Find the constraint operator in the generated rule
        found_op = None
        for node in rule["@graph"]:
            for perm in node.get("odrl:permission", []):
                for constr in perm.get("odrl:constraint", []):
                    if "odrl:operator" in constr:
                        found_op = constr["odrl:operator"]
                # Also check duty constraints
                for duty in perm.get("odrl:duty", []):
                    for constr in duty.get("odrl:constraint", []):
                        if "odrl:operator" in constr:
                            found_op = constr["odrl:operator"]

        if found_op == expected_odrl_op:
            res.ok(f"{rid}: '{operator_val}' → '{expected_odrl_op}'")
        else:
            res.fail(f"{rid}: expected '{expected_odrl_op}', got '{found_op}'")


def test_consistency_refinement(res: Results):
    """
    Verify DQR3EH (Consistency/DQRP4) produces a rule with refinement + constraint.
    """
    print("\n--- Test: consistency pattern produces refinement structure ---")
    rpath = REQUIREMENTS_DIR / "DQR3EH.json"
    if not rpath.exists():
        res.fail("DQR3EH: requirement file not found")
        return
    req = load_json(rpath)
    tmpl_path = ODRL_TEMPLATES_DIR / "DQRP4_odrl_template.json"
    template = load_json(tmpl_path)
    rule = build_odrl_rule(req, template)

    rule_node = rule["@graph"][0]
    permissions = rule_node.get("odrl:permission", [])
    if not permissions:
        res.fail("DQR3EH: no permissions in rule")
        return

    perm = permissions[0]
    duties = perm.get("odrl:duty", [])
    if not duties:
        res.fail("DQR3EH: no duties (expected refinement-based structure)")
        return

    duty = duties[0]

    # Check for refinement block
    action = duty.get("odrl:action", {})
    refinements = action.get("odrl:refinement", [])
    if refinements:
        ref = refinements[0]
        if ref.get("odrl:operator") == "odrl:isAnyOf":
            res.ok("DQR3EH: has refinement with odrl:isAnyOf")
        else:
            res.fail(f"DQR3EH: refinement operator is '{ref.get('odrl:operator')}', expected 'odrl:isAnyOf'")
    else:
        res.fail("DQR3EH: no refinement block in duty action")

    # Check for constraint block
    constraints = duty.get("odrl:constraint", [])
    if constraints:
        res.ok("DQR3EH: has constraint in duty")
    else:
        res.fail("DQR3EH: no constraint in duty")


def test_measurement_concept_override(res: Results):
    """
    DQR4EH has measurementConcept='Volume' overriding dimension='Completeness'.
    The generated rule should use 'Volume' for measurement IDs.
    """
    print("\n--- Test: measurementConcept override (DQR4EH) ---")
    rpath = REQUIREMENTS_DIR / "DQR4EH.json"
    req = load_json(rpath)
    tmpl_path = ODRL_TEMPLATES_DIR / "DQRP5_odrl_template.json"
    template = load_json(tmpl_path)
    rule = build_odrl_rule(req, template)

    # The measurement node should be "VolumeMeasurement", not "ValidityMeasurement"
    graph_ids = [n.get("@id", "") for n in rule["@graph"]]
    if "ab:VolumeMeasurement" in graph_ids:
        res.ok("DQR4EH: uses 'VolumeMeasurement' (overridden)")
    else:
        res.fail(f"DQR4EH: expected 'ab:VolumeMeasurement' in graph IDs: {graph_ids}")

    if "ab:ValidityMeasurement" in graph_ids:
        res.fail("DQR4EH: should NOT have 'ab:ValidityMeasurement' (dimension was overridden)")


def test_reference_standard_node(res: Results):
    """
    DQRP3 (Compliance/Standards) should generate a ReferenceStandard node.
    """
    print("\n--- Test: reference standard node (DQRP3 rules) ---")
    for rid in ["DQR2EH", "DQR6EH"]:
        rpath = REQUIREMENTS_DIR / f"{rid}.json"
        req = load_json(rpath)
        tmpl_path = ODRL_TEMPLATES_DIR / "DQRP3_odrl_template.json"
        template = load_json(tmpl_path)
        rule = build_odrl_rule(req, template)

        has_ref_standard = any(
            n.get("@type") == "tb:ReferenceStandard"
            for n in rule["@graph"]
        )
        if has_ref_standard:
            res.ok(f"{rid}: has ReferenceStandard node")
        else:
            res.fail(f"{rid}: missing ReferenceStandard node")


def test_gui_create_then_generate(res: Results):
    """
    Simulate the exact GUI workflow: create a DQR from a pattern (only
    pattern-defined parameters + sourceEntity), then generate the ODRL rule.
    This catches mismatches where build_odrl_rule expects fields the GUI
    doesn't collect (e.g. a missing operator parameter).
    """
    print("\n--- Test: GUI workflow (create DQR → generate ODRL) for each pattern ---")

    # Realistic sample parameter values per pattern
    gui_inputs = {
        "DQRP1": {
            "entityName": "SensorData",
            "attributeName1": "SensorData.temperature",
            "amountOfTime": "60",
            "timeUnit": "Minutes",
            "attributeName2": "SensorData.timestamp",
        },
        "DQRP2": {
            "entityName": "Patient",
            "attributeName": "Patient.email",
            "operator": "at least",
            "percentageValue": "95",
        },
        "DQRP3": {
            "entityName": "Address",
            "attributeName": "Address.postalCode",
            "standardName": "ISO 3166",
        },
        "DQRP4": {
            "entityName1": "Order",
            "attributeName1": "Order.status",
            "ValueSet1": "{cancelled}",
            "attributeName2": "Order.refundAmount",
            "entityName2": "Payment",
            "operator": "contain",
            "ValueSet2": "{0}",
        },
        "DQRP5": {
            "entityName": "ClinicalTrial.participants",
            "operator": "at least",
            "value": "500",
        },
        "DQRP6": {
            "entityName": "Survey.respondents",
            "attributeName": "Survey.respondents.ageGroup",
            "operator": "not exceed",
            "percValue": "10",
        },
    }

    for tmpl_file in sorted(ODRL_TEMPLATES_DIR.glob("*.json")):
        template = load_json(tmpl_file)
        pid = template["patternId"]
        pattern_path = PATTERNS_DIR / f"{pid}.json"
        if not pattern_path.exists():
            res.fail(f"{pid}: pattern file not found")
            continue

        pattern = load_json(pattern_path)
        params = gui_inputs.get(pid)
        if params is None:
            res.fail(f"{pid}: no GUI test inputs defined")
            continue

        # Replicate exactly what page_create_dqr saves
        gui_dqr = {
            "id": f"GUI_TEST_{pid}",
            "goal": pattern["goal"],
            "description": pattern["description"],
            "qualityDimension": pattern["qualityDimension"],
            "pattern": {"id": pattern["id"], "version": pattern["version"]},
            "parameters": params,
            "statement": "GUI-generated test statement",
            "sourceEntity": "TestGovernanceAuthority",
            "supportingMaterials": "",
            "history": "",
        }

        try:
            rule = build_odrl_rule(gui_dqr, template)
        except Exception as e:
            res.fail(f"{pid}: GUI DQR → build_odrl_rule raised {type(e).__name__}: {e}")
            continue

        # Validate structure
        if "@context" not in rule or "@graph" not in rule:
            res.fail(f"{pid}: GUI DQR → incomplete rule (missing @context/@graph)")
            continue
        graph = rule["@graph"]
        if len(graph) == 0:
            res.fail(f"{pid}: GUI DQR → empty @graph")
            continue

        rule_node = graph[0]
        if rule_node.get("@type") != "dqv:QualityPolicy":
            res.fail(f"{pid}: GUI DQR → wrong type: {rule_node.get('@type')}")
            continue

        # Find the constraint operator and verify it's not the fallback "odrl:eq"
        # unless the template actually specifies eq
        found_op = None
        for perm in rule_node.get("odrl:permission", []):
            for c in perm.get("odrl:constraint", []):
                found_op = c.get("odrl:operator")
            for d in perm.get("odrl:duty", []):
                for c in d.get("odrl:constraint", []):
                    found_op = c.get("odrl:operator")

        constraint_tmpl = template.get("constraint", {})
        if "operator" in constraint_tmpl:
            expected_op = constraint_tmpl["operator"]
        elif "operatorMapping" in constraint_tmpl:
            op_val = params.get("operator", params.get("comparisonOperator", ""))
            expected_op = constraint_tmpl["operatorMapping"].get(op_val)
        else:
            expected_op = None

        if expected_op and found_op != expected_op:
            res.fail(f"{pid}: GUI DQR → operator '{found_op}' != expected '{expected_op}'")
        else:
            res.ok(f"{pid}: GUI DQR → valid rule (operator={found_op}, {len(graph)} nodes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("End-to-End Test: ODRL Rule Generation from Templates & Patterns")
    print("=" * 60)

    res = Results()

    test_all_patterns_have_templates(res)
    test_all_requirements_have_templates(res)
    test_odrl_rule_generation(res)
    test_odrl_rule_structure(res)
    test_round_trip_all_templates(res)
    test_operator_mappings(res)
    test_consistency_refinement(res)
    test_measurement_concept_override(res)
    test_reference_standard_node(res)
    test_gui_create_then_generate(res)

    success = res.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
