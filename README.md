# Reference Catalog of Data Quality Requirement Patterns

The Reference catalog of Data Quality Requirement (DQR) Patterns is designed to support Data Space Governance Authorities in defining and managing data quality throughout the governance and operational processes underpinning their data spaces. It enables authorities to elicit DQRs by selecting and instantiating relevant patterns, thereby constructing a data space specific DQR catalog tailored to their governance and operational needs.

These patterns capture common and recurring DQRs encountered in data space data sharing and governance scenarios. For each pattern in the catalog, the associated data quality dimension, its identifier, a textual description of the requirement, the pattern template, an example of the pattern instantiation, and the corresponding automated validation service are explicitly defined.

| Quality Dimension | DQR Pattern Identifier | DQR Description | DQR Pattern | DQR Pattern Instantiation Example | Validation Service | Result |
| ----------------- | ---------------------- | --------------- | ----------- | --------------------------------- | ------------------ | ------ |
| Currentness (ISO/IEC 25012) | DQRP1 | A specific data age is required for the values of an attribute of an entity | [DQRP1](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP1/DQRP1-Currentness.png) | The EHDS performs the [DQRP1 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP1/DQR7EHInstantiation.png) to define a DQR specifying that Patient Summary records are only valid if their data age does not exceed 1440 minutes. Its DQR record is [DQR7EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR7EH.json) and its corresponding ODRL rule is [DQR7EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR7EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_05fb5861) | – |
| Completeness (ISO/IEC 25012) | DQRP2 | Values of an attribute must be mandatory | [DQRP2](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP2/DQRP2-Completeness.png) | The EHDS performs the [DQRP2 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP2/DQR1EHInstantiation.png) to define a DQR specifying that national healthcare patient ID shall be unambiguously used to identify patients and, therefore, it must not be a null value. Its DQR record is [DQR1EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR1EH.json) and its corresponding ODRL rule is [DQR1EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR1EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_3ae130f1) | 98.0%, violated |
| Compliance (ISO/IEC 25012) | DQRP3 | Values of an attribute must follow a specific format | [DQRP3](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP3/DQRP3-Compliance.png) | The EHDS performs the [DQRP3 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP3/DQR2EHInstantiation.png) to define a DQR specifying that patient affiliation countries must be referenced using country codes from the ISO 3166 International Standard. Its DQR record is [DQR2EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR2EH.json) and its corresponding ODRL rule is [DQR2EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR2EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_5b132606) | 98.2%, violated |
| Compliance (ISO/IEC 25012) | DQRP3 | Values of an attribute must follow a specific format | [DQRP3](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP3/DQRP3-Compliance.png) | The EHDS also performs a [DQRP3 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP3/DQR6EHInstantiation.png) to define a DQR specifying that hospital countries must be referenced using country codes from the ISO 3166 International Standard. Its DQR record is [DQR6EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR6EH.json) and its corresponding ODRL rule is [DQR6EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR6EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_32ec32b7) | 98.2%, violated |
| Consistency (ISO/IEC 25012) | DQRP4 | Values of an attribute must be compatible with values of another attribute | [DQRP4](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP4/DQRP4-Consistency.png) | The EHDS performs the [DQRP4 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP4/DQR3EHInstantiation.png) to define a DQR specifying that male patients shall not have any recorded pregnancy history. Its DQR record is [DQR3EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR3EH.json) and its corresponding ODRL rule is [DQR3EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR3EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_842a8b01) | 100.0%, satisfied |
| Completeness (ISO/IEC 25012) | DQRP5 | A dataset must contain a minimum number of records | [DQRP5](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP5/DQRP5-Completeness.png) | The EHDS performs the [DQRP5 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP5/DQR4EHInstantiation.png) to define a DQR specifying that an AMR study must include at least 2000 bacterial isolates to ensure statistical reliability. Its DQR record is [DQR4EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR4EH.json) and its corresponding ODRL rule is [DQR4EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR4EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_21a1ab80) | 2,249 isolates, satisfied |
| Fairness (Biessmann et al., 2021) | DQRP6 | An entity composition includes groups in appropriate proportions for the task and context | [DQRP6](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP6/DQRP6-Fairness.png) | The EHDS performs the [DQRP6 Instantiation](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/media/DQRP6/DQR5EHInstantiation.png) to define a DQR specifying that accurate estimation of antimicrobial resistance rates requires a study population with balanced representation of male and female patients for mitigating potential biases. Its DQR record is [DQR5EH.json](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/requirements/DQR5EH.json) and its corresponding ODRL rule is [DQR5EH](https://github.com/feed-upc/DS-DataQualityRequirements/blob/main/prototype/odrl_rules/DQR5EH_odrl.json) | [policyChecker](https://github.com/feed-upc/DS-DataQualityRequirements/tree/main/services/policyChecker_96133334) | 8.8 points gap, violated |

> Biessmann, F., Golebiowski, J., Rukat, T., Lange, D., Schmidt, P.: Automated data validation in machine learning systems. IEEE Data Eng. Bull. 44, 51–65 (2021)

The Result column gives the measured value and verdict of each DQR on the synthetic data in `tools/dqvp/data/`, into which defects were introduced on purpose. It is produced by the [DQVP pipeline](#dqvp), which does not yet cover DQRP1.

## Repository Structure

- **`prototype/`** — Proof-of-concept tool for defining, instantiating, and operationalizing DQRs.
  - `patterns/` — DQR pattern definitions (DQRP1–6, JSON)
  - `requirements/` — Instantiated DQR specifications for the EHDS use case
  - `odrl_rules/` — Generated ODRL policies, one per DQR instantiation
  - `odrl_templates/` — ODRL generation templates, one per pattern
  - `dqr_prototype2.py` — Main application (`streamlit run prototype/dqr_prototype2.py`)
- **`media/`** — Auto-generated pattern diagrams and instantiation visualizations
- **`services/`** — Auto-generated validation services, one per DQR instantiation
- **`tools/`** — The Validation Engine and DQVP, as submodules (see below)
- **`benchmarks/`** — The benchmark notebook, with its saved results (see [Benchmarks](#benchmarks))
- **`evaluation/`** — Preliminary feedback from data-space practitioners

## Validation Engine

The validation services in `services/` are executed by the **DataValidationWorkflow** engine, available as a submodule under [`tools/validation-engine`](https://github.com/feed-upc/DataValidationWorkflow). The engine takes an ODRL policy as input, resolves the data and service catalog metadata, and deploys the corresponding validation service as an executable microservice.

## DQVP

[`tools/dqvp`](https://github.com/feed-upc/DQVP-position) is DQVP, an ODRL profile for data quality, with a pipeline that compiles a DQVP policy into checks for several engines and executes them. It covers constraints that plain ODRL cannot state, such as row filters, reference standards, per-group counts and share gaps.

The pipeline reads the DQRs from `prototype/requirements/` and its synthetic data from `tools/dqvp/data/`: 500 Patient Summary records and 2,249 AMR isolates derived from them. It produced the **Result** column of the table above. It needs a separate environment from the Validation Engine, because it uses Great Expectations 0.18, and the [EYE reasoner](https://github.com/eyereasoner/eye) on `PATH`.

```bash
git submodule update --init tools/dqvp
pip install -r tools/dqvp/requirements.txt
cd tools/dqvp/operationalization-pipeline
python dqr_to_dqvp.py         # measured values and verdicts of the EHDS DQRs
python test_end_to_end.py     # every stage, checked against values computed from the CSVs
python automation_report.py   # what is authored and what is generated, per DQR
```

### Benchmarks

The notebook [`benchmarks/benchmarks.ipynb`](benchmarks/benchmarks.ipynb) measures how compilation grows with the number of checks, and how execution grows with the size of the data and the number of checks. It runs the functions of the pipeline's `bench_planning.py` and `bench_execution.py`. Its saved outputs are the run below, made on 23 Oct 2026 on a laptop with an AMD Ryzen 5 PRO 215 (6 cores, 12 threads) and 7.1 GiB of memory, under Ubuntu 24.04 on WSL2, with Python 3.12.3, DuckDB 1.5.6, rdflib 7.6.0 and EYE 11.24.4. Times vary by up to about 30% between runs on this machine.

| Checks | Planning | Code generation | Per check |
| -----: | -------: | --------------: | --------: |
| 128 | 2.17 s | 0.54 s | 21 ms |
| 256 | 4.14 s | 1.13 s | 21 ms |
| 512 | 8.01 s | 2.13 s | 20 ms |

| Checks over 5,000,000 records | Execution | Per check |
| ----------------------------: | --------: | --------: |
| 3 | 0.07 s | 24 ms |
| 12 | 0.35 s | 29 ms |
| 48 | 1.12 s | 23 ms |
| 96 | 2.08 s | 22 ms |

- **Compilation**: medians of 7 runs. Planning includes about 0.3 s to start the reasoner, each check adds 4 operations to the policy checker, and doubling the policy multiplies the time by 1.7 to 1.9.
- **Execution**: medians of 5 runs, with the data already loaded; loading the 5,000,000-record CSV took 2.3 s. Single checks range from 2–12 ms (null and non-null rates) to 0.2 s (uniqueness of 5,000,000 distinct identifiers) and 0.6 s (conformance to the 249 ISO 3166 codes).
- **Data size**: the three EHDS checks took 8 ms over 500 records, 0.14 s over 500,000 and 0.58 s over 5,000,000, with the same measured values at every size.
