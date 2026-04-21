import glob
import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, train_test_split
import re
import traceback
import warnings
import argparse
import sys

# ... [Keep imports and model definitions RSF to DeepSurv unchanged] ...

# ----------------------------------------------------------------------------
# 1. Random Survival Forest (Primary Method)
# ----------------------------------------------------------------------------
def run_rsf(X, y, random_state=42):
    from sksurv.ensemble import RandomSurvivalForest
    rsf = RandomSurvivalForest(
        n_estimators=1000,
        min_samples_split=10,
        min_samples_leaf=15,
        n_jobs=-1,
        random_state=random_state
    )
    rsf.fit(X, y)
    return rsf

def run_xgboost_survival(X, y, params=None):
    import xgboost as xgb
    if params is None:
        params = {
            "objective": "survival:cox",
            "eval_metric": "cox-nloglik",
            "tree_method": "hist",
            "device": "cpu"
        }
    y_xgb = np.where(y['Status'], y['Survival_Time'], -y['Survival_Time'])
    dtrain = xgb.DMatrix(X, label=y_xgb)
    model = xgb.train(params, dtrain, num_boost_round=100, verbose_eval=False)
    return model

def run_gradient_boosting(X, y, random_state=42):
    from sksurv.ensemble import GradientBoostingSurvivalAnalysis
    gbs = GradientBoostingSurvivalAnalysis(
        loss="coxph",
        n_estimators=100,
        learning_rate=0.1,
        random_state=random_state
    )
    gbs.fit(X, y)
    return gbs

def run_deepsurv(X, y, learning_rate=1e-3):
    """
    DeepSurv implementation with regularization to address Reviewer concerns about overfitting.
    Added Dropout and reduced epochs.
    """
    import torchtuples as tt
    from pycox.models import CoxPH
    X = X.astype('float32')
    y_time = y['Survival_Time'].astype('float32')
    y_event = y['Status'].astype('float32')

    # Improved architecture: added dropout to prevent overfitting
    from torch import nn
    net = tt.practical.MLPVanilla(X.shape[1], [32, 32], 1, dropout=0.3)

    model = CoxPH(net, tt.optim.Adam(lr=learning_rate))

    # Reduced epochs from 100 to 50 as per Phase 3 plan
    model.fit(X, (y_time, y_event), batch_size=256, epochs=50, verbose=False)
    return model

# ----------------------------------------------------------------------------
# Cross-Validation Helper
# ----------------------------------------------------------------------------
def run_cv_evaluation(model_func, X, y, model_name="Model", n_splits=10, random_state=42, **kwargs):
    print(f"    Running {n_splits}-Fold CV for {model_name}...")
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    c_indexes = []
    stratify_label = y["Status"]
    fold = 1
    for train_idx, val_idx in skf.split(X, stratify_label):
        X_fold_train, X_fold_val = X[train_idx], X[val_idx]
        y_fold_train, y_fold_val = y[train_idx], y[val_idx]
        scaler = StandardScaler()
        X_fold_train_scaled = scaler.fit_transform(X_fold_train)
        X_fold_val_scaled = scaler.transform(X_fold_val)
        try:
            model = model_func(X_fold_train_scaled, y_fold_train, **kwargs)
            if hasattr(model, "predict"):
                if model_name == "XGBoost":
                    dval = xgb.DMatrix(X_fold_val_scaled)
                    risk_scores = model.predict(dval)
                elif model_name == "DeepSurv":
                    risk_scores = model.predict(X_fold_val_scaled.astype('float32'))
                    if risk_scores.ndim > 1: risk_scores = risk_scores.ravel()
                else:
                    risk_scores = model.predict(X_fold_val_scaled)

                from sksurv.metrics import concordance_index_censored
                c = concordance_index_censored(y_fold_val["Status"], y_fold_val["Survival_Time"], risk_scores)[0]
                c_indexes.append(c)
        except Exception as e:
            print(f"      Fold {fold} Error: {e}")
        fold += 1
    mean_c = np.mean(c_indexes) if c_indexes else 0
    std_c = np.std(c_indexes) if c_indexes else 0
    print(f"    Mean CV C-index: {mean_c:.4f} (+/- {std_c:.4f})")
    return c_indexes

# ----------------------------------------------------------------------------
# Rubin's Rules Pooling
# ----------------------------------------------------------------------------
def rubins_pooling(estimates, variances, m):
    pooled_estimate = np.mean(estimates)
    W = np.mean(variances)
    B = np.var(estimates, ddof=1)
    T = W + (1 + 1/m) * B
    pooled_se = np.sqrt(T)
    ci_lower = pooled_estimate - 1.96 * pooled_se
    ci_upper = pooled_estimate + 1.96 * pooled_se
    return pooled_estimate, T, pooled_se, ci_lower, ci_upper

def prepare_features(df):
    X_df = df.drop(columns=['Survival_Time', 'Status'])
    X_df = pd.get_dummies(X_df, drop_first=True)
    return X_df

def group_mice_files(files):
    mice_groups = {}
    single_files = []
    for file in files:
        match = re.match(r'imputed_mice(\d+)_(.+)\.csv', file)
        if match:
            mechanism = match.group(2)
            if mechanism not in mice_groups: mice_groups[mechanism] = []
            mice_groups[mechanism].append(file)
        else:
            single_files.append(file)
    return mice_groups, single_files

# ----------------------------------------------------------------------------
# Main Execution Loop
# ----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deepsurv", action="store_true", help="Only run DeepSurv model")
    args = parser.parse_args()

    from sksurv.util import Surv
    imputed_files = glob.glob("imputed_*.csv")

    # Robust path handling: Check standard project data locations if not found in CWD
    if not imputed_files:
        # Check relative to script location or common root
        standard_data_path = "../../data/imputed/imputed_*.csv"
        imputed_files = glob.glob(standard_data_path)
        if imputed_files:
            print(f"Loading data from: {os.path.dirname(imputed_files[0])}")
        else:
            # Try absolute path based on workspace detection or script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            rel_data_path = os.path.join(script_dir, "..", "..", "data", "imputed", "imputed_*.csv")
            imputed_files = glob.glob(rel_data_path)

    # Filter out unwanted files
    imputed_files = [f for f in imputed_files if 'dataset_MI' not in f]
    if not imputed_files:
        print("No imputed datasets found matching 'imputed_*.csv'.")
        return

    print(f"Found {len(imputed_files)} datasets to process.")
    mice_groups, single_files = group_mice_files(imputed_files)

    performance_records = []
    prediction_records = []
    vimp_records = []

    # Time points for AUC evaluation (days)
    AUC_TIMES = np.array([3.0, 7.0, 14.0])

    # --- PROCESS MICE GROUPS ---
    for mechanism, mice_files in mice_groups.items():
        print(f"\n{'='*70}\nProcessing MICE Group: {mechanism}\n{'='*70}")
        m = len(mice_files)
        all_models = [("RSF", run_rsf), ("XGBoost", run_xgboost_survival),
                      ("GradientBoosting", run_gradient_boosting), ("DeepSurv", run_deepsurv)]
        models_to_run = [("DeepSurv", run_deepsurv)] if args.deepsurv else all_models

        for model_name, model_func in models_to_run:
            print(f"\n[MICE - {model_name}]")
            cv_estimates = {fold: [] for fold in range(10)}
            test_c_estimates = []
            test_ibs_estimates = []
            test_auc_estimates = {3.0: [], 7.0: [], 14.0: []} # Storage for AUCs
            pooled_risk_scores = None

            for i, file_path in enumerate(sorted(mice_files), 1):
                print(f"  Processing imputation {i}/{m}")
                df = pd.read_csv(file_path)
                X_df = prepare_features(df)

                y = Surv.from_dataframe("Status", "Survival_Time", df)
                X = X_df.values.astype(float)

                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=0.10, random_state=42, stratify=y["Status"]
                )

                # DIAGNOSTIC: Check event counts in test set to investigate AUC=1.0 artifact
                n_events_test = np.sum(y_test["Status"])
                if i == 1: # Only print for the first imputation to avoid spam
                    print(f"    [Diagnostic] Test set size: {len(y_test)}, Events: {n_events_test}")

                # CV
                cv_scores = run_cv_evaluation(model_func, X_train, y_train, model_name=model_name)
                for fold_idx, score in enumerate(cv_scores):
                    cv_estimates[fold_idx].append(score)

                # Test
                try:
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    model = model_func(X_train_scaled, y_train)

                    # Risk Scores
                    if model_name == "XGBoost":
                        risk_scores = model.predict(xgb.DMatrix(X_test_scaled))
                    elif model_name == "DeepSurv":
                        risk_scores = model.predict(X_test_scaled.astype('float32')).ravel()
                    else:
                        risk_scores = model.predict(X_test_scaled)

                    # C-index
                    from sksurv.metrics import concordance_index_censored
                    c_index_test = concordance_index_censored(y_test["Status"], y_test["Survival_Time"], risk_scores)[0]
                    test_c_estimates.append(c_index_test)

                    # IBS
                    if hasattr(model, "predict_survival_function"):
                        times = np.percentile(y_test["Survival_Time"], np.linspace(5, 95, 15))
                        surv_funcs = model.predict_survival_function(X_test_scaled)
                        preds = [fn(times) for fn in surv_funcs] if hasattr(surv_funcs[0], "x") else surv_funcs
                        metrics_input = np.array(preds)
                        from sksurv.metrics import integrated_brier_score
                        ibs_score = integrated_brier_score(y_train, y_test, metrics_input, times)
                        test_ibs_estimates.append(ibs_score)

                    # Time-dependent AUC
                    # Need risk scores. For RSF/GB/Cox, higher risk score = higher risk.
                    # cumulative_dynamic_auc returns (auc, mean_auc). We want auc at specific times.
                    try:
                        # VALIDITY CHECK:
                        # To calculate AUC at time t, we need:
                        # 1. t < max(y_train) (for IPCW estimation)
                        # 2. At least one event in y_test <= t (cases)
                        # 3. At least one sample in y_test > t (controls)
                        auc_times_valid = []
                        for t in AUC_TIMES:
                             if t >= y_train["Survival_Time"].max():
                                 continue

                             # Check test set constraints
                             cases = (y_test["Survival_Time"] <= t) & (y_test["Status"] == 1)
                             controls = (y_test["Survival_Time"] > t)

                             if cases.any() and controls.any():
                                 auc_times_valid.append(t)

                        if auc_times_valid:
                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore", RuntimeWarning)
                                from sksurv.metrics import cumulative_dynamic_auc
                                aucs, mean_auc = cumulative_dynamic_auc(y_train, y_test, risk_scores, auc_times_valid)

                            for idx, t in enumerate(auc_times_valid):
                                test_auc_estimates[t].append(aucs[idx])
                        else:
                             # If no valid times, just skip simply
                             pass

                    except Exception as e_auc:
                        print(f"    AUC Failed: {e_auc}")

                    if pooled_risk_scores is None: pooled_risk_scores = np.zeros_like(risk_scores)
                    pooled_risk_scores += risk_scores

                except Exception as e:
                    print(f"    Error in imputation {i}: {e}")

            # Pooling Logic
            # CV Pooling
            for fold_idx in range(10):
                 if len(cv_estimates[fold_idx]) == m:
                     pooled_cv, _, pooled_se, ci_l, ci_u = rubins_pooling(cv_estimates[fold_idx], [0.01]*m, m)
                     performance_records.append({"Imputation": "MICE (pooled)", "Mechanism": mechanism, "Model": model_name, "Metric": "C-index (CV)", "Fold": fold_idx+1, "Value": pooled_cv, "CI_Lower": ci_l, "CI_Upper": ci_u})

            # Test Pooling C-index
            if len(test_c_estimates) == m:
                pooled_c, _, _, ci_l_c, ci_u_c = rubins_pooling(test_c_estimates, [0.01]*m, m)
                performance_records.append({"Imputation": "MICE (pooled)", "Mechanism": mechanism, "Model": model_name, "Metric": "C-index (Test)", "Fold": "Test", "Value": pooled_c, "CI_Lower": ci_l_c, "CI_Upper": ci_u_c})

            # Test Pooling IBS
            if len(test_ibs_estimates) == m:
                pooled_ibs, _, _, ci_l_i, ci_u_i = rubins_pooling(test_ibs_estimates, [0.001]*m, m)
                performance_records.append({"Imputation": "MICE (pooled)", "Mechanism": mechanism, "Model": model_name, "Metric": "IBS (Test)", "Fold": "Test", "Value": pooled_ibs, "CI_Lower": ci_l_i, "CI_Upper": ci_u_i})

            # Test Pooling AUCs
            for t in AUC_TIMES:
                if len(test_auc_estimates[t]) == m:
                    pooled_auc, _, _, ci_l_a, ci_u_a = rubins_pooling(test_auc_estimates[t], [0.01]*m, m)
                    print(f"  Pooled AUC (Day {t}): {pooled_auc:.4f}")
                    performance_records.append({"Imputation": "MICE (pooled)", "Mechanism": mechanism, "Model": model_name, "Metric": f"AUC_Day{int(t)}", "Fold": "Test", "Value": pooled_auc, "CI_Lower": ci_l_a, "CI_Upper": ci_u_a})

            # Save pooled predictions
            if pooled_risk_scores is not None:
                avg_risk_scores = pooled_risk_scores / m
                for idx in range(len(y_test)):
                    prediction_records.append({
                        "Imputation": "MICE (pooled)",
                        "Mechanism": mechanism,
                        "Model": model_name,
                        "Index": idx,
                        "Observed_Time": y_test[idx]["Survival_Time"],
                        "Observed_Status": y_test[idx]["Status"],
                        "Predicted_Risk": avg_risk_scores[idx]
                    })

            # Variable importance for MICE RSF (from last imputation)
            if model_name == "RSF" and model is not None:
                from sklearn.inspection import permutation_importance
                result = permutation_importance(model, X_test_scaled, y_test, n_repeats=5, random_state=42)
                for idx, feature_name in enumerate(X_df.columns):
                    vimp_records.append({
                        "Imputation": "MICE",
                        "Mechanism": mechanism,
                        "Imputation_Idx": m,
                        "Model": "RSF",
                        "Feature": feature_name,
                        "Importance_Mean": result.importances_mean[idx],
                        "Importance_Std": result.importances_std[idx]
                    })

    # --- PROCESS SINGLE IMPUTATIONS ---
    for file_path in single_files:
        base_name = file_path.replace("imputed_", "").replace(".csv", "")
        parts = base_name.split("_")
        imputation_method = parts[0]
        missing_mechanism = "_".join(parts[1:])

        print(f"\nProcessing Single: {imputation_method} - {missing_mechanism}")
        df = pd.read_csv(file_path)
        X_df = prepare_features(df)
        y = Surv.from_dataframe("Status", "Survival_Time", df)
        X = X_df.values.astype(float)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.10, random_state=42, stratify=y["Status"])

        all_models = [("RSF", run_rsf), ("XGBoost", run_xgboost_survival),
                      ("GradientBoosting", run_gradient_boosting), ("DeepSurv", run_deepsurv)]
        models_to_run = [("DeepSurv", run_deepsurv)] if args.deepsurv else all_models

        for model_name, model_func in models_to_run:
            print(f"  [{model_name}]")
            # CV
            cv_scores = run_cv_evaluation(model_func, X_train, y_train, model_name=model_name)
            for i, score in enumerate(cv_scores):
                performance_records.append({"Imputation": imputation_method, "Mechanism": missing_mechanism, "Model": model_name, "Metric": "C-index (CV)", "Fold": i+1, "Value": score})

            # Test
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            try:
                model = model_func(X_train_scaled, y_train)
                if model_name == "XGBoost":
                    import xgboost as xgb
                    risk_scores = model.predict(xgb.DMatrix(X_test_scaled))
                elif model_name == "DeepSurv": risk_scores = model.predict(X_test_scaled.astype('float32')).ravel()
                else: risk_scores = model.predict(X_test_scaled)

                # C-index
                from sksurv.metrics import concordance_index_censored
                c_test = concordance_index_censored(y_test["Status"], y_test["Survival_Time"], risk_scores)[0]
                performance_records.append({"Imputation": imputation_method, "Mechanism": missing_mechanism, "Model": model_name, "Metric": "C-index (Test)", "Fold": "Test", "Value": c_test})

                # Save predictions
                for i in range(len(y_test)):
                    prediction_records.append({
                        "Imputation": imputation_method,
                        "Mechanism": missing_mechanism,
                        "Model": model_name,
                        "Index": i,
                        "Observed_Time": y_test[i]["Survival_Time"],
                        "Observed_Status": y_test[i]["Status"],
                        "Predicted_Risk": risk_scores[i]
                    })

                # --- NEW: EXPORT FOR R SCRIPT (RSF-GAIN PRIMARY) ---
                if model_name == "RSF" and imputation_method == "GAIN":
                    print("    >>> Saving detailed RSF-GAIN predictions for R analysis...")
                    rsf_gain_data = []
                    for i in range(len(y_test)):
                         rsf_gain_data.append({
                             "Observed_Time": y_test[i]["Survival_Time"],
                             "Observed_Status": 1 if y_test[i]["Status"] else 0, # Explicit numeric conversion
                             "Predicted_Risk": risk_scores[i],
                             "Risk_Group": "High" if risk_scores[i] >= np.median(risk_scores) else "Low"
                         })
                    out_filename = f"rsf_gain_predictions_{missing_mechanism}.csv"
                    pd.DataFrame(rsf_gain_data).to_csv(out_filename, index=False)
                    print(f"    >>> Saved: {out_filename}")

                    # Also save Lactate distribution if available
                    if "Lactate" in df.columns:
                        print("    >>> Saving Lactate distribution for Figure B1...")
                        lactate_data = pd.DataFrame({
                            "Lactate_Imputed": df["Lactate"],
                            "Imputation": "GAIN"
                        })
                        lactate_data.to_csv("lactate_gain_distribution.csv", index=False)
                        print("    >>> Saved: lactate_gain_distribution.csv")
                # ---------------------------------------------------

                # Variable importance (RSF only)
                if model_name == "RSF":
                    from sklearn.inspection import permutation_importance
                    result = permutation_importance(model, X_test_scaled, y_test, n_repeats=5, random_state=42)
                    for idx, feature_name in enumerate(X_df.columns):
                        vimp_records.append({
                            "Imputation": imputation_method,
                            "Mechanism": missing_mechanism,
                            "Imputation_Idx": 1,
                            "Model": "RSF",
                            "Feature": feature_name,
                            "Importance_Mean": result.importances_mean[idx],
                            "Importance_Std": result.importances_std[idx]
                        })

                # IBS
                if hasattr(model, "predict_survival_function"):
                    times = np.percentile(y_test["Survival_Time"], np.linspace(5, 95, 15))
                    surv_funcs = model.predict_survival_function(X_test_scaled)
                    preds = [fn(times) for fn in surv_funcs] if hasattr(surv_funcs[0], "x") else surv_funcs
                    metrics_input = np.array(preds)
                    from sksurv.metrics import integrated_brier_score
                    ibs_score = integrated_brier_score(y_train, y_test, metrics_input, times)
                    performance_records.append({"Imputation": imputation_method, "Mechanism": missing_mechanism, "Model": model_name, "Metric": "IBS (Test)", "Fold": "Test", "Value": ibs_score})

                # Time-dependent AUC
                try:
                    # VALIDITY CHECK:
                    auc_times_valid = []
                    for t in AUC_TIMES:
                         if t >= y_train["Survival_Time"].max():
                             continue

                         cases = (y_test["Survival_Time"] <= t) & (y_test["Status"] == 1)
                         controls = (y_test["Survival_Time"] > t)

                         if cases.any() and controls.any():
                             auc_times_valid.append(t)

                    if auc_times_valid:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", RuntimeWarning)
                            from sksurv.metrics import cumulative_dynamic_auc
                            aucs, mean_auc = cumulative_dynamic_auc(y_train, y_test, risk_scores, auc_times_valid)

                        for idx, t in enumerate(auc_times_valid):
                            print(f"    AUC Day {t}: {aucs[idx]:.4f}")
                            performance_records.append({"Imputation": imputation_method, "Mechanism": missing_mechanism, "Model": model_name, "Metric": f"AUC_Day{int(t)}", "Fold": "Test", "Value": aucs[idx]})
                except Exception as e_auc:
                    print(f"    AUC Failed: {e_auc}")

            except Exception as e:
                print(f"    Test Failed: {e}")

    # Summary
    results_df = pd.DataFrame(performance_records)
    if results_df.empty:
        print("\n" + "!"*70)
        print("ERROR: No successful model results were generated.")
        print("Please check the error messages above (e.g., missing dependencies).")
        print("!"*70)
        return

    results_df.to_csv("model_performance_results.csv", index=False)
    print("Saved: model_performance_results.csv")

    # Save predictions
    if prediction_records:
        predictions_df = pd.DataFrame(prediction_records)
        predictions_df.to_csv("model_predictions.csv", index=False)
        print("Saved: model_predictions.csv")
    else:
        print("Warning: No predictions to save")

    # Save variable importance
    if vimp_records:
        vimp_df = pd.DataFrame(vimp_records)
        vimp_df.to_csv("variable_importance.csv", index=False)
        print("Saved: variable_importance.csv")
    else:
        print("Warning: No variable importance to save")

    print("\nGenerating Methodological Summary...")
    summary_list = []
    grouped = results_df.groupby(["Imputation", "Mechanism", "Model", "Metric"])
    for name, group in grouped:
        imp, mech, model, metric = name
        mean_val = group["Value"].mean()
        if "MICE" in imp or "CV" in metric:
            sem = group["Value"].std() / np.sqrt(len(group)) if len(group)>1 else 0
            if "CI_Lower" in group.columns and not group["CI_Lower"].isna().all():
                 ci_low, ci_high = group["CI_Lower"].mean(), group["CI_Upper"].mean()
            else:
                 ci_low, ci_high = mean_val - 1.96*sem, mean_val + 1.96*sem
        else:
            ci_low, ci_high = np.nan, np.nan

        summary_list.append({
            "Imputation": imp, "Mechanism": mech, "Model": model, "Metric": metric,
            "Mean": mean_val, "Formatted": f"{mean_val:.3f} ({ci_low:.3f}-{ci_high:.3f})" if not np.isnan(ci_low) else f"{mean_val:.3f}"
        })

    pd.DataFrame(summary_list).to_csv("model_performance_summary.csv", index=False)
    print("DONE")

if __name__ == "__main__":
    main()