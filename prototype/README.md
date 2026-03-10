# Managing Data Quality Requirements in Data Spaces

A prototype web application built with **Streamlit** for managing Data Quality Requirements (DQRs) in data spaces. The tool allows users to define, instantiate, update and transform DQRs into machine-executable ODRL rules.

---

## Features

- **Reference Catalog of DQR Patterns** — Browse reusable patterns that describe common DQRs across dimensions such as completeness, accuracy, timeliness, etc.
- **Data Space Catalog of DQRs** — Instantiate concrete requirements from patterns, filling in specific parameter values to generate formal requirement statements.
- **ODRL Rules and Validation Services Generation** — Transform requirements into ODRL (Open Digital Rights Language) rules and automated validation services.

---

## Project Structure

```
.
├── dqr_prototype_gui.py          # Main Streamlit application
├── dqr_pattern.schema.json       # JSON file containing DQR Pattern structure
├── patterns/                     # JSON files defining DQR Patterns
├── requirements/                 # JSON files of instantiated DQRs
├── odrl_rules/                   # Generated ODRL rule files (output)
├── odrl_templates/               # ODRL templates, one per pattern
└── services/                     # (Reserved) Validation services
```

---

## Prerequisites

- Python 3.9+
- [Streamlit](https://streamlit.io/)
- pandas

Install dependencies:

```bash
pip install streamlit pandas
```

---

## Running the Application

```bash
streamlit run dqr_prototype_gui.py
```

The app will open in your browser at `http://localhost:8501`.

---

## Data Model

### DQR Pattern (`patterns/*.json`)

Patterns are reusable templates that describe a family of DQRs. Each pattern file contains:

| Field | Description |
|---|---|
| `id` | Unique pattern identifier |
| `version` | Pattern version |
| `goal` | Purpose of the requirement |
| `description` | Human-readable description |
| `qualityDimension` | Dimension and source standard (e.g. ISO 25012) |
| `statementTemplate` | Template string with `%parameter%` placeholders |
| `parameters` | List of parameters with name, domain type and invariants |
| `relationships` | Related patterns and relationship types |
| `sourceEntity` | Who defined the pattern |
| `supportingMaterials` | References or links |
| `history` | Change log |
| `date` | Creation or last update date |

**Example:**

```json
{
  "id": "DQRP2",
  "goal": "Supporting a required percentage of non-empty values of an attribute in an entity",
  "description": "Values of an attribute must be mandatory",
  "date": "03/11/2025",
  "version": "1.0",
  "qualityDimension": {
    "dimension": "Completeness",
    "source": "ISO/IEC 25012"
  },
  "relationships": [
    {
      "type": "Conflict",
      "relatedPattern": "DQRPz",
      "description": "Allowing optional attributes to contain any percentage of empty values without restriction"
    },
    {
      "type": "Dependency",
      "relatedPattern": "DQRPt",
      "description": "Ensuring that non-empty values conform to the expected data type and format"
    }
  ],
  "statementTemplate": "In the %entityName% entity, the %attributeName% attribute must contain %operator% %percentageValue% percent non-empty values",
  "parameters": [
    {
      "name": "entityName",
      "domainType": "String"
    },
    {
      "name": "attributeName",
      "domainType": "String"
    },
    {
      "name": "operator",
      "domainType": "String",
      "invariants": "operator = “at least” OR “exactly”"
    },
    {
      "name": "percentageValue",
      "domainType": "Float",
      "invariants": "1<= percentageValue<=100"
    }
  ],
  "sourceEntity": "Source Entity [Data Space Governance Authority, Requirement Engineer, Automated Process, …]",
  "supportingMaterials": "Document [rulebooks, standards, legislation, …] with precise details (URL, page, line)",
  "history": "Change description [Created, Updated, Deleted] and change date"
}
```

---

### DQ Requirement (`requirements/*.json`)

A DQ Requirement is an instantiation of a pattern with concrete values. Each file contains:

| Field | Description |
|---|---|
| `id` | Unique requirement identifier |
| `goal` | Inherited from pattern |
| `description` | Inherited from pattern |
| `qualityDimension` | Inherited from pattern |
| `pattern` | Reference to source pattern (`id` + `version`) |
| `parameters` | Key-value map of filled-in parameter values |
| `statement` | Generated statement (template with values substituted) |
| `sourceEntity` | Organisation or actor that raised the requirement |
| `supportingMaterials` | References or links |
| `history` | Change log |

**Example:**

```json
{
  "id": "DQR1EH",
  "goal": "Supporting a required percentage of non-empty values of an attribute in an entity",
  "description": "Values of an attribute must be mandatory",
  "qualityDimension": {
    "dimension": "Completeness",
    "source": "ISO/IEC 25012"
  },
  "pattern": {
    "id": "DQRP2",
    "version": "1.0"
  },
  "parameters": {
    "entityName": "PatientIdentification",
    "attributeName": "nationalHealthcarePatientID",
    "operator": "contain",
    "percentageValue": "100"
  },
  "statement": "In the PatientIdentification entity, the nationalHealthcarePatientID attribute must contain contain\u00a0100 percent non-empty values",
  "sourceEntity": "EHDS Governance Authority",
  "supportingMaterials": "Dataspace Rulebook (page 40)",
  "history": "Created 28/01/2026"
}
```

---

### ODRL Template (`odrl_templates/<pattern_id>_odrl_template.json`)

Each pattern must have a corresponding ODRL template that defines how its constraints map to ODRL vocabulary. Key fields:

| Field | Description |
|---|---|
| `context` | JSON-LD `@context` for the generated rule |
| `policy.type` | ODRL policy type (e.g. `odrl:Agreement`) |
| `policy.action` | ODRL action (e.g. `odrl:use`) |
| `assignee.fixed` | Fixed assignee URI |
| `target.parameter` | Parameter name that holds the target asset |
| `constraint.leftOperand` | The quality metric being constrained |
| `constraint.rightOperand` | Parameter providing the threshold value and its XSD type |
| `constraint.operatorMapping` | Map from symbolic operators (`=`, `<`, `>=`, …) to ODRL operators |
| `constraint.unit.fixed` | Fixed unit URI (e.g. `qudt:MinuteTime`) |

---

## Application Workflow

```
Pattern Catalog
      │
      │  Select pattern + fill parameters
      ▼
DQR Catalog (instantiated requirements)
      │
      │  Select requirement + ODRL template
      ▼
ODRL Rule (saved to odrl_rules/)
```

1. **Browse patterns** in the Reference Catalog to understand what kinds of requirements are available.
2. **Create a DQ Requirement** by selecting a pattern and providing values for each parameter. The app generates a formal natural-language statement automatically.
3. **Manage requirements** — update parameter values (regenerating the statement), delete, or view full details.
4. **Generate an ODRL rule** for any requirement. The app combines the requirement's parameters with the pattern's ODRL template to produce a JSON-LD policy, which can be saved to disk.

---

## Adding New Patterns

1. Create a JSON file in `patterns/` following the schema above.
2. Create a corresponding ODRL template in `odrl_templates/` named `<pattern_id>_odrl_template.json`.
3. The new pattern will appear automatically in the application.

---

## Notes

- All data is stored as local JSON files; no database is required.
- ODRL rules are saved to `odrl_rules/` with the naming convention `<requirement_id>_odrl.json`.
- The validation service generation feature is reserved for future development.

