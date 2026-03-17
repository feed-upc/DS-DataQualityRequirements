import great_expectations

import great_expectations as gx
import pandas as pd

def run_gx_validation(data_path):
    context = gx.get_context(mode='ephemeral')
    _df = pd.read_csv(data_path)
    suite = context.suites.add(gx.ExpectationSuite(name='semantic_suite'))

    # Step 2: http://www.semanticweb.org/acraf/ontologies/2024/healthmesh/abox#CheckFairness
    _kw = {'column': 'gender', 'threshold': 0.05}
    _cats = sorted(_df['gender'].dropna().unique().tolist())
    _uniform = {"values": _cats, "weights": [1.0/len(_cats)]*len(_cats)}
    _kw['partition_object'] = _uniform
    suite.add_expectation(gx.expectations.ExpectColumnKLDivergenceToBeLessThan(**_kw))

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
    if len(sys.argv) < 2:
        print("Usage: python validation_job.py <data_path>")
        sys.exit(1)
    data_file = sys.argv[1]
    print(f"Loading data from {data_file}...")
    try:
        result = run_gx_validation(data_file)
        print("\n=== VALIDATION RESULT ===")
        print(result)
        print("===========================")
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)
