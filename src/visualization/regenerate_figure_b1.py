"""
Regenerate Figure B1 with Lactate Median Value Annotations
===========================================================
Creates distribution comparison plot with median values displayed
for each imputation method.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

print("Generating Figure B1 with median value annotations...")

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11

# Load data
original = pd.read_csv("mimic_sepsis_cohort_full.csv")
observed_median = original['Lac'].median()

# Load imputed datasets
datasets = {
    'Observed (MIMIC-IV)': original['Lac'].dropna(),
}

# MICE (pool 5 imputations)
mice_lacs = []
for i in range(1, 6):
    try:
        mice_data = pd.read_csv(f"imputed_mice{i}_full.csv")
        mice_lacs.append(mice_data['Lac'].values)
    except:
        pass

if mice_lacs:
    mice_pooled = np.mean(mice_lacs, axis=0)
    datasets['MICE'] = mice_pooled

# Other methods
try:
    datasets['missForest'] = pd.read_csv("imputed_missForest_full.csv")['Lac']
except:
    pass

try:
    datasets['GAIN'] = pd.read_csv("imputed_GAIN_full.csv")['Lac']
except:
    pass

try:
    datasets['MIDA'] = pd.read_csv("imputed_MIDA_full.csv")['Lac']
except:
    pass

# Create figure
fig, ax = plt.subplots(figsize=(14, 8))

colors = {
    'Observed (MIMIC-IV)': '#2E86AB',
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
ax.set_title('Figure B1: Distribution of Lactate Values Across Imputation Methods\nwith Median Value Annotations', 
            fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', fontsize=11, framealpha=0.9)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 10)

plt.tight_layout()
plt.savefig('distribution_comparison_complete_vs_missing.png', dpi=300, bbox_inches='tight')
print("Saved: distribution_comparison_complete_vs_missing.png")

plt.close()

# Also create a summary table figure
fig, ax = plt.subplots(figsize=(10, 4))
ax.axis('tight')
ax.axis('off')

# Create table data
table_data = []
for name, data in datasets.items():
    if len(data) > 0:
        median_val = np.median(data)
        table_data.append([name, f"{median_val:.2f} mmol/L"])

table = ax.table(cellText=table_data, 
                colLabels=['Method', 'Median Lactate'],
                cellLoc='left',
                loc='center',
                colWidths=[0.5, 0.5])

table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1, 2.5)

# Style header
for i in range(2):
    table[(0, i)].set_facecolor('#4472C4')
    table[(0, i)].set_text_props(weight='bold', color='white')

# Alternate row colors
for i in range(1, len(table_data) + 1):
    for j in range(2):
        if i % 2 == 0:
            table[(i, j)].set_facecolor('#E7E6E6')

plt.title('Lactate Median Values by Imputation Method', 
         fontsize=14, fontweight='bold', pad=20)
plt.savefig('lactate_medians_table.png', dpi=300, bbox_inches='tight')
print("Saved: lactate_medians_table.png (bonus summary table)")

print("\nFigure B1 regenerated with median value annotations!")
print("The PDF will automatically update on next compilation.")
