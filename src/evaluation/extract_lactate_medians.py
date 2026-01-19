"""
Extract Lactate Median Values for Figure B1
============================================
Calculates median Lactate values from observed and imputed datasets
for comparison across imputation methods.
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("EXTRACTING LACTATE MEDIAN VALUES FOR FIGURE B1")
print("=" * 80)

# Load original data (observed values)
print("\n1. Loading original MIMIC-IV data...")
original = pd.read_csv("mimic_sepsis_cohort_full.csv")
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
