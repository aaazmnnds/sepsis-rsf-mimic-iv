import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob

def plot_performance_comparison():
    print("Generating Performance Comparison Plot...")

    if not glob.glob("model_performance_sensitivity_analysis.csv"):
        print("Error: 'model_performance_sensitivity_analysis.csv' not found.")
        return

    df = pd.read_csv("model_performance_sensitivity_analysis.csv")
    df_plot = df[df["Mechanism"].isin(["FULL", "MIMIC"]) & (df["Metric"] == "C-index (CV-Pooled)")].copy()
    df_plot["Imputation"] = df_plot["Imputation"].replace({"MICE (pooled)": "MICE"})

    imputation_order = ["MICE", "missForest", "GAIN", "MIDA"]
    model_order = ["RSF", "XGBoost", "GradientBoosting", "DeepSurv", "CoxnetElasticNet", "CoxnetRidge"]
    legend_labels = ["RSF", "XGBoost", "Gradient Boosting", "DeepSurv", "Elastic-net Cox", "Ridge Cox"]

    n_groups = len(imputation_order)
    n_models = len(model_order)
    bar_width = 0.13
    indices = np.arange(n_groups)

    fig, ax = plt.subplots(figsize=(14, 7))
    palette = sns.color_palette("tab10", n_models)

    for i, (model_name, label) in enumerate(zip(model_order, legend_labels)):
        model_df = df_plot[df_plot["Model"] == model_name].set_index("Imputation").reindex(imputation_order).reset_index()
        values = model_df["Value"].values
        ci_lower = model_df["CI_Lower"].values
        ci_upper = model_df["CI_Upper"].values

        yerr_lower = values - ci_lower
        yerr_upper = ci_upper - values
        yerr = np.array([yerr_lower, yerr_upper])

        offsets = indices + (i - (n_models - 1) / 2) * bar_width
        bars = ax.bar(offsets, values, bar_width, label=label, color=palette[i],
                      yerr=yerr, capsize=3, error_kw={"elinewidth": 1, "capthick": 1})

        for bar, val in zip(bars, values):
            if not np.isnan(val):
                ax.text(bar.get_x() + bar.get_width() / 2, val + 0.005, f"{val:.3f}",
                        ha="center", va="bottom", fontsize=7, rotation=0)

    ax.set_ylim(0.5, 0.95)
    ax.set_ylabel("Pooled out-of-fold C-index (95% bootstrap CI)", fontsize=12)
    ax.set_xlabel("Imputation method", fontsize=12)
    ax.set_title("Pooled out-of-fold C-index, real MIMIC-IV data", fontsize=14)
    ax.set_xticks(indices)
    ax.set_xticklabels(imputation_order, fontsize=11)
    ax.legend(title="Model", loc="upper right", fontsize=8, title_fontsize=9, borderpad=0.3, labelspacing=0.3, handletextpad=0.4, handlelength=1.2)

    plt.tight_layout()
    plt.savefig("performance_comparison.png", dpi=300)
    print("Saved 'performance_comparison.png'")


def plot_auc_time_dependent():
    print("Generating Time-dependent AUC Plot...")

    if not glob.glob("model_performance_results.csv"):
        print("Error: 'model_performance_results.csv' not found.")
        return

    df = pd.read_csv("model_performance_results.csv")

    # Filter for AUC metrics
    # Metrics are saved as "AUC_Day3", "AUC_Day7", "AUC_Day14"
    df_auc = df[df["Metric"].str.startswith("AUC_Day")]

    if df_auc.empty:
        print("No Time-dependent AUC results found.")
        return

    # Extract Day Number for sorting/plotting
    df_auc["Day"] = df_auc["Metric"].apply(lambda x: int(x.replace("AUC_Day", "")))
    df_auc = df_auc.sort_values("Day")

    plt.figure(figsize=(12, 6))
    sns.set_style("whitegrid")

    # Plot: x=Day, y=Value, hue=Model (Aggregated across imputations or specific one?)
    # Let's show average performance across imputations for each Model at each Time
    sns.lineplot(data=df_auc, x="Day", y="Value", hue="Model", style="Model", markers=True, dashes=False, palette="viridis", err_style="bars", errorbar=("ci", 95))

    plt.title("Time-dependent AUC (Discrimination Stability)", fontsize=14)
    plt.ylabel("Time-dependent AUC", fontsize=12)
    plt.xlabel("Time (Days)", fontsize=12)
    plt.ylim(0.5, 1.0)
    plt.xticks([3, 7, 14])
    plt.legend(title="Model", loc="lower right")

    plt.tight_layout()
    plt.savefig("auc_time_dependent.png", dpi=300)
    print("Saved 'auc_time_dependent.png'")


def plot_calibration_curves():
    print("Generating Calibration Curves...")

    if not glob.glob("model_predictions.csv"):
        print("Error: 'model_predictions.csv' not found. Run survival_models.py first.")
        return

    from sksurv.nonparametric import kaplan_meier_estimator

    df_preds = pd.read_csv("model_predictions.csv")
    df_s30 = df_preds[df_preds["Model"] == "RSF_OOF_S30"].copy()

    if df_s30.empty:
        print("Error: No predictions found for Model == 'RSF_OOF_S30'.")
        return

    imputation_panels = [
        ("MICE (pooled)", "MICE"),
        ("missForest", "missForest"),
        ("GAIN", "GAIN"),
        ("MIDA", "MIDA")
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharex=True, sharey=True)
    sns.set_style("whitegrid")

    for idx, (imp_name, panel_title) in enumerate(imputation_panels):
        ax = axes[idx // 2, idx % 2]
        df_imp = df_s30[df_s30["Imputation"] == imp_name].copy()

        if len(df_imp) != 766:
            print(f"Warning: Expected 766 rows for '{imp_name}', found {len(df_imp)} rows.")

        print(f"\n--- Calibration Group Values: {panel_title} ({imp_name}) ---")

        if df_imp.empty:
            ax.set_title(panel_title, fontsize=13, fontweight="bold")
            continue

        # Split patients into 5 quantile groups of predicted survival
        df_imp["Quantile_Group"] = pd.qcut(df_imp["Predicted_Risk"], q=5, labels=False, duplicates="drop")

        pred_means = []
        obs_kms = []
        err_lowers = []
        err_uppers = []

        for q_idx in sorted(df_imp["Quantile_Group"].unique()):
            grp_df = df_imp[df_imp["Quantile_Group"] == q_idx]
            x_mean = float(grp_df["Predicted_Risk"].mean())

            event = grp_df["Observed_Status"].values.astype(bool)
            time = grp_df["Observed_Time"].values.astype(float)

            try:
                res = kaplan_meier_estimator(event, time, conf_type="log-log")
                if len(res) == 3:
                    km_times, km_probs, conf_int = res
                else:
                    km_times, km_probs = res
                    conf_int = None
            except Exception:
                km_times, km_probs = kaplan_meier_estimator(event, time)
                conf_int = None

            if len(km_times) == 0 or 30.0 < km_times[0]:
                y_km = 1.0
                ci_l = 1.0
                ci_u = 1.0
            elif 30.0 >= km_times[-1]:
                y_km = float(km_probs[-1])
                ci_l = float(conf_int[0][-1]) if conf_int is not None else np.nan
                ci_u = float(conf_int[1][-1]) if conf_int is not None else np.nan
            else:
                idx_30 = np.where(km_times <= 30.0)[0][-1]
                y_km = float(km_probs[idx_30])
                ci_l = float(conf_int[0][idx_30]) if conf_int is not None else np.nan
                ci_u = float(conf_int[1][idx_30]) if conf_int is not None else np.nan

            pred_means.append(x_mean)
            obs_kms.append(y_km)

            if not np.isnan(ci_l) and not np.isnan(ci_u):
                err_lower = max(0.0, y_km - ci_l)
                err_upper = max(0.0, ci_u - y_km)
                err_lowers.append(err_lower)
                err_uppers.append(err_upper)
                print(f"Group {q_idx + 1}: n={len(grp_df)}, Predicted={x_mean:.4f}, Observed KM={y_km:.4f} (95% CI: {ci_l:.4f} - {ci_u:.4f})")
            else:
                err_lowers.append(0.0)
                err_uppers.append(0.0)
                print(f"Group {q_idx + 1}: n={len(grp_df)}, Predicted={x_mean:.4f}, Observed KM={y_km:.4f} (No CI)")

        # Plot dashed y=x line
        ax.plot([0.5, 1.0], [0.5, 1.0], "k--", alpha=0.7, label="Ideal")

        # Plot points with error bars
        has_ci = any(l > 0 or u > 0 for l, u in zip(err_lowers, err_uppers))
        if has_ci:
            yerr = [err_lowers, err_uppers]
            ax.errorbar(pred_means, obs_kms, yerr=yerr, fmt="o", color="#1f77b4", ecolor="gray", elinewidth=1.2, capsize=3, markersize=6, label="RSF quantile groups")
        else:
            ax.plot(pred_means, obs_kms, "o", color="#1f77b4", markersize=6, label="RSF quantile groups")

        ax.set_title(panel_title, fontsize=13, fontweight="bold")
        ax.set_xlim(0.5, 1.0)
        ax.set_ylim(0.5, 1.0)
        ax.legend(loc="lower right", fontsize=9)

    for i in range(2):
        axes[1, i].set_xlabel("Predicted 30-day survival (mean per group)", fontsize=11)
        axes[i, 0].set_ylabel("Observed 30-day survival (Kaplan-Meier)", fontsize=11)

    plt.tight_layout()
    plt.savefig("calibration_curve_proxy.png", dpi=300, bbox_inches="tight")
    print("Saved 'calibration_curve_proxy.png'")


def plot_variable_importance():
    print("Generating Variable Importance Plot...")

    if not glob.glob("variable_importance.csv"):
        print("Error: 'variable_importance.csv' not found. Run survival_models.py first.")
        return

    df = pd.read_csv("variable_importance.csv")

    # Filter for RSF and real data mechanisms (matches "full" and "mimic_sepsis_cohort_full")
    df_filtered = df[(df["Model"] == "RSF") & (df["Mechanism"].str.lower().str.contains("full"))].copy()

    if df_filtered.empty:
        print("No variable importance records found for RSF under Mechanism matching 'full'.")
        return

    # Order features by mean of Importance_Mean across the four imputations descending (largest at top)
    mean_imp = df_filtered.groupby("Feature")["Importance_Mean"].mean()
    features_ordered = mean_imp.sort_values(ascending=False).index.tolist()

    # Imputation methods in order
    imputations = ["MICE", "missForest", "GAIN", "MIDA"]
    colors = ["#4C72B0", "#55A868", "#C44E52", "#8172B3"]

    n_features = len(features_ordered)
    n_imputations = len(imputations)
    y_pos = np.arange(n_features)
    bar_height = 0.8 / n_imputations

    plt.figure(figsize=(10, 8))
    sns.set_style("whitegrid")

    # Grouped horizontal bars with one bar per imputation per feature
    for i, imp in enumerate(imputations):
        imp_data = df_filtered[df_filtered["Imputation"] == imp].set_index("Feature")
        means = [imp_data.loc[f, "Importance_Mean"] if f in imp_data.index else np.nan for f in features_ordered]
        stds = [imp_data.loc[f, "Importance_Std"] if f in imp_data.index else 0 for f in features_ordered]

        offset = (i - (n_imputations - 1) / 2) * bar_height
        plt.barh(y_pos + offset, means, height=bar_height, xerr=stds, capsize=3,
                 label=imp, color=colors[i % len(colors)], edgecolor="black", alpha=0.85)

    plt.axvline(x=0, color="black", linestyle="--", linewidth=1)

    plt.yticks(y_pos, features_ordered, fontsize=11)
    plt.gca().invert_yaxis()  # Largest mean at the top

    plt.xlabel("Mean decrease in C-index (permutation importance)", fontsize=12)
    plt.ylabel("Feature", fontsize=12)
    plt.title("Permutation importance, RSF (real MIMIC-IV data)", fontsize=14)
    plt.legend(title="Imputation method", fontsize=10, title_fontsize=11)

    plt.tight_layout()
    plt.savefig("variable_importance.png", dpi=300)
    print("Saved 'variable_importance.png'")


from sksurv.nonparametric import kaplan_meier_estimator

def plot_survival_curves():
    print("Generating Survival Curves (KM)...")

    if not glob.glob("model_predictions.csv"):
        print("Error: 'model_predictions.csv' not found. Run survival_models.py first.")
        return

    df = pd.read_csv("model_predictions.csv")

    # Filter for RSF on Real Data (Mechanism='full') using GAIN imputation (Best Model)
    # If GAIN not found, try others.

    target_imputation = "GAIN"
    target_mechanism = "full"
    target_model = "RSF"

    df_subset = df[
        (df["Imputation"] == target_imputation) &
        (df["Mechanism"] == target_mechanism) &
        (df["Model"] == target_model)
    ]

    if df_subset.empty:
        print(f"No predictions found for {target_model} with {target_imputation} on {target_mechanism} data.")
        # Fallback to any RSF full
        df_test_data = df[(df["Mechanism"] == "full") & (df["Model"] == "RSF")]
        if df_test_data.empty:
             print("No RSF predictions on full data found.")
             print(f"Available combinations: {df[['Model', 'Imputation', 'Mechanism']].drop_duplicates()}")
             return
        print(f"Falling back to available RSF full data (Imputation: {df_test_data['Imputation'].unique()[0]})")
        df_subset = df_test_data

    # Median Split
    median_risk = df_subset["Predicted_Risk"].median()
    df_subset["Risk_Group"] = np.where(df_subset["Predicted_Risk"] >= median_risk, "High Risk", "Low Risk")

    plt.figure(figsize=(10, 8))
    sns.set_style("whitegrid")

    # Function to plot with CI using sksurv
    def plot_km_sksurv(data, label, color):
        mask = data["Risk_Group"] == label
        if not mask.any():
            return

        events = data.loc[mask, "Observed_Status"].astype(bool)
        times = data.loc[mask, "Observed_Time"]

        # Calculate KM estimate with 95% Confidence Intervals
        try:
             time_treatment, survival_prob_treatment, conf_int = kaplan_meier_estimator(
                events, times, conf_type="log-log"
            )
             # Plot survival curve
             plt.step(time_treatment, survival_prob_treatment, where="post", color=color, label=label)
             # Plot confidence intervals
             plt.fill_between(time_treatment, conf_int[0], conf_int[1], alpha=0.25, step="post", color=color)
        except Exception as e:
            # Fallback for older scikit-survival versions without conf_type
            print(f"Warning: Could not calculate CI for {label} ({str(e)}). Plotting mean only.")
            time_treatment, survival_prob_treatment = kaplan_meier_estimator(events, times)
            plt.step(time_treatment, survival_prob_treatment, where="post", color=color, label=label)

    # Plot High Risk
    plot_km_sksurv(df_subset, "High Risk", "red")

    # Plot Low Risk
    plot_km_sksurv(df_subset, "Low Risk", "blue")

    plt.title(f"Kaplan-Meier Survival Curves by RSF Predicted Risk ({target_imputation})", fontsize=14)
    plt.xlabel("Time (days)", fontsize=12)
    plt.ylabel("Survival Probability", fontsize=12)
    plt.legend(title="Risk Group")
    plt.ylim(0, 1.05)

    plt.tight_layout()
    plt.savefig("survival_curves_test_set_unused.png", dpi=300)
    print("Saved 'survival_curves_test_set_unused.png'")


if __name__ == "__main__":
    plot_performance_comparison()
    plot_auc_time_dependent()
    plot_calibration_curves()
    plot_variable_importance()
    plot_survival_curves()
    print("Visualization script completed.")