"""
Generate Full Cohort RSF Predictions using Python sksurv
=========================================================
Trains RSF on full MIMIC-IV cohort (n=852) and generates predictions
with proper risk score interpretation matching the original analysis.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sksurv.util import Surv
from sksurv.ensemble import RandomSurvivalForest

print("=" * 80)
print("GENERATING FULL COHORT RSF PREDICTIONS (Python sksurv)")
print("=" * 80)

# Load full MIMIC-IV cohort
print("\n1. Loading MIMIC-IV data...")
data = pd.read_csv("mimic_sepsis_cohort_full.csv")
print(f"   Loaded: n={len(data)} patients")
print(f"   Events: {data['Event'].sum()} ({100*data['Event'].mean():.1f}%)")

# Prepare features
feature_cols = [col for col in data.columns if col not in ['subject_id', 'hadm_id', 'Time', 'Event']]
X = data[feature_cols].values
y = Surv.from_dataframe('Event', 'Time', data)

print(f"\n2. Preparing data...")
print(f"   Features: {len(feature_cols)} variables")

# Handle missing values (median imputation)
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# Train RSF
print(f"\n3. Training RSF on full cohort...")
print(f"   (This may take a few minutes...)")

rsf = RandomSurvivalForest(
    n_estimators=1000,
    min_samples_split=10,
    min_samples_leaf=15,
    n_jobs=-1,
    random_state=42
)

rsf.fit(X_scaled, y)
print(f"   Training complete!")

# Generate predictions
print(f"\n4. Generating predictions...")
risk_scores = rsf.predict(X_scaled)  # Higher = higher risk (correct interpretation)

# Create risk groups (median split)
median_risk = np.median(risk_scores)
risk_groups = ["High" if r >= median_risk else "Low" for r in risk_scores]

# Save predictions
predictions = pd.DataFrame({
    'Patient_ID': range(len(data)),
    'Observed_Time': data['Time'].values,
    'Observed_Status': data['Event'].values.astype(int),
    'Predicted_Risk': risk_scores,
    'Risk_Group': risk_groups
})

predictions.to_csv("PYTHON_full_cohort_predictions.csv", index=False)
print(f"   Saved: PYTHON_full_cohort_predictions.csv")

# Summary
print(f"\n5. Summary:")
for group in ['High', 'Low']:
    subset = predictions[predictions['Risk_Group'] == group]
    print(f"\n   {group} Risk:")
    print(f"     N = {len(subset)}")
    print(f"     Events = {subset['Observed_Status'].sum()}")
    print(f"     Event Rate = {100*subset['Observed_Status'].mean():.1f}%")

print("\n" + "=" * 80)
print("DONE! Now run the R script to calculate survival statistics.")
print("=" * 80)