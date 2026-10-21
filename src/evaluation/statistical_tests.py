import pandas as pd
import numpy as np
from sksurv.metrics import concordance_index_censored
import os

def calculate_cindex(time, status, risk_scores):
    """Calculate Harrell's C-index using sksurv."""
    try:
        # sksurv expects status as boolean
        status_bool = status.astype(bool)
        result = concordance_index_censored(status_bool, time, risk_scores)
        return result[0]
    except Exception as e:
        return np.nan

def bootstrap_comparison(df, model_a, imp_a, model_b, imp_b, n_iterations=1000, random_seed=42):
    """
    Perform bootstrap comparison between two model-imputation combinations.
    Returns: Mean diff, 95% CI of diff, and p-value.
    """
    np.random.seed(random_seed)

    # Filter data for specific combinations
    data_a = df[(df['Model'] == model_a) & (df['Imputation'] == imp_a)].copy()
    data_b = df[(df['Model'] == model_b) & (df['Imputation'] == imp_b)].copy()

    if len(data_a) == 0:
        print(f"   Warning: No data found for {model_a}+{imp_a}")
        return None
    if len(data_b) == 0:
        print(f"   Warning: No data found for {model_b}+{imp_b}")
        return None

    # Join on Index to ensure same patients
    data_a = data_a.set_index('Index')
    data_b = data_b.set_index('Index')

    merged = data_a[['Observed_Time', 'Observed_Status', 'Predicted_Risk']].join(
        data_b[['Predicted_Risk']], lsuffix='_A', rsuffix='_B'
    ).dropna()

    if len(merged) == 0:
        print(f"   Warning: No shared patients found between {model_a} and {model_b}")
        return None

    n_samples = len(merged)
    diffs = []

    print(f"   Bootstrapping {model_a}+{imp_a} vs {model_b}+{imp_b} (n={n_samples})...")

    for _ in range(n_iterations):
        boot_indices = np.random.choice(merged.index, size=n_samples, replace=True)
        boot_sample = merged.loc[boot_indices]

        c_a = calculate_cindex(boot_sample['Observed_Time'], boot_sample['Observed_Status'], boot_sample['Predicted_Risk_A'])
        c_b = calculate_cindex(boot_sample['Observed_Time'], boot_sample['Observed_Status'], boot_sample['Predicted_Risk_B'])

        if not np.isnan(c_a) and not np.isnan(c_b):
            diffs.append(c_a - c_b)

    if not diffs:
        return None

    diffs = np.array(diffs)
    mean_diff = np.mean(diffs)
    ci_lower = np.percentile(diffs, 2.5)
    ci_upper = np.percentile(diffs, 97.5)

    # Two-sided p-value
    p_val = 2 * min(np.mean(diffs > 0), np.mean(diffs < 0))
    p_val = max(p_val, 1/n_iterations)

    return {
        'Comparison': f"{model_a}+{imp_a} vs {model_b}+{imp_b}",
        'Mean_Diff': mean_diff,
        'CI_Lower': ci_lower,
        'CI_Upper': ci_upper,
        'P_Value': p_val,
        'Significant': p_val < 0.05
    }

def main():
    print("=" * 80)
    print("STATISTICAL COMPARISON OF SURVIVAL MODELS (BOOTSTRAP)")
    print("=" * 80)

    # Check for model_predictions.csv
    possible_paths = [
        "model_predictions.csv",
        "results/predictions/model_predictions.csv",
        "../results/predictions/model_predictions.csv",
        "../../results/predictions/model_predictions.csv"
    ]

    input_file = None
    for path in possible_paths:
        if os.path.exists(path):
            input_file = path
            break

    if not input_file:
        print("ERROR: model_predictions.csv not found.")
        print("Please ensure the file exists in one of the following locations:")
        for path in possible_paths:
            print(f"  - {path}")
        return

    print(f"\nUsing data from: {input_file}")
    df = pd.read_csv(input_file)

    # Normalize Imputation names
    # Handling file paths and special mice cases
    df['Imputation'] = df['Imputation'].apply(lambda x: os.path.basename(str(x)))
    # If the basename is still the full filename like 'imputed_GAIN_full.csv', we extract 'GAIN'
    def extract_method(name):
        if 'mice' in name.lower(): return 'MICE'
        if name.startswith('imputed_'):
            return name.split('_')[1]
        return name

    df['Imputation'] = df['Imputation'].apply(extract_method)

    print(f"\nAvailable Imputations found: {df['Imputation'].unique()}")
    print(f"Available Models found: {df['Model'].unique()}")
    print(f"Total prediction records: {len(df)}")

    results = []
    imputations = ['GAIN', 'MIDA', 'missForest', 'MICE']

    # 1. PRIMARY COMPARISON: RSF+GAIN vs Gradient Boosting+missForest
    print("\n1. Primary Comparison (Reviewer Request)")
    res = bootstrap_comparison(df, 'RSF', 'GAIN', 'GradientBoosting', 'missForest')
    if res: results.append(res)

    # 2. WITHIN RSF COMPARISONS
    print("\n2. Within RSF Imputation Comparisons")
    for i in range(len(imputations)):
        for j in range(i + 1, len(imputations)):
            res = bootstrap_comparison(df, 'RSF', imputations[i], 'RSF', imputations[j])
            if res: results.append(res)

    # 3. WITHIN GRADIENT BOOSTING COMPARISONS
    print("\n3. Within Gradient Boosting Imputation Comparisons")
    for i in range(len(imputations)):
        for j in range(i + 1, len(imputations)):
            res = bootstrap_comparison(df, 'GradientBoosting', imputations[i], 'GradientBoosting', imputations[j])
            if res: results.append(res)

    # 4. RSF vs DEEPSURV COMPARISONS (Phase 3 Target)
    print("\n4. RSF vs DeepSurv Comparisons")
    for imp in imputations:
        res = bootstrap_comparison(df, 'RSF', imp, 'DeepSurv', imp)
        if res: results.append(res)

    # 5. RSF vs Elastic-net Cox Comparisons
    print("\n5. RSF vs Elastic-net Cox Comparisons")
    for imp in imputations:
        res = bootstrap_comparison(df, 'RSF', imp, 'CoxnetElasticNet', imp)
        if res: results.append(res)

    if not results:
        print("\nERROR: No comparisons were successful. Check if Model/Imputation names match accurately.")
        return

    # Save results with FDR adjustment
    output_df = pd.DataFrame(results)

    # FDR adjustment (Benjamini-Hochberg)
    from statsmodels.stats.multitest import multipletests
    p_values = output_df['P_Value'].values
    reject, p_adjusted, _, _ = multipletests(p_values, method='fdr_bh')
    output_df['P_Value_Adjusted'] = p_adjusted
    output_df['Significant_Adjusted'] = reject
    output_df['Significant_Raw'] = output_df['Significant']

    output_df.to_csv("statistical_comparison_results.csv", index=False)

    print("\n" + "=" * 80)
    print("STATISTICAL TESTING COMPLETE")
    print("=" * 80)
    print("Results saved to: statistical_comparison_results.csv")
    print("\nSummary of Significant Findings (FDR-adjusted p < 0.05):")
    sig = output_df[output_df['Significant_Adjusted'] == True]
    if len(sig) > 0:
        print(sig[['Comparison', 'Mean_Diff', 'P_Value', 
                   'P_Value_Adjusted']])
    else:
        print("No statistically significant differences after FDR adjustment.")
    print("=" * 80)

if __name__ == "__main__":
    main()