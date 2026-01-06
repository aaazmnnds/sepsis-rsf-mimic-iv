"""
Generate Full Cohort Predictions for Survival Analysis
=======================================================
This script trains RSF on the FULL cohort (n=852) and generates
predictions for ALL patients to enable proper survival analysis.

Input: synthetic_complete.csv (or your real MIMIC-IV data)
Output: full_cohort_rsf_predictions.csv with n=852 predictions
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sksurv.util import Surv
from sksurv.ensemble import RandomSurvivalForest

print("=" * 80)
print("GENERATING FULL COHORT RSF PREDICTIONS (n=852)")
print("=" * 80)

# ============================================================================
# 1. LOAD FULL COHORT DATA
# ============================================================================
print("\n1. Loading full cohort data...")

# Try to load the data file
try:
    data = pd.read_csv("mimic_sepsis_cohort_full.csv")
    print(f"   Loaded: mimic_sepsis_cohort_full.csv")
except FileNotFoundError:
    print("   ERROR: mimic_sepsis_cohort_full.csv not found!")
    print("   Please ensure the full MIMIC-IV cohort data file exists.")
    exit(1)
except Exception as e:
    print(f"   ERROR loading data: {e}")
    exit(1)

print(f"   Total patients: n={len(data)}")
print(f"   Total events: {data['Event'].sum()} ({100*data['Event'].mean():.1f}%)")

# ============================================================================
# 2. PREPARE DATA
# ============================================================================
print("\n2. Preparing data for RSF...")

# Separate features and outcome
feature_cols = [col for col in data.columns if col not in ['Time', 'Event']]
X = data[feature_cols].values
y = Surv.from_dataframe('Event', 'Time', data)

print(f"   Features: {len(feature_cols)} variables")
print(f"   Feature names: {', '.join(feature_cols[:5])}...")

# Standardize features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ============================================================================
# 3. TRAIN RSF ON FULL COHORT
# ============================================================================
print("\n3. Training RSF on full cohort...")

rsf = RandomSurvivalForest(
    n_estimators=1000,
    min_samples_split=10,
    min_samples_leaf=15,
    n_jobs=-1,
    random_state=42
)

rsf.fit(X_scaled, y)
print("   RSF training complete!")

# ============================================================================
# 4. GENERATE PREDICTIONS FOR ALL PATIENTS
# ============================================================================
print("\n4. Generating predictions for all patients...")

# Get risk scores (higher = higher risk)
risk_scores = rsf.predict(X_scaled)

# Create risk groups (median split)
median_risk = np.median(risk_scores)
risk_groups = ["High" if r >= median_risk else "Low" for r in risk_scores]

# Prepare output dataframe
predictions = pd.DataFrame({
    'Patient_ID': range(len(data)),
    'Observed_Time': data['Time'].values,
    'Observed_Status': data['Event'].values.astype(int),
    'Predicted_Risk': risk_scores,
    'Risk_Group': risk_groups
})

# Save predictions
predictions.to_csv("full_cohort_rsf_predictions.csv", index=False)
print(f"   Saved: full_cohort_rsf_predictions.csv (n={len(predictions)})")

# ============================================================================
# 5. SUMMARY STATISTICS
# ============================================================================
print("\n5. Summary statistics:")

for group in ['High', 'Low']:
    subset = predictions[predictions['Risk_Group'] == group]
    print(f"\n   {group} Risk Group:")
    print(f"     N = {len(subset)}")
    print(f"     Events = {subset['Observed_Status'].sum()}")
    print(f"     Event Rate = {100*subset['Observed_Status'].mean():.1f}%")
    print(f"     Mean Risk Score = {subset['Predicted_Risk'].mean():.2f}")

print("\n" + "=" * 80)
print("PREDICTION GENERATION COMPLETE")
print("=" * 80)
print("\nNext step:")
print("  Run: Rscript extract_full_cohort_statistics.R")
print("  (Update the R script to read 'full_cohort_rsf_predictions.csv')")
print("=" * 80)
