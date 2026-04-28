import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

def plot_sensitivity():
    # Absolute Root Configuration
    ROOT_DIR = "/Users/nazu.ds/Documents/Research Collections/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
    RESULTS_DIR = os.path.join(ROOT_DIR, "Results sensitivity")
    
    print("Generating Sensitivity Analysis Plot...")
    
    # 1. Load data
    filename = os.path.join(RESULTS_DIR, "model_performance_sensitivity_analysis.csv")
    if not os.path.exists(filename):
        print(f"Error: {filename} not found. Run survival_models.py first.")
        return
        
    df = pd.read_csv(filename)
    
    # 2. Filter for primary analysis
    plot_df = df[df["Metric"] == "C-index (Test)"].copy()
    plot_df["Target_Rate"] = pd.to_numeric(plot_df["Missingness_Rate"])
    plot_df["Imputation"] = plot_df["Imputation"].replace("MICE (pooled)", "MICE")
    
    # --- MAPPING TARGET TO ACTUAL RATES ---
    # Target 10 -> 10.00%, Target 40 -> 40.01%, Target 55 -> 54.98%
    rate_map = {10: 10.00, 40: 40.01, 55: 54.98}
    plot_df["Actual_Rate"] = plot_df["Target_Rate"].map(rate_map).fillna(plot_df["Target_Rate"])
    
    # 3. Setup Aesthetic
    sns.set_style("white")
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'sans-serif']
    
    mechanisms = sorted(plot_df["Mechanism"].unique())
    actual_rates = sorted(plot_df["Actual_Rate"].unique())
    
    fig, axes = plt.subplots(1, len(mechanisms), figsize=(20, 7), sharey=True)
    if len(mechanisms) == 1: axes = [axes]
    
    model_colors = {
        "RSF": "#1F77B4", "XGBoost": "#FF7F0E", "GradientBoosting": "#2CA02C", "DeepSurv": "#D62728"
    }
    
    for i, mech in enumerate(mechanisms):
        ax = axes[i]
        mech_data = plot_df[plot_df["Mechanism"] == mech]
        if mech_data.empty: continue
            
        summary = mech_data.groupby(["Model", "Actual_Rate"])["Value"].agg(["mean", "std"]).reset_index()
        
        for model in ["RSF", "XGBoost", "GradientBoosting", "DeepSurv"]:
            m_data = summary[summary["Model"] == model]
            if m_data.empty: continue
            
            lw = 4 if model == "RSF" else 2
            alpha = 1.0 if model == "RSF" else 0.6
            z = 10 if model == "RSF" else 5
            
            ax.plot(m_data["Actual_Rate"], m_data["mean"], 
                    label=model, color=model_colors[model], 
                    linewidth=lw, marker='o', markersize=8, alpha=alpha, zorder=z)
            
            ax.fill_between(m_data["Actual_Rate"], m_data["mean"] - m_data["std"], 
                           m_data["mean"] + m_data["std"], 
                           color=model_colors[model], alpha=0.1, zorder=z-1)
        
        ax.set_title(f"Mechanism: {mech}", fontsize=18, fontweight='bold', pad=20)
        ax.set_xlabel("Actual Missingness Rate (%)", fontsize=14)
        if i == 0: ax.set_ylabel("C-index (Mean \u00B1 SD)", fontsize=14)
        
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.set_xticks(actual_rates + [26.8])
        ax.set_ylim(0.4, 0.95)
        
        # Restore Baseline Line
        ax.axvline(x=26.8, color='#7F8C8D', linestyle='--', linewidth=2, alpha=0.8)
        if i == 0:
            ax.text(27.5, 0.42, "MIMIC-IV Baseline (26.8%)", rotation=90, color='#7F8C8D', fontsize=11, fontweight='bold')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=4, bbox_to_anchor=(0.5, -0.05), fontsize=14, frameon=False)
    plt.suptitle("Sensitivity Analysis: Model Robustness Across Missingness Rates", fontsize=22, fontweight='bold', y=1.05)
    plt.tight_layout()
    
    out_name = os.path.join(RESULTS_DIR, "sensitivity_analysis_rsf.png")
    plt.savefig(out_name, dpi=300, bbox_inches='tight')
    print(f"Saved: {out_name}")
    plt.close()

if __name__ == "__main__":
    plot_sensitivity()
