import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob

def plot_performance_comparison():
    print("Generating Performance Comparison Plot...")
    
    # Check if results file exists
    if not glob.glob("model_performance_results.csv"):
        print("Error: 'model_performance_results.csv' not found. Run survival_models.py first.")
        return

    df = pd.read_csv("model_performance_results.csv")
    
    # Filter for C-index (Test) or C-index (CV) 
    # Let's plot Test C-index for final comparison
    df_test = df[df["Metric"] == "C-index (Test)"]
    
    if df_test.empty:
        # Fallback to CV mean if Test not available or just to show CV
        df_test = df[df["Metric"] == "C-index (CV)"]
        title_suffix = "(CV Mean)"
    else:
        title_suffix = "(Hold-out Test)"

    plt.figure(figsize=(12, 6))
    sns.set_style("whitegrid")
    
    # Bar plot: x=Imputation, y=Value, hue=Model
    # We want to see how Imputation affects performance for each Model
    # Or focus on RSF across imputations as per paper aim
    
    ax = sns.barplot(data=df_test, x="Imputation", y="Value", hue="Model", palette="viridis")
    
    plt.title(f"Model Discrimination Performance {title_suffix}", fontsize=14)
    plt.ylabel("C-index", fontsize=12)
    plt.xlabel("Imputation Method", fontsize=12)
    plt.ylim(0.5, 1.0) # C-index scale
    plt.legend(title="Model", loc="upper right")
    
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
        
    df_preds = pd.read_csv("model_predictions.csv")
    
    # Focus on RSF model for calibration plot (Primary Method)
    df_rsf = df_preds[df_preds["Model"] == "RSF"]
    
    if df_rsf.empty:
        print("No predictions found for RSF.")
        return
        
    plt.figure(figsize=(8, 8))
    sns.set_style("whitegrid")
    
    # Plotting calibration is complex for survival (time-dependent).
    # Simple approach for visualization script: 
    # Stratify predicted risk into deciles and plot Mean Predicted Risk vs Observed Event Rate 
    # (Note: This is a simplified proxy for visual check, rigor required Brier Score which we calculated numerically)
    
    # Create Deciles
    df_rsf["Risk_Decile"] = pd.qcut(df_rsf["Predicted_Risk"], 10, labels=False)
    
    calibration_data = df_rsf.groupby("Risk_Decile").agg({
        "Predicted_Risk": "mean",
        "Observed_Status": "mean" # Mean event rate (approximate probability)
    }).reset_index()
    
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.plot(calibration_data["Predicted_Risk"], calibration_data["Observed_Status"], "o-", label="RSF (Risk Deciles)", color="blue")
    
    plt.title("Calibration Plot (RSF Risk Score vs Event Rate)", fontsize=14)
    plt.xlabel("Predicted Risk (Mean)", fontsize=12)
    plt.ylabel("Observed Event Rate", fontsize=12)
    plt.legend()
    
    plt.tight_layout()
    plt.tight_layout()
    plt.savefig("calibration_curve_proxy.png", dpi=300)
    print("Saved 'calibration_curve_proxy.png'")


def plot_variable_importance():
    print("Generating Variable Importance Plot...")
    
    if not glob.glob("variable_importance.csv"):
        print("Error: 'variable_importance.csv' not found. Run survival_models.py first.")
        return
        
    df = pd.read_csv("variable_importance.csv")
    
    # We want to show the Top 10 features for RSF across imputation methods
    # Filter for RSF (should be the only one, but safe to filter)
    df_rsf = df[df["Model"] == "RSF"]
    
    if df_rsf.empty:
        print("No variable importance records found for RSF.")
        return
        
    # Aggregate importance across imputations (mean of means)
    # Group by Imputation Method and Feature
    df_agg = df_rsf.groupby(["Imputation", "Feature"])["Importance_Mean"].mean().reset_index()
    
    # Find global Top 10 features (averaged across all imputation methods for simplicity)
    # Or better: Pick one imputation method (e.g., MICE) as the reference for sorting
    top_features = df_agg.groupby("Feature")["Importance_Mean"].mean().sort_values(ascending=False).head(10).index
    
    # Filter data to only valid top features
    df_plot = df_agg[df_agg["Feature"].isin(top_features)]
    
    plt.figure(figsize=(10, 8))
    sns.set_style("whitegrid")
    
    # Bar plot: x=Importance, y=Feature, hue=Imputation
    sns.barplot(data=df_plot, x="Importance_Mean", y="Feature", hue="Imputation", 
                order=top_features, palette="viridis")
    
    plt.title("Variable Importance (RSF Model)", fontsize=14)
    plt.xlabel("Permutation Importance (Mean Decrease in Accuracy)", fontsize=12)
    plt.ylabel("Feature", fontsize=12)
    plt.legend(title="Imputation Method", loc="lower right")
    
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
    plt.savefig("survival_curves_all_subjects1.png", dpi=300)
    print("Saved 'survival_curves_all_subjects1.png'")


if __name__ == "__main__":
    plot_performance_comparison()
    plot_auc_time_dependent()
    plot_calibration_curves()
    plot_variable_importance()
    plot_survival_curves()
    print("Visualization script completed.")
