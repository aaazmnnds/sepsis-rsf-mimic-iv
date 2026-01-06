"""
Extract Full Test Set Statistics for Manuscript (Simplified Version)
=====================================================================
Uses only numpy/pandas to avoid dependency issues.
Outputs statistics from the FULL test set in model_predictions.csv
"""

import pandas as pd
import numpy as np

print("=" * 80)
print("EXTRACTING FULL TEST SET STATISTICS")
print("=" * 80)

# ============================================================================
# 1. LOAD FULL MODEL PREDICTIONS
# ============================================================================
print("\n1. Loading full model predictions...")

try:
    df = pd.read_csv("model_predictions.csv")
    print(f"   Loaded {len(df)} total predictions")
    
    # Filter for RSF + GAIN
    rsf_gain = df[(df['Model'] == 'RSF') & (df['Imputation'] == 'GAIN')].copy()
    print(f"   RSF-GAIN predictions: {len(rsf_gain)} rows")
    
    if len(rsf_gain) == 0:
        print("   ERROR: No RSF-GAIN predictions found!")
        exit(1)
    
    # Convert status to int
    rsf_gain['Observed_Status'] = rsf_gain['Observed_Status'].astype(int)
    
    # Create risk groups (median split)
    median_risk = rsf_gain['Predicted_Risk'].median()
    rsf_gain['Risk_Group'] = rsf_gain['Predicted_Risk'].apply(
        lambda x: 'High' if x >= median_risk else 'Low'
    )
    
    print(f"   Sample size: n={len(rsf_gain)}")
    print(f"   Events: {rsf_gain['Observed_Status'].sum()}")
    print(f"   Event rate: {rsf_gain['Observed_Status'].mean():.3f}")
    
except Exception as e:
    print(f"   ERROR: {e}")
    exit(1)

# ============================================================================
# 2. CALIBRATION STATISTICS
# ============================================================================
print("\n2. Calculating calibration statistics...")

rsf_gain['risk_decile'] = pd.qcut(
    rsf_gain['Predicted_Risk'], 
    q=10, 
    labels=False, 
    duplicates='drop'
)

calib = rsf_gain.groupby('risk_decile').agg({
    'Predicted_Risk': 'mean',
    'Observed_Status': 'mean'
}).reset_index()

calib.columns = ['Decile', 'Mean_Predicted_Risk', 'Observed_Event_Rate']
calib.to_csv("full_test_calibration.csv", index=False)

print(f"   Predicted Risk Range: {calib['Mean_Predicted_Risk'].min():.4f} - {calib['Mean_Predicted_Risk'].max():.4f}")
print(f"   Observed Rate Range: {calib['Observed_Event_Rate'].min():.4f} - {calib['Observed_Event_Rate'].max():.4f}")
print("   Saved: full_test_calibration.csv")

# ============================================================================
# 3. RISK GROUP SUMMARY
# ============================================================================
print("\n3. Risk group summary...")

for group in ['Low', 'High']:
    subset = rsf_gain[rsf_gain['Risk_Group'] == group]
    print(f"\n   {group} Risk Group:")
    print(f"     N = {len(subset)}")
    print(f"     Events = {subset['Observed_Status'].sum()}")
    print(f"     Event Rate = {subset['Observed_Status'].mean():.3f}")
    print(f"     Mean Survival Time = {subset['Observed_Time'].mean():.1f} days")

# Save risk group data for R analysis
rsf_gain[['Observed_Time', 'Observed_Status', 'Predicted_Risk', 'Risk_Group']].to_csv(
    "full_test_rsf_gain_for_r.csv", index=False
)
print("\n   Saved: full_test_rsf_gain_for_r.csv")
print("   (Use this file with extract_missing_statistics.R for KM curves and Cox model)")

# ============================================================================
# 4. SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("EXTRACTION COMPLETE")
print("=" * 80)
print("\nGenerated files:")
print("  1. full_test_calibration.csv - Calibration statistics")
print("  2. full_test_rsf_gain_for_r.csv - Data for R analysis")
print("\nNext steps:")
print("  1. Run extract_missing_statistics.R on full_test_rsf_gain_for_r.csv")
print("  2. Check if the p-value is now significant with full dataset")
print("  3. Update manuscript with correct values")
print("=" * 80)
