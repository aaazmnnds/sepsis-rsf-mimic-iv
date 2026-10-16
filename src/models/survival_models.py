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
import xgboost

# ... [Keep imports and model definitions RSF to DeepSurv unchanged] ...

# FIX R1.8/R2.5: Imputation inside train/test split boundary
def impute_train_test(X_train_raw, X_test_raw, method="GAIN"):
    """
    Fit imputer on training data only, transform both train and test.
    Prevents data leakage across train/test boundary.
    """
    if method == "GAIN":
        import sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); from missingness.imputation_python import run_gain
        X_train_imputed = run_gain(X_train_raw)
        train_means = np.nanmean(X_train_raw, axis=0)
        X_test_imputed = X_test_raw.copy()
        for col in range(X_test_raw.shape[1]):
            mask = np.isnan(X_test_raw[:, col])
            X_test_imputed[mask, col] = train_means[col]
        return X_train_imputed, X_test_imputed
    elif method == "MIDA":
        from missingness.imputation_python import run_mida
        X_train_imputed = run_mida(X_train_raw)
        train_means = np.nanmean(X_train_raw, axis=0)
        X_test_imputed = X_test_raw.copy()
        for col in range(X_test_raw.shape[1]):
            mask = np.isnan(X_test_raw[:, col])
            X_test_imputed[mask, col] = train_means[col]
        return X_train_imputed, X_test_imputed
    else:
        train_means = np.nanmean(X_train_raw, axis=0)
        X_train_imputed = X_train_raw.copy()
        X_test_imputed = X_test_raw.copy()
        for col in range(X_train_raw.shape[1]):
            mask_train = np.isnan(X_train_raw[:, col])
            mask_test = np.isnan(X_test_raw[:, col])
            X_train_imputed[mask_train, col] = train_means[col]
            X_test_imputed[mask_test, col] = train_means[col]
        return X_train_imputed, X_test_imputed


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
    if params is None:
        params = {
            "objective": "survival:cox",
            "eval_metric": "cox-nloglik",
            "tree_method": "hist",
            "device": "cpu",
            "seed": 42
        }
    y_xgb = np.where(y['Status'], y['Survival_Time'], -y['Survival_Time'])
    dtrain = xgboost.DMatrix(X, label=y_xgb)
    model = xgboost.train(params, dtrain, num_boost_round=100, verbose_eval=False)
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
    import random
    import torchtuples as tt
    from pycox.models import CoxPH
    import torch
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)
    torch.set_num_threads(1) # Prevent deadlocks on Mac
    X = X.astype('float32')
    y_time = y['Survival_Time'].astype('float32')
    y_event = y['Status'].astype('float32')

    # Improved architecture: added dropout to prevent overfitting
    from torch import nn
    net = tt.practical.MLPVanilla(X.shape[1], [32, 32], 1, dropout=0.3)

    model = CoxPH(net, tt.optim.Adam(lr=learning_rate))

    # Reduced epochs from 100 to 50 as per Phase 3 plan
    print("      (DeepSurv Training...)", end="\r")
    model.fit(X, (y_time, y_event), batch_size=256, epochs=50, verbose=False)
    return model

# ----------------------------------------------------------------------------
# Cross-Validation Helper
# ----------------------------------------------------------------------------
def run_cv_evaluation(model_func, X, y, model_name="Model", 
                      n_splits=10, random_state=42, 
                      n_repeats=5, return_oof=False, **kwargs):
    """
    Repeated stratified k-fold cross-validation.
    n_repeats=5 runs 5 independent 10-fold CV iterations
    with different random seeds to assess stability.
    """
    all_fold_scores = []
    repeat_means = []
    oof_predictions = []
    failed_folds_count = 0
    
    for repeat in range(n_repeats):
        repeat_seed = random_state + repeat
        skf = StratifiedKFold(n_splits=n_splits, shuffle=True, 
                              random_state=repeat_seed)
        fold_scores = []
        stratify_label = y["Status"]
        
        for fold_num, (train_idx, val_idx) in enumerate(skf.split(X, stratify_label), 1):
            X_fold_train = X[train_idx]
            X_fold_val = X[val_idx]
            y_fold_train = y[train_idx]
            y_fold_val = y[val_idx]
            
            scaler = StandardScaler()
            X_fold_train_scaled = scaler.fit_transform(X_fold_train)
            X_fold_val_scaled = scaler.transform(X_fold_val)
            
            try:
                model = model_func(X_fold_train_scaled, 
                                   y_fold_train, **kwargs)
                if model_name == "XGBoost":
                    dval = xgboost.DMatrix(X_fold_val_scaled)
                    risk_scores = model.predict(dval)
                elif model_name == "DeepSurv":
                    risk_scores = model.predict(
                        X_fold_val_scaled.astype('float32'))
                    if risk_scores.ndim > 1:
                        risk_scores = risk_scores.ravel()
                else:
                    risk_scores = model.predict(X_fold_val_scaled)
                    
                from sksurv.metrics import concordance_index_censored
                c = concordance_index_censored(
                    y_fold_val["Status"], 
                    y_fold_val["Survival_Time"], 
                    risk_scores)[0]
                fold_scores.append(c)
                all_fold_scores.append(c)

                if return_oof:
                    for p_idx, score in zip(val_idx, risk_scores):
                        oof_predictions.append((repeat, int(p_idx), float(score)))
            except Exception as e:
                failed_folds_count += 1
                print(f"WARNING: Fold evaluation failed - Repeat {repeat+1}, Fold {fold_num}, Val Patients {len(val_idx)}, Error: {e}")
        
        if fold_scores:
            repeat_mean = np.mean(fold_scores)
            repeat_means.append(repeat_mean)
            print(f"    Repeat {repeat+1}/{n_repeats} Mean: "
                  f"{repeat_mean:.4f} (+/- {np.std(fold_scores):.4f})")
    
    overall_mean = np.mean(all_fold_scores) if all_fold_scores else 0
    overall_std = np.std(all_fold_scores) if all_fold_scores else 0
    print(f"    Overall Mean CV C-index ({n_repeats}x{n_splits}-fold): "
          f"{overall_mean:.4f} (+/- {overall_std:.4f})")
    
    if return_oof:
        return all_fold_scores, repeat_means, oof_predictions, failed_folds_count
    return all_fold_scores, repeat_means

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
    # Standardize column names for synthetic data compatibility
    if "Time" in df.columns: df.rename(columns={"Time": "Survival_Time"}, inplace=True)
    if "Event" in df.columns: df.rename(columns={"Event": "Status"}, inplace=True)
    
    EXCLUDE = ['Survival_Time', 'Status', 'subject_id', 'hadm_id']
    X_df = df.drop(columns=[c for c in EXCLUDE if c in df.columns])
    X_df = pd.get_dummies(X_df, drop_first=True)
    return X_df

def group_mice_files(files):
    mice_groups = {}
    single_files = []
    for file in files:
        fname = os.path.basename(file)
        match = re.match(r'mice(\d+)_(.+)\.csv', fname)
        if match:
            mechanism = match.group(2)
            if mechanism not in mice_groups: mice_groups[mechanism] = []
            mice_groups[mechanism].append(file)
        else:
            single_files.append(file)
    return mice_groups, single_files

# ----------------------------------------------------------------------------
# Checkpoint Helpers
# ----------------------------------------------------------------------------
def norm_rate(r):
    try: return str(float(r))
    except: return str(r)

def is_already_processed(checkpoint_file, imputation, mechanism, rate, model):
    """Check if this combination exists in checkpoint file."""
    if not os.path.exists(checkpoint_file):
        return False
    try:
        df = pd.read_csv(checkpoint_file)
        mask = (
            (df["Imputation"] == imputation) &
            (df["Mechanism"] == mechanism) &
            (df["Missingness_Rate"].apply(norm_rate) == norm_rate(rate)) &
            (df["Model"] == model)
        )
        return mask.any()
    except Exception:
        return False

def save_checkpoint(checkpoint_file, new_records):
    """Append new records to checkpoint file."""
    if not new_records:
        return
    new_df = pd.DataFrame(new_records)
    if os.path.exists(checkpoint_file):
        try:
            existing_df = pd.read_csv(checkpoint_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        except Exception:
            combined_df = new_df
    else:
        combined_df = new_df
    combined_df.to_csv(checkpoint_file, index=False)
    print(f"Checkpoint saved: {len(combined_df)} total records")

# ----------------------------------------------------------------------------
# Main Execution Loop
# ----------------------------------------------------------------------------
def main():
    # Absolute Root Configuration
    ROOT_DIR = "/Users/nazu.ds/Documents/Research Collections/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
    RESULTS_DIR = os.path.join(ROOT_DIR, "Results sensitivity")
    checkpoint_file = os.path.join(RESULTS_DIR, "model_performance_sensitivity_analysis.csv")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--deepsurv", action="store_true", help="Only run DeepSurv model")
    parser.add_argument("--skip-deepsurv", action="store_true", help="Skip DeepSurv model")
    parser.add_argument("--rates", nargs="+", help="Specific missingness rates to process (e.g., 10 40 55)")
    args = parser.parse_args()

    from sksurv.util import Surv
    imputed_files = glob.glob(os.path.join(ROOT_DIR, "Results sensitivity", "*.csv"))

    # Filter by rates if specified
    if args.rates:
        print(f"Filtering for specific rates: {args.rates}")
        filtered_files = []
        for f in imputed_files:
            # Match _rate.csv or _rate_ (for MICE numbering)
            if any(f"_{rate}.csv" in f or f"_{rate}_" in f for rate in args.rates):
                filtered_files.append(f)
        imputed_files = filtered_files
        imputed_files.sort() # Sort for consistent processing order (10 -> 40 -> 55)
        print(f"Files remaining after filtering: {len(imputed_files)}")

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

    # Filter out unwanted files (raw synthetic and other MI artifacts)
    imputed_files = [f for f in imputed_files if 'dataset_MI' not in f and not os.path.basename(f).startswith('synthetic_') and not os.path.basename(f).startswith('model_') and not os.path.basename(f).startswith('variable_') and not os.path.basename(f).startswith('sensitivity_') and not os.path.basename(f).startswith('statistical_')]
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
    for mechanism, mice_files in sorted(mice_groups.items()):
        print(f"\n{'='*70}\nProcessing MICE Group: {mechanism}\n{'='*70}")
        m = len(mice_files)
        all_models = [("RSF", run_rsf), ("XGBoost", run_xgboost_survival),
                      ("GradientBoosting", run_gradient_boosting), ("DeepSurv", run_deepsurv)]
        if args.deepsurv:
            models_to_run = [("DeepSurv", run_deepsurv)]
        elif args.skip_deepsurv:
            models_to_run = [m for m in all_models if m[0] != "DeepSurv"]
        else:
            models_to_run = all_models

        # Parse mechanism and rate (e.g., mcar_10)
        mech_parts = mechanism.split("_")
        mech_label = mech_parts[0].upper()
        rate_label = norm_rate(mech_parts[1]) if len(mech_parts) > 1 else "26.8"

        for model_name, model_func in models_to_run:
            if is_already_processed(checkpoint_file, "MICE (pooled)", mech_label, rate_label, model_name):
                print(f"  [MICE - {model_name}] Already processed - skipping")
                continue

            print(f"\n[MICE - {model_name}]")
            cv_estimates = {fold: [] for fold in range(10)}
            cv_repeat_stability = {}
            test_c_estimates = []
            test_ibs_estimates = []
            test_auc_estimates = {3.0: [], 7.0: [], 14.0: []} # Storage for AUCs
            pooled_risk_scores = None
            mice_oof_imputations = []

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
                is_real_data = ("mimic" in mechanism.lower() or mechanism.lower() == "full")
                if is_real_data:
                    all_fold_scores, repeat_means, oof_predictions, failed_folds = run_cv_evaluation(
                        model_func, X_train, y_train, 
                        model_name=model_name, n_repeats=5, return_oof=is_real_data)
                    if failed_folds > 0:
                        print(f"WARNING: {failed_folds} fold(s) failed in MICE imputation {i} for {model_name}.")
                    oof_mat = np.zeros((5, len(y_train)))
                    for r, p_idx, score in oof_predictions:
                        oof_mat[r, p_idx] = score
                    mice_oof_imputations.append((oof_mat, failed_folds))
                else:
                    all_fold_scores, repeat_means = run_cv_evaluation(
                        model_func, X_train, y_train, 
                        model_name=model_name, n_repeats=5, return_oof=is_real_data)
                # Use all fold scores for Rubin pooling
                for fold_idx, score in enumerate(all_fold_scores[:10]):
                    cv_estimates[fold_idx].append(score)
                # Store repeat stability
                cv_repeat_stability[i] = np.std(repeat_means) if repeat_means else 0

                # Test
                try:
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)
                    model = model_func(X_train_scaled, y_train)

                    # Risk Scores
                    if model_name == "XGBoost":
                        risk_scores = model.predict(xgboost.DMatrix(X_test_scaled))
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
                     # Parse mechanism and rate (e.g., mcar_10)
                     mech_parts = mechanism.split("_")
                     mech_label = mech_parts[0].upper()
                     rate_label = norm_rate(mech_parts[1]) if len(mech_parts) > 1 else "26.8"
                     
                     performance_records.append({
                         "Imputation": "MICE (pooled)", 
                         "Mechanism": mech_label, 
                         "Missingness_Rate": rate_label,
                         "Model": model_name, 
                         "Metric": "C-index (CV)", 
                         "Fold": fold_idx+1, 
                         "Value": pooled_cv, 
                         "CI_Lower": ci_l, 
                         "CI_Upper": ci_u
                     })

            # Test Pooling C-index
            if len(test_c_estimates) == m:
                pooled_c, _, _, ci_l_c, ci_u_c = rubins_pooling(test_c_estimates, [0.01]*m, m)
                performance_records.append({
                    "Imputation": "MICE (pooled)", 
                    "Mechanism": mech_label, 
                    "Missingness_Rate": rate_label,
                    "Model": model_name, 
                    "Metric": "C-index (Test)", 
                    "Fold": "Test", 
                    "Value": pooled_c, 
                    "CI_Lower": ci_l_c, 
                    "CI_Upper": ci_u_c
                })

            # Test Pooling IBS
            if len(test_ibs_estimates) == m:
                pooled_ibs, _, _, ci_l_i, ci_u_i = rubins_pooling(test_ibs_estimates, [0.001]*m, m)
                performance_records.append({
                    "Imputation": "MICE (pooled)", 
                    "Mechanism": mech_label, 
                    "Missingness_Rate": rate_label,
                    "Model": model_name, 
                    "Metric": "IBS (Test)", 
                    "Fold": "Test", 
                    "Value": pooled_ibs, 
                    "CI_Lower": ci_l_i, 
                    "CI_Upper": ci_u_i
                })

            # Test Pooling AUCs
            for t in AUC_TIMES:
                if len(test_auc_estimates[t]) == m:
                    pooled_auc, _, _, ci_l_a, ci_u_a = rubins_pooling(test_auc_estimates[t], [0.01]*m, m)
                    performance_records.append({
                        "Imputation": "MICE (pooled)", 
                        "Mechanism": mech_label, 
                        "Missingness_Rate": rate_label,
                        "Model": model_name, 
                        "Metric": f"AUC_Day{int(t)}", 
                        "Fold": "Test", 
                        "Value": pooled_auc, 
                        "CI_Lower": ci_l_a, 
                        "CI_Upper": ci_u_a
                    })

            # Checkpoint saving for MICE combination
            current_mice_records = [r for r in performance_records if r["Imputation"] == "MICE (pooled)" and r["Mechanism"] == mech_label and norm_rate(r["Missingness_Rate"]) == norm_rate(rate_label) and r["Model"] == model_name]
            save_checkpoint(checkpoint_file, current_mice_records)

            # Save pooled predictions (real data only)
            if pooled_risk_scores is not None and mechanism.lower() == "full":
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
    for file_path in sorted(single_files):
        base_name = os.path.basename(file_path).replace(".csv", "")
        parts = base_name.split("_")
        imputation_method = parts[0]
        missing_mechanism = "_".join(parts[1:])

        print(f"\nProcessing Single: {imputation_method} - {missing_mechanism}")
        # FIX R1.8/R2.5: Isolate GAIN and MIDA imputation within 
        # train/test split to prevent data leakage
        if imputation_method in ["GAIN", "MIDA"]:
            base_name = os.path.basename(file_path)
            if "mimic" in base_name.lower():
                raw_file = os.path.join(ROOT_DIR, "data", "raw", "mimic_sepsis_cohort_full.csv")
                if not os.path.exists(raw_file):
                    raw_file = os.path.join(ROOT_DIR, "mimic_sepsis_cohort_full.csv")
            else:
                raw_file = file_path.replace(f"{imputation_method}_", "synthetic_")
            df_raw = pd.read_csv(raw_file)
            X_df_raw = prepare_features(df_raw)
            y = Surv.from_dataframe("Status", "Survival_Time", df_raw)
            X_raw = X_df_raw.values.astype(float)
            X_train_raw, X_test_raw, y_train, y_test = train_test_split(
                X_raw, y, test_size=0.10, random_state=42, stratify=y["Status"]
            )
            X_train, X_test = impute_train_test(
                X_train_raw, X_test_raw, method=imputation_method
            )
        else:
            df = pd.read_csv(file_path)
            X_df = prepare_features(df)
            y = Surv.from_dataframe("Status", "Survival_Time", df)
            X = X_df.values.astype(float)
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.10, random_state=42, stratify=y["Status"]
            )

        all_models = [("RSF", run_rsf), ("XGBoost", run_xgboost_survival),
                      ("GradientBoosting", run_gradient_boosting), ("DeepSurv", run_deepsurv)]
        if args.deepsurv:
            models_to_run = [("DeepSurv", run_deepsurv)]
        elif args.skip_deepsurv:
            models_to_run = [m for m in all_models if m[0] != "DeepSurv"]
        else:
            models_to_run = all_models

        # Parse mechanism and rate (e.g., mcar_10 or mcar)
        mech_parts = missing_mechanism.split("_")
        mech_label = mech_parts[0].upper()
        rate_label = norm_rate(mech_parts[1]) if len(mech_parts) > 1 else "26.8"

        for model_name, model_func in models_to_run:
            if is_already_processed(checkpoint_file, imputation_method, mech_label, rate_label, model_name):
                print(f"  [{model_name}] Already processed - skipping")
                continue
            print(f"  [{model_name}]")
            # CV
            is_real_data = ("mimic" in missing_mechanism.lower() or missing_mechanism.lower() == "full")
            if is_real_data:
                all_fold_scores, repeat_means, oof_predictions, failed_folds = run_cv_evaluation(
                    model_func, X_train, y_train,
                    model_name=model_name, n_repeats=5, return_oof=is_real_data)
                if failed_folds > 0:
                    print(f"WARNING: {failed_folds} fold(s) failed in {imputation_method} for {model_name}.")
                oof_mat = np.zeros((5, len(y_train)))
                for r, p_idx, score in oof_predictions:
                    oof_mat[r, p_idx] = score
            else:
                all_fold_scores, repeat_means = run_cv_evaluation(
                    model_func, X_train, y_train,
                    model_name=model_name, n_repeats=5, return_oof=is_real_data)
                
            # Record overall CV performance
            performance_records.append({
                "Imputation": imputation_method,
                "Mechanism": mech_label,
                "Missingness_Rate": rate_label,
                "Model": model_name,
                "Metric": "C-index (CV)",
                "Fold": "All",
                "Value": np.mean(all_fold_scores),
                "CV_SD": np.std(all_fold_scores),
                "Repeat_SD": np.std(repeat_means) if repeat_means else 0,
                "CI_Lower": np.mean(all_fold_scores) - 1.96*np.std(all_fold_scores),
                "CI_Upper": np.mean(all_fold_scores) + 1.96*np.std(all_fold_scores)
            })

            # Also record per-repeat means for stability plot
            for r_idx, r_mean in enumerate(repeat_means):
                performance_records.append({
                    "Imputation": imputation_method,
                    "Mechanism": mech_label,
                    "Missingness_Rate": rate_label,
                    "Model": model_name,
                    "Metric": "C-index (CV-Repeat)",
                    "Fold": f"Repeat_{r_idx+1}",
                    "Value": r_mean,
                    "CV_SD": np.nan,
                    "Repeat_SD": np.nan,
                    "CI_Lower": np.nan,
                    "CI_Upper": np.nan
                })

            # Test
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            try:
                model = model_func(X_train_scaled, y_train)
                if model_name == "XGBoost":
                    risk_scores = model.predict(xgboost.DMatrix(X_test_scaled))
                elif model_name == "DeepSurv": risk_scores = model.predict(X_test_scaled.astype('float32')).ravel()
                else: risk_scores = model.predict(X_test_scaled)

                # C-index
                from sksurv.metrics import concordance_index_censored
                c_test = concordance_index_censored(y_test["Status"], y_test["Survival_Time"], risk_scores)[0]
                performance_records.append({
                    "Imputation": imputation_method, 
                    "Mechanism": mech_label, 
                    "Missingness_Rate": rate_label,
                    "Model": model_name, 
                    "Metric": "C-index (Test)", 
                    "Fold": "Test", 
                    "Value": c_test
                })

                # Save predictions for bootstrap comparison
                if "mimic" in missing_mechanism.lower() or missing_mechanism == "full":
                    for idx in range(len(y_test)):
                        prediction_records.append({
                            "Imputation": imputation_method,
                            "Mechanism": missing_mechanism,
                            "Model": model_name,
                            "Index": idx,
                            "Observed_Time": y_test[idx]["Survival_Time"],
                            "Observed_Status": y_test[idx]["Status"],
                            "Predicted_Risk": risk_scores[idx]
                        })

                # IBS
                if hasattr(model, "predict_survival_function"):
                    times = np.percentile(y_test["Survival_Time"], np.linspace(5, 95, 15))
                    surv_funcs = model.predict_survival_function(X_test_scaled)
                    preds = [fn(times) for fn in surv_funcs] if hasattr(surv_funcs[0], "x") else surv_funcs
                    metrics_input = np.array(preds)
                    from sksurv.metrics import integrated_brier_score
                    ibs_score = integrated_brier_score(y_train, y_test, metrics_input, times)
                    performance_records.append({
                        "Imputation": imputation_method, 
                        "Mechanism": mech_label, 
                        "Missingness_Rate": rate_label,
                        "Model": model_name, 
                        "Metric": "IBS (Test)", 
                        "Fold": "Test", 
                        "Value": ibs_score
                    })

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
                            performance_records.append({
                                "Imputation": imputation_method, 
                                "Mechanism": mech_label, 
                                "Missingness_Rate": rate_label,
                                "Model": model_name, 
                                "Metric": f"AUC_Day{int(t)}", 
                                "Fold": "Test", 
                                "Value": aucs[idx]
                            })
                except Exception as e_auc:
                    print(f"    AUC Failed: {e_auc}")

            except Exception as e:
                print(f"    Test Failed: {e}")

            # Checkpoint saving for single file combination
            current_single_records = [r for r in performance_records if r["Imputation"] == imputation_method and r["Mechanism"] == mech_label and norm_rate(r["Missingness_Rate"]) == norm_rate(rate_label) and r["Model"] == model_name]
            save_checkpoint(checkpoint_file, current_single_records)

    # Summary
    # Summary
    if os.path.exists(checkpoint_file):
        results_df = pd.read_csv(checkpoint_file)
    else:
        results_df = pd.DataFrame(performance_records)

    if results_df.empty:
        print("\n" + "!"*70)
        print("ERROR: No successful model results were generated.")
        print("Please check the error messages above (e.g., missing dependencies).")
        print("!"*70)
        return

    # Deduplicate in case of resume overlaps
    results_df = results_df.drop_duplicates()
    results_df.to_csv(checkpoint_file, index=False)
    print(f"Successfully finalized {len(results_df)} total result rows.")
    print(f"Saved: {checkpoint_file}")

    # Save predictions (merge on resume and clean synthetic MICE)
    predictions_path = os.path.join(RESULTS_DIR, "model_predictions.csv")
    new_pred_df = pd.DataFrame(prediction_records) if prediction_records else pd.DataFrame()
    if os.path.exists(predictions_path):
        existing_pred_df = pd.read_csv(predictions_path)
        combined_pred_df = pd.concat([existing_pred_df, new_pred_df], ignore_index=True) if not new_pred_df.empty else existing_pred_df
    else:
        combined_pred_df = new_pred_df

    if not combined_pred_df.empty:
        # Drop synthetic MICE rows
        synthetic_mice_mask = (combined_pred_df["Imputation"] == "MICE (pooled)") & (combined_pred_df["Mechanism"].str.lower() != "full")
        combined_pred_df = combined_pred_df[~synthetic_mice_mask]
        combined_pred_df = combined_pred_df.drop_duplicates(subset=["Imputation", "Mechanism", "Model", "Index"])
        combined_pred_df.to_csv(predictions_path, index=False)
        print(f"Saved: {predictions_path}")
    else:
        print("Warning: No predictions to save")

    # Save variable importance (merge on resume)
    vimp_path = os.path.join(RESULTS_DIR, "variable_importance.csv")
    new_vimp_df = pd.DataFrame(vimp_records) if vimp_records else pd.DataFrame()
    if os.path.exists(vimp_path):
        existing_vimp_df = pd.read_csv(vimp_path)
        combined_vimp_df = pd.concat([existing_vimp_df, new_vimp_df], ignore_index=True) if not new_vimp_df.empty else existing_vimp_df
    else:
        combined_vimp_df = new_vimp_df

    if not combined_vimp_df.empty:
        combined_vimp_df = combined_vimp_df.drop_duplicates(subset=["Imputation", "Mechanism", "Imputation_Idx", "Model", "Feature"])
        combined_vimp_df.to_csv(vimp_path, index=False)
        print(f"Saved: {vimp_path}")
    else:
        print("Warning: No variable importance to save")

    print("\nGenerating Methodological Summary...")
    summary_list = []
    grouped = results_df.groupby(["Imputation", "Mechanism", "Missingness_Rate", "Model", "Metric"])
    for name, group in grouped:
        imp, mech, rate, model, metric = name
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
            "Imputation": imp, "Mechanism": mech, "Missingness_Rate": rate, "Model": model, "Metric": metric,
            "Mean": mean_val, "Formatted": f"{mean_val:.3f} ({ci_low:.3f}-{ci_high:.3f})" if not np.isnan(ci_low) else f"{mean_val:.3f}"
        })

    summary_df = pd.DataFrame(summary_list)
    summary_path = os.path.join(RESULTS_DIR, "model_performance_summary_sensitivity.csv")
    summary_df.to_csv(summary_path, index=False)
    print(f"Summary generated for {len(summary_df)} model-mechanism-rate combinations.")
    print(f"Saved summary: {summary_path}")
    print("DONE")

if __name__ == "__main__":
    main()