"""
Extract Lactate Median Values for Figure B1
============================================
Calculates median Lactate values from observed and imputed datasets
for comparison across imputation methods.
"""

import pandas as pd
import numpy as np


def extract_lactate_medians():

    print("=" * 80)
    print("EXTRACTING LACTATE MEDIAN VALUES FOR FIGURE B1")
    print("=" * 80)

    # Load original data (observed values)
    print("\n1. Loading original MIMIC-IV data...")
    original = pd.read_csv("../data/raw/mimic_sepsis_cohort_full.csv")
    observed_median = original['Lac'].median()
    observed_missing = original['Lac'].isna().sum()
    observed_pct = 100 * original['Lac'].isna().mean()

    print(f"   Observed Lactate median: {observed_median:.2f} mmol/L")
    print(f"   Missing values: {observed_missing} ({observed_pct:.1f}%)")

    # Extract medians from imputed datasets
    results = []

    # MICE (average across 5 imputations)
    print("\n2. Processing MICE (pooling 5 imputations)...")
    mice_lacs = []
    for i in range(1, 6):
        try:
            mice_data = pd.read_csv(f"imputed_mice{i}_full.csv")
            mice_lacs.append(mice_data['Lac'].values)
            print(f"   MICE {i}: median = {mice_data['Lac'].median():.2f}")
        except FileNotFoundError:
            print(f"   MICE {i}: file not found")

    if mice_lacs:
        # Pool MICE imputations (average across datasets)
        mice_pooled = np.mean(mice_lacs, axis=0)
        mice_median = np.median(mice_pooled)
        results.append({
            'Method': 'MICE',
            'Median_Imputed': mice_median,
            'Median_Observed': observed_median
        })
        print(f"   MICE pooled median: {mice_median:.2f}")

    # missForest
    print("\n3. Processing missForest...")
    try:
        missforest_data = pd.read_csv("imputed_missForest_full.csv")
        missforest_median = missforest_data['Lac'].median()
        results.append({
            'Method': 'missForest',
            'Median_Imputed': missforest_median,
            'Median_Observed': observed_median
        })
        print(f"   missForest median: {missforest_median:.2f}")
    except FileNotFoundError:
        print("   missForest file not found")

    # GAIN
    print("\n4. Processing GAIN...")
    try:
        gain_data = pd.read_csv("imputed_GAIN_full.csv")
        gain_median = gain_data['Lac'].median()
        results.append({
            'Method': 'GAIN',
            'Median_Imputed': gain_median,
            'Median_Observed': observed_median
        })
        print(f"   GAIN median: {gain_median:.2f}")
    except FileNotFoundError:
        print("   GAIN file not found")

    # MIDA
    print("\n5. Processing MIDA...")
    try:
        mida_data = pd.read_csv("imputed_MIDA_full.csv")
        mida_median = mida_data['Lac'].median()
        results.append({
            'Method': 'MIDA',
            'Median_Imputed': mida_median,
            'Median_Observed': observed_median
        })
        print(f"   MIDA median: {mida_median:.2f}")
    except FileNotFoundError:
        print("   MIDA file not found")

    # Save results
    if results:
        results_df = pd.DataFrame(results)
        results_df.to_csv("lactate_medians_figure_b1.csv", index=False)

        print("\n" + "=" * 80)
        print("RESULTS SUMMARY")
        print("=" * 80)
        print("\nLactate Median Values (mmol/L):")
        print(results_df.to_string(index=False))

        # Generate LaTeX text
        print("\n" + "=" * 80)
        print("LATEX TEXT FOR SECTION 3.2 (Figure B1)")
        print("=" * 80)

        latex_parts = []
        for _, row in results_df.iterrows():
            latex_parts.append(f"{row['Method']}: median imputed {row['Median_Imputed']:.2f} vs observed {row['Median_Observed']:.2f}")

        latex_text = "with key variables like Lactate showing close alignment (" + ", ".join(latex_parts) + ")."
        print(f"\n{latex_text}")

        with open("lactate_latex_text.txt", "w") as f:
            f.write(latex_text)

        print("\n" + "=" * 80)
        print("Files saved:")
        print("  - lactate_medians_figure_b1.csv")
        print("  - lactate_latex_text.txt")
        print("=" * 80)
    else:
        print("\nERROR: No imputed files found!")


# ============================================================================
# IMPUTATION SCORING FUNCTION
# ============================================================================

def score_imputations(run_dir=None):
    import os

    if run_dir is None:
        if os.path.exists("Results sensitivity"):
            run_dir = "Results sensitivity"
        elif os.path.exists("synthetic_complete.csv"):
            run_dir = "."
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cand = os.path.join(base_dir, "Results sensitivity")
            if os.path.exists(cand):
                run_dir = cand
            else:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                run_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "Results sensitivity"))

    truth_file = os.path.join(run_dir, "synthetic_complete.csv")
    if not os.path.exists(truth_file):
        print(f"Missing file: {os.path.basename(truth_file)}")
        return

    truth_df = pd.read_csv(truth_file)

    variables = ["Age", "ALT", "HR", "RR", "GCS", "Cl", "Lac", "Plt", "Na", "AST"]
    mechanisms = ["mar", "mcar", "mnar"]
    rates = [10, 26.8, 40.01, 54.98]

    # Precompute standard deviation of true values (all 852 subjects)
    truth_sd = {var: float(truth_df[var].std(ddof=1)) for var in variables}

    records = []

    for mech in mechanisms:
        for rate in rates:
            rate_str = "10" if rate == 10 else str(rate)
            mask_filename = f"synthetic_{mech}_{rate_str}.csv"
            mask_file = os.path.join(run_dir, mask_filename)

            if not os.path.exists(mask_file):
                print(f"Missing file: {mask_filename}")
                continue

            synthetic_df = pd.read_csv(mask_file)

            # 1. MICE (mice1..mice5)
            mice_filenames = [f"mice{i}_{mech}_{rate_str}.csv" for i in range(1, 6)]
            mice_paths = [os.path.join(run_dir, f) for f in mice_filenames]
            mice_missing = [f for f, p in zip(mice_filenames, mice_paths) if not os.path.exists(p)]

            if mice_missing:
                for f in mice_missing:
                    print(f"Missing file: {f}")
            else:
                mice_dfs = [pd.read_csv(p) for p in mice_paths]
                for var in variables:
                    mask = synthetic_df[var].isna().values
                    if np.sum(mask) == 0:
                        records.append({
                            "Mechanism": mech,
                            "Rate": rate,
                            "Method": "MICE",
                            "Variable": var,
                            "RMSE": np.nan,
                            "MAE": np.nan,
                            "NRMSE": np.nan,
                            "coverage": np.nan,
                            "between_imp_var": np.nan
                        })
                    else:
                        y_true = truth_df[var].values[mask].astype(float)
                        imp_vals = np.array([df[var].values[mask].astype(float) for df in mice_dfs])  # shape: (5, n_miss)
                        imp_mean = np.mean(imp_vals, axis=0)
                        diff = imp_mean - y_true
                        rmse = float(np.sqrt(np.mean(diff ** 2)))
                        mae = float(np.mean(np.abs(diff)))
                        sd_t = truth_sd.get(var, np.nan)
                        nrmse = float(rmse / sd_t) if (sd_t is not None and sd_t > 0) else np.nan

                        sd_imp = np.std(imp_vals, axis=0, ddof=1)
                        ci_lower = imp_mean - 1.96 * sd_imp
                        ci_upper = imp_mean + 1.96 * sd_imp
                        coverage = float(np.mean((y_true >= ci_lower) & (y_true <= ci_upper)))
                        var_imp = np.var(imp_vals, axis=0, ddof=1)
                        between_imp_var = float(np.mean(var_imp))

                        records.append({
                            "Mechanism": mech,
                            "Rate": rate,
                            "Method": "MICE",
                            "Variable": var,
                            "RMSE": rmse,
                            "MAE": mae,
                            "NRMSE": nrmse,
                            "coverage": coverage,
                            "between_imp_var": between_imp_var
                        })

            # 2. Single imputation methods: missForest, GAIN, MIDA
            single_methods = [
                ("missForest", f"missForest_{mech}_{rate_str}.csv"),
                ("GAIN", f"GAIN_{mech}_{rate_str}.csv"),
                ("MIDA", f"MIDA_{mech}_{rate_str}.csv")
            ]

            for method_name, fname in single_methods:
                fpath = os.path.join(run_dir, fname)
                if not os.path.exists(fpath):
                    print(f"Missing file: {fname}")
                    continue

                imp_df = pd.read_csv(fpath)
                for var in variables:
                    mask = synthetic_df[var].isna().values
                    if np.sum(mask) == 0:
                        records.append({
                            "Mechanism": mech,
                            "Rate": rate,
                            "Method": method_name,
                            "Variable": var,
                            "RMSE": np.nan,
                            "MAE": np.nan,
                            "NRMSE": np.nan,
                            "coverage": np.nan,
                            "between_imp_var": np.nan
                        })
                    else:
                        y_true = truth_df[var].values[mask].astype(float)
                        y_imp = imp_df[var].values[mask].astype(float)
                        diff = y_imp - y_true
                        rmse = float(np.sqrt(np.mean(diff ** 2)))
                        mae = float(np.mean(np.abs(diff)))
                        sd_t = truth_sd.get(var, np.nan)
                        nrmse = float(rmse / sd_t) if (sd_t is not None and sd_t > 0) else np.nan

                        records.append({
                            "Mechanism": mech,
                            "Rate": rate,
                            "Method": method_name,
                            "Variable": var,
                            "RMSE": rmse,
                            "MAE": mae,
                            "NRMSE": nrmse,
                            "coverage": np.nan,
                            "between_imp_var": np.nan
                        })

    score_long = pd.DataFrame(records)
    metric_cols = ["RMSE", "MAE", "NRMSE", "coverage", "between_imp_var"]

    if not score_long.empty:
        score_summary = score_long.groupby(["Mechanism", "Rate", "Method"], as_index=False)[metric_cols].mean()
    else:
        score_summary = pd.DataFrame(columns=["Mechanism", "Rate", "Method"] + metric_cols)

    out_by_var = os.path.join(run_dir, "imputation_diagnostics_by_variable.csv")
    out_summary = os.path.join(run_dir, "imputation_diagnostics_summary.csv")

    score_long.to_csv(out_by_var, index=False)
    score_summary.to_csv(out_summary, index=False)

    if os.path.abspath(run_dir) != os.path.abspath("."):
        score_long.to_csv("imputation_diagnostics_by_variable.csv", index=False)
        score_summary.to_csv("imputation_diagnostics_summary.csv", index=False)

    print(f"imputation_diagnostics_by_variable.csv: {len(score_long)} rows")
    print(f"imputation_diagnostics_summary.csv: {len(score_summary)} rows")

    return score_long, score_summary


if __name__ == "__main__":
    extract_lactate_medians()
    score_imputations()

