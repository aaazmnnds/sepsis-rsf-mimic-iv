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
        
    df = pd.read_csv(filename, dtype={"Missingness_Rate": str})
    
    # 2. Filter for primary analysis
    plot_df = df[
        (df["Metric"] == "C-index (CV)") & 
        (df["Model"] == "RSF") & 
        (df["Mechanism"].isin(["MAR", "MCAR", "MNAR"]))
    ].copy()
    plot_df["Missingness_Rate"] = pd.to_numeric(plot_df["Missingness_Rate"])
    plot_df["Imputation"] = plot_df["Imputation"].replace("MICE (pooled)", "MICE")
    
    # 3. Setup Aesthetic
    sns.set_style("white")
    plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'sans-serif']
    
    mechanisms = ["MAR", "MCAR", "MNAR"]
    imputations = ["MICE", "missForest", "GAIN", "MIDA"]
    
    fig, axes = plt.subplots(1, len(mechanisms), figsize=(18, 6), sharey=True)
    if len(mechanisms) == 1:
        axes = [axes]
    
    # Four distinct colors and markers
    imp_styles = {
        "MICE": {"color": "#1f77b4", "marker": "o"},
        "missForest": {"color": "#2ca02c", "marker": "s"},
        "GAIN": {"color": "#d62728", "marker": "^"},
        "MIDA": {"color": "#9467bd", "marker": "D"}
    }
    
    for i, mech in enumerate(mechanisms):
        ax = axes[i]
        mech_data = plot_df[plot_df["Mechanism"] == mech]
        
        for imp in imputations:
            imp_data = mech_data[mech_data["Imputation"] == imp].sort_values(by="Missingness_Rate")
            if imp_data.empty:
                continue
            
            x_vals = imp_data["Missingness_Rate"].values
            y_vals = imp_data["Value"].values
            sd_vals = imp_data["CV_SD"].values
            
            style = imp_styles[imp]
            ax.plot(
                x_vals, y_vals,
                label=imp,
                color=style["color"],
                marker=style["marker"],
                linewidth=2.2,
                markersize=7,
                alpha=0.9
            )
            
            ax.fill_between(
                x_vals,
                y_vals - sd_vals,
                y_vals + sd_vals,
                color=style["color"],
                alpha=0.08
            )
        
        ax.set_title(mech, fontsize=16, fontweight='bold', pad=12)
        ax.set_xlabel("Overall missingness rate (%)", fontsize=13)
        if i == 0:
            ax.set_ylabel("Cross-validated C-index (mean, shaded: fold SD)", fontsize=13)
        
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.set_xticks([10.0, 26.8, 40.01, 54.98])
        ax.set_ylim(0.4, 0.95)
        
        # Vertical line at observed rate
        ax.axvline(x=26.8, color='#7F8C8D', linestyle='--', linewidth=1.5, alpha=0.8)
        ax.text(
            27.5, 0.42, "MIMIC-IV rate (26.8%)",
            rotation=90, color='#7F8C8D', fontsize=11, fontweight='bold'
        )

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles, labels,
        title="Imputation method",
        loc='lower center',
        ncol=4,
        bbox_to_anchor=(0.5, -0.08),
        fontsize=12,
        title_fontsize=13,
        frameon=False
    )
    plt.tight_layout()
    
    out_name = os.path.join(RESULTS_DIR, "sensitivity_analysis_rsf.png")
    plt.savefig(out_name, dpi=300, bbox_inches='tight')
    print(f"Saved: {out_name}")
    plt.close()

if __name__ == "__main__":
    plot_sensitivity()
