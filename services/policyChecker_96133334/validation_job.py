import great_expectations

import great_expectations as gx
import pandas as pd

def run_gx_validation(data_path):
    context = gx.get_context(mode='ephemeral')
    _df = pd.read_csv(data_path)
    suite = context.suites.add(gx.ExpectationSuite(name='semantic_suite'))

    # Step 2: http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/abox#qM_Fairness
    # DQR5EH: the gap, in percentage points, between the shares of the most and the
    # least frequent gender must be below percValue = 5 (odrl:lt).
    _shares = _df['gender'].dropna().value_counts(normalize=True) * 100
    _df['gender_share_gap'] = float(_shares.max() - _shares.min()) if len(_shares) else 0.0
    suite.add_expectation(gx.expectations.ExpectColumnValuesToBeBetween(column='gender_share_gap', min_value=0, **{'max_value': 5.0, 'strict_max': True}))

    ds = context.data_sources.add_pandas('pandas_source')
    da = ds.add_dataframe_asset(name='df_asset')
    batch_def = da.add_batch_definition_whole_dataframe('dataframe_batch_def')
    validation_definition = gx.ValidationDefinition(name='semantic_validation', data=batch_def, suite=suite)
    context.validation_definitions.add(validation_definition)
    checkpoint = gx.Checkpoint(name='semantic_checkpoint', validation_definitions=[validation_definition])
    context.checkpoints.add(checkpoint)
    result = checkpoint.run(batch_parameters={'dataframe': _df})
    return result.success

if __name__ == "__main__":
    import sys
    # Extract data path from args or use default
    data_file = sys.argv[1] if len(sys.argv) > 1 else "/home/acraf/psr/Fdatavalidation-1/DataProductLayer/DataProduct_EHDS_AMR/Data/Patient_Summary.csv"
    print(f"Loading data from {data_file}...")
    try:
        result = run_gx_validation(data_file)
        print("\n=== VALIDATION RESULT ===")
        print(result)
        print("===========================")
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)
