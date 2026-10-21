"""
Regenerate Figure B1 with Lactate Median Value Annotations
===========================================================
Creates distribution comparison plot with median values displayed
for each imputation method.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

print("Generating Figure B1 with median value annotations...")

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

# Run folder
run_dir = "Results sensitivity"
if not os.path.exists(run_dir):
    # Try relative paths
    if os.path.exists(os.path.join("..", "Results sensitivity")):
        run_dir = os.path.join("..", "Results sensitivity")
    elif os.path.exists(os.path.join("..", "..", "Results sensitivity")):
        run_dir = os.path.join("..", "..", "Results sensitivity")

# Raw data path
raw_path = "../data/raw/mimic_sepsis_cohort_full.csv"
if not os.path.exists(raw_path):
    if os.path.exists(os.path.join("..", raw_path)):
        raw_path = os.path.join("..", raw_path)
    elif os.path.exists("mimic_sepsis_cohort_full.csv"):
        raw_path = "mimic_sepsis_cohort_full.csv"

# Load raw observed data
original = pd.read_csv(raw_path)
observed = original['Lac'].dropna()
mask = original['Lac'].isna()

# Load imputed entries only (where mask is True)
datasets = {
    'Observed': observed,
}

imputed_files = {
    'MICE': 'mice1_full.csv',
    'missForest': 'missForest_full.csv',
    'GAIN': 'GAIN_mimic_sepsis_cohort_full.csv',
    'MIDA': 'MIDA_mimic_sepsis_cohort_full.csv'
}

for name, fname in imputed_files.items():
    fpath = os.path.join(run_dir, fname)
    if os.path.exists(fpath):
        imp_df = pd.read_csv(fpath)
        datasets[name] = imp_df.loc[mask, 'Lac']
    else:
        print(f"Warning: {fpath} not found.")

# Create figure
fig, ax = plt.subplots(figsize=(14, 8))

colors = {
    'Observed': '#2E86AB',
    'MICE': '#A23B72',
    'missForest': '#F18F01',
    'GAIN': '#C73E1D',
    'MIDA': '#6A994E'
}

# Plot distributions
for name, data in datasets.items():
    if len(data) > 0:
        median_val = np.median(data)

        # Plot KDE (Density Curve)
        data_clean = data[~np.isnan(data)]
        if len(data_clean) > 10:
            sns.kdeplot(data_clean, fill=True, alpha=0.1, label=f'{name} (median={median_val:.2f})',
                       color=colors.get(name, 'gray'), ax=ax, linewidth=2.5)

            # Add median line
            ax.axvline(median_val, color=colors.get(name, 'gray'),
                      linestyle='--', linewidth=1.5, alpha=0.8)

ax.set_xlabel('Lactate (mmol/L)', fontsize=13, fontweight='bold')
ax.set_ylabel('Density', fontsize=13, fontweight='bold')
ax.set_title('Lactate distribution: observed values and imputed entries',
            fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 10)

plt.tight_layout()
output_filename = 'distribution_comparison_complete_vs_missing.png'
out_path = os.path.join(run_dir, output_filename)
plt.savefig(out_path, dpi=300, bbox_inches='tight')
if os.path.abspath(run_dir) != os.path.abspath("."):
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
print(f"Saved: {output_filename}")

plt.close()
