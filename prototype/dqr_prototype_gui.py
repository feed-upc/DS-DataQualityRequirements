import streamlit as st
import json
import os
import base64
import pandas as pd
import requests
from pathlib import Path

# =========================
# CONFIG
# =========================
PATTERNS_DIR = Path("patterns")
REQUIREMENTS_DIR = Path("requirements")
ODRL_RULES_DIR = Path("odrl_rules")
ODRL_TEMPLATES_DIR = Path("odrl_templates")
ODRL_POLICIES_DIR = Path("..") / "ODRL_policies"
API_URL = os.environ.get("VALIDATION_API_URL", "http://localhost:5000")

st.set_page_config(
    page_title="Managing Data Quality Requirements in Data Spaces",
    layout="wide"
)

# =========================
# STYLES
# =========================
st.markdown("""
<style>
.main-header {
    background-color: rgb(49,83,143);
    padding: 28px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}
.main-header h1 { font-size: 54px; margin-bottom: 10px; }
.main-header p  { font-size: 30px; }
.tool-card {
    border: 1px solid #31538F;
    padding: 18px;
    border-radius: 12px;
    background-color: #fafafa;
    height: 200px;
}
.tool-title { font-size: 30px; font-weight: 600; margin-bottom: 8px; color: rgb(49,83,143); }
.tool-desc  { color: #555; font-size: 24px; }
table { font-size: 20px; border-collapse: collapse; width: 100%; }
th    { font-size: 22px; text-align: center; padding: 8px; }
td    { padding: 8px; }
</style>
""", unsafe_allow_html=True)

# =========================
# DATA LOADERS
# =========================
def load_json_dir(directory: Path) -> list:
    """Load all JSON files from a directory, supporting both objects and lists."""
    items = []
    if directory.exists():
        for file in sorted(directory.glob("*.json")):
            try:
                with open(file, encoding="utf-8") as f:
                    data = json.load(f)
                items.extend(data if isinstance(data, list) else [data])
            except Exception as e:
                st.warning(f"Skipping {file.name}: {e}")
    return items

def load_json_file(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading file {path}: {e}")
        return None

def load_patterns() -> list:
    return load_json_dir(PATTERNS_DIR)

def load_requirements() -> list:
    return load_json_dir(REQUIREMENTS_DIR)

def save_json_file(path: str, data: dict) -> bool:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving file {path}: {e}")
        return False

# =========================
# HELPERS
# =========================
def find_by_id(items: list, item_id: str) -> dict | None:
    return next((item for item in items if item.get("id") == item_id), None)

def fill_statement(template: str, values: dict) -> str:
    for k, v in values.items():
        template = template.replace(f"%{k}%", str(v))
    return template

def pattern_to_row(p: dict) -> dict:
    dim = p.get("qualityDimension", {})
    return {
        "Dimension (Source)": f"{dim.get('dimension','')} ({dim.get('source','')})",
        "Description": p.get("description", ""),
        "Pattern ID": p.get("id", ""),
    }

def requirement_to_row(r: dict) -> dict:
    dim = r.get("qualityDimension", {})
    return {
        "Dimension (Source)": f"{dim.get('dimension','')} ({dim.get('source','')})",
        "Statement": r.get("statement", ""),
        "Requirement ID": r.get("id", ""),
    }

def render_html_table(rows: list[dict]):
    df = pd.DataFrame(rows).reset_index(drop=True)
    st.markdown(df.to_html(index=False, justify="center"), unsafe_allow_html=True)

def navigate(page: str):
    st.session_state.page = page
    st.rerun()

# =========================
# SHARED UI COMPONENTS
# =========================
def show_requirement_info(req: dict):
    """Display read-only fields of a requirement."""
    fields = [
        ("Goal", req.get("goal")),
        ("Description", req.get("description")),
        ("Quality dimension", "{dimension} ({source})".format(**req.get("qualityDimension", {}))),
        ("Pattern", "{id} ({version})".format(**req.get("pattern", {}))),
        ("Statement", req.get("statement")),
        ("Source Entity", req.get("sourceEntity")),
        ("Supporting Materials", req.get("supportingMaterials")),
        ("History", req.get("history")),
    ]
    for label, value in fields:
        st.markdown(f"**{label}**")
        st.info(value or "—")

def select_requirement() -> dict | None:
    """Selectbox to pick a requirement; returns the selected object or None."""
    requirements = load_requirements()
    if not requirements:
        st.warning("No Data Quality Requirements available.")
        return None
    st.write("### Select a Data Quality Requirement")
    ids = [r.get("id") for r in requirements]
    selected_id = st.selectbox("Requirements ID", ids)
    return find_by_id(requirements, selected_id)

def back_button(label: str, target_page: str):
    if st.button(f"⬅ {label}"):
        navigate(target_page)

# =========================
# ODRL BUILDER
# =========================
def build_odrl_rule(requirement: dict, template: dict) -> dict:
    params = requirement.get("parameters", {})
    operator_map = template["constraint"].get("operatorMapping", {})
    operator_symbol = (
        params.get("operator")
        or params.get("comparisonOperator")
        or params.get("comparison")
        or "="
    )
    odrl_operator = operator_map.get(operator_symbol, "odrl:eq")
    attribute = params.get(template["target"]["parameter"])
    threshold_param = template["constraint"]["rightOperand"]["parameter"]
    threshold_value = params.get(threshold_param)
    req_id = requirement["id"]
    dim = requirement["qualityDimension"]["dimension"]

    return {
        "@context": template["context"],
        "@graph": [
            {
                "@id": f"ab:{req_id}Rule",
                "@type": template["policy"]["type"],
                "@rdfs:label": f"ab:{req_id}Rule - QualityPolicy",
                "tb:derivedFrom": req_id,
                "tb:qualityDimension": dim,
                "tb:sourceEntity": {"@id": f"ab:{requirement['sourceEntity']}"},
                "odrl:permission": [
                    {
                        "@id": f"ab:{req_id}_Permission",
                        "@type": "odrl:Permission",
                        "odrl:action": template["policy"]["action"],
                        "odrl:assigner": {"@id": f"ab:{requirement['sourceEntity']}"},
                        "odrl:assignee": {"@id": f"ab:{template['assignee']['fixed']}"},
                        "odrl:target": {"@id": f"ab:{attribute}"},
                        "odrl:constraint": [
                            {
                                "@id": f"ab:{req_id}_Constraint",
                                "@type": "odrl:Constraint",
                                "odrl:leftOperand": {
                                    "@id": f"ab:{template['constraint']['leftOperand']['id']}",
                                    "@type": template["constraint"]["leftOperand"]["type"],
                                },
                                "odrl:operator": odrl_operator,
                                "odrl:rightOperand": {
                                    "@value": str(threshold_value),
                                    "@type": template["constraint"]["rightOperand"]["type"],
                                },
                                "odrl:unit": {"@id": template["constraint"]["unit"]["fixed"]},
                            }
                        ],
                    }
                ],
            },
            {
                "@id": f"ab:{template['constraint']['leftOperand']['id']}",
                "@type": "Metric",
                "rdfs:label": f"{dim} Measurement",
                "dqv:isMeasurementOf": {"@id": f"ab:Check{dim}"},
            },
            {
                "@id": f"ab:{dim}",
                "@type": "Metric",
                "rdfs:label": f"{dim} Metric (Abstract)",
                "dqv:inDimension": {
                    "@id": f"ab:{dim}Dimension",
                    "@type": "dqv:Dimension",
                },
            },
            {
                "@id": f"ab:{dim}Dimension",
                "@type": "dqv:Dimension",
                "rdfs:label": f"{dim} ({requirement['qualityDimension']['source']})",
            },
            {
                "@id": f"ab:{attribute}",
                "@type": "odrl:Asset",
                "odrl:partOf": {"@id": ""},
            },
        ],
    }

# =========================
# PAGE FUNCTIONS
# =========================
def page_home():
    st.markdown("""
    <div class="main-header">
        <h1>Managing Data Quality Requirements in Data Spaces</h1>
        <p>A prototype environment for managing Data Quality Requirements in data spaces</p>
    </div>
    """, unsafe_allow_html=True)

    cards = [
        ("Reference Catalog of Data Quality Requirement Patterns",
         "Explore the reusable catalogue of Data Quality Requirement patterns "
         "supporting consistent specification across data spaces.",
         "catalog"),
        ("Data Space Catalog of Data Quality Requirements",
         "Instantiate concrete Data Quality Requirements from reusable patterns "
         "in the Data Space Specific Data Quality Requirements Catalog to support "
         "governance and automated validation.",
         "manage_dqr"),
        ("Generate ODRL Policies and Validation Services",
         "Transform Data Quality Requirements into machine-executable ODRL "
         "rules and automate them into validation services.",
         "manage_odrl"),
    ]

    for col, (title, desc, page) in zip(st.columns(3), cards):
        with col:
            st.markdown(f"""
            <div class="tool-card">
                <div class="tool-title">{title}</div>
                <div class="tool-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Open", key=f"open_{page}"):
                navigate(page)


def page_catalog():
    st.title("Reference Catalog of Data Quality Requirement Patterns")
    st.write(
        "Explore the reusable catalogue of Data Quality Requirement patterns "
        "supporting consistent specification across data spaces."
    )
    back_button("Back", "home")

    patterns = load_patterns()
    if not patterns:
        st.warning("No patterns found in /patterns folder.")
        return

    render_html_table([pattern_to_row(p) for p in patterns])

    st.write("### Select a Data Quality Requirement pattern")
    selected_id = st.selectbox("Pattern ID", [p.get("id") for p in patterns])

    if st.button("View pattern"):
        st.session_state.selected_pattern = find_by_id(patterns, selected_id)
        navigate("pattern_detail")


def page_pattern_detail():
    back_button("Back to catalog", "catalog")

    p = st.session_state.get("selected_pattern")
    if not p:
        st.error("No pattern selected.")
        return

    st.subheader(f"Pattern: {p.get('id')}")

    sections = [
        ("Goal", p.get("goal")),
        ("Description", p.get("description")),
        ("Quality Dimension",
         f"{p['qualityDimension'].get('dimension')} ({p['qualityDimension'].get('source')})"),
        ("Date", p.get("date")),
        ("Version", p.get("version")),
        ("Statement Template", p.get("statementTemplate")),
        ("Source Entity", p.get("sourceEntity")),
        ("Supporting Materials", p.get("supportingMaterials")),
        ("History", p.get("history")),
    ]
    for title, content in sections:
        st.markdown(f"### {title}")
        st.write(content)

    st.markdown("### Relationships")
    rels = p.get("relationships")
    if isinstance(rels, list) and rels:
        for r in rels:
            if isinstance(r, dict):
                st.write(f"- {r.get('type','')} ({r.get('relatedPattern','')}): {r.get('description','')}")
            else:
                st.write(f"- {r}")
    else:
        st.write("None")

    st.markdown("### Parameters")
    params = p.get("parameters", [])
    if params:
        st.table(pd.DataFrame(params))


def page_manage_dqr():
    st.title("Data Space Catalog of Data Quality Requirements")
    st.write(
        "Instantiate concrete Data Quality Requirements from reusable patterns "
        "in the Data Space Data Quality Requirement Catalog to support governance "
        "and automated validation."
    )
    back_button("Back", "home")

    dqrs = load_requirements()
    if not dqrs:
        st.warning("No requirements found in /requirements folder.")
        return

    render_html_table([requirement_to_row(r) for r in dqrs])

    st.markdown("---")
    st.subheader("Actions")

    action = st.radio("Select an action:", [
        "Select one of the options",
        "Create a Data Quality Requirement",
        "Update a Data Quality Requirement",
        "Delete a Data Quality Requirement",
        "View details of a Data Quality Requirement",
    ], index=0)

    action_map = {
        "Create a Data Quality Requirement": "create_dqr",
        "Update a Data Quality Requirement": "update_dqr",
        "Delete a Data Quality Requirement": "delete_dqr",
        "View details of a Data Quality Requirement": "view_dqr",
    }
    if action in action_map:
        navigate(action_map[action])
    elif action == "Select one of the options":
        st.info("Please choose an action to continue.")


def page_manage_odrl():
    st.title("Generate ODRL Policies and Validation Services")
    st.write(
        "Transform Data Quality Requirements into machine-executable ODRL "
        "policies and automate them into validation services."
    )
    back_button("Back", "home")

    dqrs = load_requirements()
    if not dqrs:
        st.warning("No requirements found in /requirements folder.")
        return

    render_html_table([requirement_to_row(r) for r in dqrs])
    navigate("generate_odrl")


def page_create_dqr():
    st.title("Create a Data Quality Requirement")
    st.write("Create a Data Quality Requirement from a Data Quality Requirement Pattern in the catalog")
    back_button("Back", "manage_dqr")

    patterns = load_patterns()
    if not patterns:
        st.warning("No patterns available.")
        return

    st.write("### Select a Data Quality Requirement pattern")
    selected_id = st.selectbox("Pattern ID", [p.get("id") for p in patterns])
    pattern = find_by_id(patterns, selected_id)

    st.markdown("---")
    st.markdown("### Information inherited from the Data Quality Requirement Pattern")
    for label, value in [
        ("Data Quality Requirement Pattern", f"{pattern['id']} {pattern['version']}"),
        ("Goal", pattern["goal"]),
        ("Data Quality Requirement description", pattern["description"]),
        ("Quality dimension", f"{pattern['qualityDimension']['dimension']} ({pattern['qualityDimension']['source']})"),
        ("Data Quality Requirement statement template", pattern["statementTemplate"]),
    ]:
        st.markdown(f"**{label}**")
        st.info(value)

    st.markdown("---")
    st.markdown("### Create the Data Quality Requirement")
    dqr_id = st.text_input("Data Quality Requirement id")

    st.markdown("#### Provide values for the statement parameters")
    values = {}
    for p in pattern["parameters"]:
        inv = p.get("invariants")
        help_text = ", ".join(inv) if isinstance(inv, list) else (inv or "")
        values[p["name"]] = st.text_input(
            f"{p['name']} ({p['domainType']})", help=help_text, key=f"param_{p['name']}"
        )

    statement = ""
    if all(values.values()):
        statement = fill_statement(pattern["statementTemplate"], values)
        st.markdown("### Generated Data Quality Requirement Statement")
        st.success(statement)

    st.markdown("### Additional Information")
    source_entity = st.text_input("Source Entity (Who raised the Data Quality Requirement?)")
    supporting_materials = st.text_input("Supporting materials")
    history = st.text_input("History")

    if st.button("Save Data Quality Requirement"):
        if not dqr_id:
            st.error("Data Quality Requirement id is required.")
            return
        dqr = {
            "id": dqr_id,
            "goal": pattern["goal"],
            "description": pattern["description"],
            "qualityDimension": pattern["qualityDimension"],
            "pattern": {"id": pattern["id"], "version": pattern["version"]},
            "parameters": values,
            "statement": statement,
            "sourceEntity": source_entity,
            "supportingMaterials": supporting_materials,
            "history": history,
        }
        path = REQUIREMENTS_DIR / f"{dqr_id}.json"
        if save_json_file(str(path), dqr):
            st.success(f"Data Quality Requirement saved to {path}")


def page_update_dqr():
    st.title("Update a Data Quality Requirement")
    st.write("Update information of a Data Quality Requirement")
    back_button("Back", "manage_dqr")

    requirement = select_requirement()
    if not requirement:
        return

    st.markdown("---")
    st.subheader("Current Information")
    for label, value in [
        ("Goal", requirement["goal"]),
        ("Description", requirement["description"]),
        ("Quality dimension", "{dimension} ({source})".format(**requirement["qualityDimension"])),
        ("Pattern", "{id} ({version})".format(**requirement["pattern"])),
        ("Statement", requirement["statement"]),
    ]:
        st.markdown(f"**{label}**")
        st.info(value)

    st.markdown("---")
    st.subheader("Edit Requirement")
    st.markdown("#### Parameters")

    updated_params = {}
    for pname, pvalue in requirement.get("parameters", {}).items():
        updated_params[pname] = st.text_input(pname, value=str(pvalue), key=f"upd_{pname}")

    if st.button("Generate updated statement"):
        if all(v for v in updated_params.values()):
            pattern_path = PATTERNS_DIR / f"{requirement['pattern']['id']}.json"
            pattern = load_json_file(str(pattern_path))
            if pattern:
                new_statement = fill_statement(pattern["statementTemplate"], updated_params)
                st.session_state["updated_statement"] = new_statement
                st.markdown("#### Updated Data Quality Requirement Statement")
                st.success(new_statement)
        else:
            st.warning("Please complete all parameters before generating the statement.")

    st.markdown("#### Additional Information")
    new_source = st.text_input("Source Entity", value=requirement.get("sourceEntity", ""))
    new_materials = st.text_input("Supporting Materials", value=requirement.get("supportingMaterials", ""))
    new_history = st.text_input("History", value=requirement.get("history", ""))

    if st.button("Update Data Quality Requirement"):
        requirement.update({
            "statement": st.session_state.get("updated_statement", requirement.get("statement", "")),
            "sourceEntity": new_source,
            "supportingMaterials": new_materials,
            "history": new_history,
            "parameters": updated_params,
        })
        path = REQUIREMENTS_DIR / f"{requirement['id']}.json"
        if save_json_file(str(path), requirement):
            st.success("✅ Data Quality Requirement updated successfully.")


def page_delete_dqr():
    st.title("Delete a Data Quality Requirement")
    st.write("Delete a Data Quality Requirement from the catalog")
    back_button("Back", "manage_dqr")

    requirement = select_requirement()
    if not requirement:
        return

    st.markdown("---")
    st.subheader("Current Information")
    show_requirement_info(requirement)

    if st.button("Delete Data Quality Requirement"):
        path = REQUIREMENTS_DIR / f"{requirement['id']}.json"
        try:
            os.remove(path)
            st.success("✅ Data Quality Requirement deleted successfully.")
        except Exception as e:
            st.error(f"Error deleting requirement: {e}")


def page_view_dqr():
    st.title("View details of a Data Quality Requirement")
    st.write("View all the information of a Data Quality Requirement")
    back_button("Back", "manage_dqr")

    requirement = select_requirement()
    if not requirement:
        return

    st.markdown("---")
    st.subheader("Current Information")
    show_requirement_info(requirement)


def page_generate_odrl():
    st.title("Generate ODRL Rules and Validation Services")
    st.write("Generate the ODRL rule from a Data Quality Requirement and the corresponding validation service")
    back_button("Back", "home")

    requirement = select_requirement()
    if not requirement:
        return

    st.markdown("---")
    st.subheader("Current Information")
    show_requirement_info(requirement)

    st.markdown("---")
    st.subheader("ODRL rule")

    pattern_id = requirement["pattern"]["id"]
    template_path = ODRL_TEMPLATES_DIR / f"{pattern_id}_odrl_template.json"

    if not template_path.exists():
        st.error(f"ODRL template not found for pattern {pattern_id}")
        return

    template = load_json_file(str(template_path))
    if not template:
        return

    rule = build_odrl_rule(requirement, template)
    st.json(rule)

    if st.button("Save ODRL rule"):
        path = ODRL_RULES_DIR / f"{requirement['id']}_odrl.json"
        if save_json_file(str(path), rule):
            st.success(f"ODRL rule saved to {path}")

    if st.button(f"Generate {requirement['id']} validation service"):
        with st.spinner("Generating validation service — this may take a minute..."):
            # Save the ODRL rule to ODRL_policies/ so the framework picks it up
            ODRL_POLICIES_DIR.mkdir(parents=True, exist_ok=True)
            policies_path = ODRL_POLICIES_DIR / f"DQRP_{requirement['id']}_odrl.json"
            if not save_json_file(str(policies_path), rule):
                st.error("Failed to save ODRL rule to policies directory.")
                return

            # Also save to local odrl_rules/
            local_path = ODRL_RULES_DIR / f"{requirement['id']}_odrl.json"
            save_json_file(str(local_path), rule)

            # Call the validation framework API
            try:
                response = requests.post(
                    f"{API_URL}/generate-validation-service",
                    json={"rule_id": requirement["id"], "data_product": "Patient_Summary"},
                    timeout=300,
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get("message", "Validation service generated successfully."))

                    # Preview the generated validation code
                    validation_code = result.get("validation_code", "")
                    if validation_code:
                        st.markdown("---")
                        st.subheader("Generated Validation Service Code")
                        st.code(validation_code, language="python")

                    # Download ZIP button
                    zip_b64 = result.get("zip_base64", "")
                    if zip_b64:
                        zip_bytes = base64.b64decode(zip_b64)
                        zip_filename = result.get("zip_filename", f"{requirement['id']}_service.zip")
                        st.download_button(
                            label="\u2b07 Download Validation Service (ZIP)",
                            data=zip_bytes,
                            file_name=zip_filename,
                            mime="application/zip",
                        )

                    # Expandable execution logs
                    logs = result.get("logs", "")
                    if logs:
                        with st.expander("Execution Logs"):
                            st.text(logs)
                else:
                    try:
                        error_data = response.json()
                    except Exception:
                        error_data = {}
                    st.error(
                        f"API error ({response.status_code}): "
                        f"{error_data.get('error', error_data.get('detail', response.text))}"
                    )
                    if error_data.get("logs"):
                        with st.expander("Error Logs"):
                            st.text(error_data["logs"])

            except requests.ConnectionError:
                st.error(
                    f"Could not connect to the validation framework API at {API_URL}. "
                    "Make sure the API server is running (python Connector/ValidationFramework/api/api.py)."
                )
            except requests.Timeout:
                st.error("The validation service generation timed out. The process may still be running on the server.")
            except Exception as e:
                st.error(f"Error generating validation service: {e}")


# =========================
# ROUTER
# =========================
PAGES = {
    "home":           page_home,
    "catalog":        page_catalog,
    "pattern_detail": page_pattern_detail,
    "manage_dqr":     page_manage_dqr,
    "manage_odrl":    page_manage_odrl,
    "create_dqr":     page_create_dqr,
    "update_dqr":     page_update_dqr,
    "delete_dqr":     page_delete_dqr,
    "view_dqr":       page_view_dqr,
    "generate_odrl":  page_generate_odrl,
}

if "page" not in st.session_state:
    st.session_state.page = "home"
if "selected_pattern" not in st.session_state:
    st.session_state.selected_pattern = None

PAGES.get(st.session_state.page, page_home)()