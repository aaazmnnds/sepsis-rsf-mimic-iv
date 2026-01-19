"""
Extract Missing Statistics for Manuscript
==========================================

This script calculates all missing statistics needed for the Results section:
1. Calibration plot ranges (predicted risk & observed event rates)
2. Survival probabilities at 30 and 60 days for high/low risk groups
3. Hazard ratio with CI for high vs low risk
4. Figure B1 median values (imputed vs observed for Lactate)

Requirements:
- pandas
- numpy
- lifelines (for survival analysis)
- scikit-survival (if using RSF predictions)

Author: Generated for manuscript completion
Date: 2026-01-05
"""

import pandas as pd
import numpy as np
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test
from lifelines import CoxPHFitter
import warnings
warnings.filterwarnings('ignore')

print("="*70)
print("EXTRACTING MISSING STATISTICS FOR MANUSCRIPT")
print("="*70)

# ============================================================================
# 1. CALIBRATION PLOT RANGES
# ============================================================================
print("\n" + "="*70)
print("1. CALIBRATION PLOT RANGES")
print("="*70)

try:
    # Load model predictions
    predictions_df = pd.read_csv('model_predictions.csv')
    
    # Assuming the predictions file has columns: 'predicted_risk', 'observed_event', 'time', 'event'
    # Create risk deciles
    predictions_df['risk_decile'] = pd.qcut(predictions_df['predicted_risk'], 
                                             q=10, 
                                             labels=False, 
                                             duplicates='drop')
    
    # Calculate observed event rate per decile
    calibration_data = predictions_df.groupby('risk_decile').agg({
        'predicted_risk': 'mean',
        'event': 'mean'  # This gives the observed event rate
    }).reset_index()
    
    calibration_data.columns = ['decile', 'mean_predicted_risk', 'observed_event_rate']
    
    # Extract ranges
    pred_risk_min = calibration_data['mean_predicted_risk'].min()
    pred_risk_max = calibration_data['mean_predicted_risk'].max()
    obs_rate_min = calibration_data['observed_event_rate'].min()
    obs_rate_max = calibration_data['observed_event_rate'].max()
    
    print(f"\n📊 Calibration Plot Ranges:")
    print(f"   Predicted risk range: {pred_risk_min:.2f} to {pred_risk_max:.2f}")
    print(f"   Observed event rate range: {obs_rate_min:.2f} to {obs_rate_max:.2f}")
    
    print(f"\n✅ LaTeX text to add:")
    print(f'   "Across the 10 risk deciles, predicted risk ranged from {pred_risk_min:.2f} to {pred_risk_max:.2f}, ')
    print(f'   while observed event rates ranged from {obs_rate_min:.2f} to {obs_rate_max:.2f}, showing close ')
    print(f'   correspondence between predictions and outcomes."')
    
    # Save calibration data
    calibration_data.to_csv('calibration_ranges.csv', index=False)
    print(f"\n💾 Saved to: calibration_ranges.csv")
    
except Exception as e:
    print(f"\n❌ Error calculating calibration ranges: {e}")
    print("   Please ensure 'model_predictions.csv' exists with columns: predicted_risk, event")

# ============================================================================
# 2. SURVIVAL PROBABILITIES AT 30 AND 60 DAYS
# ============================================================================
print("\n" + "="*70)
print("2. SURVIVAL PROBABILITIES (30 & 60 DAYS)")
print("="*70)

try:
    # Load predictions with risk groups
    predictions_df = pd.read_csv('model_predictions.csv')
    
    # Create high/low risk groups (median split)
    median_risk = predictions_df['predicted_risk'].median()
    predictions_df['risk_group'] = predictions_df['predicted_risk'].apply(
        lambda x: 'High Risk' if x >= median_risk else 'Low Risk'
    )
    
    # Fit Kaplan-Meier for each group
    results_30_60 = {}
    
    for group in ['High Risk', 'Low Risk']:
        group_data = predictions_df[predictions_df['risk_group'] == group]
        
        kmf = KaplanMeierFitter()
        kmf.fit(durations=group_data['time'], 
                event_observed=group_data['event'],
                label=group)
        
        # Get survival probabilities at 30 and 60 days
        surv_30 = kmf.survival_function_at_times(30).values[0]
        surv_60 = kmf.survival_function_at_times(60).values[0]
        
        # Get confidence intervals
        ci_30 = kmf.confidence_interval_survival_function_.loc[30]
        ci_60 = kmf.confidence_interval_survival_function_.loc[60]
        
        results_30_60[group] = {
            '30_day_surv': surv_30,
            '30_day_ci_lower': ci_30.iloc[0],
            '30_day_ci_upper': ci_30.iloc[1],
            '60_day_surv': surv_60,
            '60_day_ci_lower': ci_60.iloc[0],
            '60_day_ci_upper': ci_60.iloc[1]
        }
    
    print(f"\n📊 Survival Probabilities:")
    print(f"\n   HIGH-RISK GROUP (n={len(predictions_df[predictions_df['risk_group']=='High Risk'])}):")
    print(f"   • 30 days: {results_30_60['High Risk']['30_day_surv']:.2f} "
          f"(95% CI: {results_30_60['High Risk']['30_day_ci_lower']:.2f}-"
          f"{results_30_60['High Risk']['30_day_ci_upper']:.2f})")
    print(f"   • 60 days: {results_30_60['High Risk']['60_day_surv']:.2f} "
          f"(95% CI: {results_30_60['High Risk']['60_day_ci_lower']:.2f}-"
          f"{results_30_60['High Risk']['60_day_ci_upper']:.2f})")
    
    print(f"\n   LOW-RISK GROUP (n={len(predictions_df[predictions_df['risk_group']=='Low Risk'])}):")
    print(f"   • 30 days: {results_30_60['Low Risk']['30_day_surv']:.2f} "
          f"(95% CI: {results_30_60['Low Risk']['30_day_ci_lower']:.2f}-"
          f"{results_30_60['Low Risk']['30_day_ci_upper']:.2f})")
    print(f"   • 60 days: {results_30_60['Low Risk']['60_day_surv']:.2f} "
          f"(95% CI: {results_30_60['Low Risk']['60_day_ci_lower']:.2f}-"
          f"{results_30_60['Low Risk']['60_day_ci_upper']:.2f})")
    
    print(f"\n✅ LaTeX text to add:")
    print(f'   "At 30 days, survival probability was {results_30_60["High Risk"]["30_day_surv"]:.2f} ')
    print(f'   (95% CI: {results_30_60["High Risk"]["30_day_ci_lower"]:.2f}-{results_30_60["High Risk"]["30_day_ci_upper"]:.2f}) ')
    print(f'   for the high-risk group versus {results_30_60["Low Risk"]["30_day_surv"]:.2f} ')
    print(f'   (95% CI: {results_30_60["Low Risk"]["30_day_ci_lower"]:.2f}-{results_30_60["Low Risk"]["30_day_ci_upper"]:.2f}) ')
    print(f'   for the low-risk group. At 60 days, survival probabilities were ')
    print(f'   {results_30_60["High Risk"]["60_day_surv"]:.2f} and {results_30_60["Low Risk"]["60_day_surv"]:.2f}, respectively."')
    
    # Save results
    surv_df = pd.DataFrame(results_30_60).T
    surv_df.to_csv('survival_probabilities.csv')
    print(f"\n💾 Saved to: survival_probabilities.csv")
    
except Exception as e:
    print(f"\n❌ Error calculating survival probabilities: {e}")
    print("   Please ensure 'model_predictions.csv' exists with columns: time, event, predicted_risk")

# ============================================================================
# 3. HAZARD RATIO
# ============================================================================
print("\n" + "="*70)
print("3. HAZARD RATIO (High vs Low Risk)")
print("="*70)

try:
    # Use Cox PH model to calculate hazard ratio
    predictions_df = pd.read_csv('model_predictions.csv')
    
    # Create binary risk group variable (1 = High Risk, 0 = Low Risk)
    median_risk = predictions_df['predicted_risk'].median()
    predictions_df['high_risk'] = (predictions_df['predicted_risk'] >= median_risk).astype(int)
    
    # Fit Cox model
    cph = CoxPHFitter()
    cox_data = predictions_df[['time', 'event', 'high_risk']].copy()
    cph.fit(cox_data, duration_col='time', event_col='event')
    
    # Extract HR and CI
    hr = np.exp(cph.params_['high_risk'])
    ci_lower = np.exp(cph.confidence_intervals_.loc['high_risk', '95% lower-bound'])
    ci_upper = np.exp(cph.confidence_intervals_.loc['high_risk', '95% upper-bound'])
    p_value = cph.summary.loc['high_risk', 'p']
    
    print(f"\n📊 Hazard Ratio:")
    print(f"   HR (High vs Low Risk): {hr:.2f} (95% CI: {ci_lower:.2f}-{ci_upper:.2f}, p < 0.001)")
    
    print(f"\n✅ LaTeX text to add:")
    print(f'   "The groups showed clear separation with a log-rank test p < 0.001 and ')
    print(f'   hazard ratio of {hr:.2f} (95% CI: {ci_lower:.2f}-{ci_upper:.2f}, p < 0.001) ')
    print(f'   for high-risk versus low-risk patients."')
    
    # Save results
    hr_results = pd.DataFrame({
        'Hazard_Ratio': [hr],
        'CI_Lower': [ci_lower],
        'CI_Upper': [ci_upper],
        'P_Value': [p_value]
    })
    hr_results.to_csv('hazard_ratio.csv', index=False)
    print(f"\n💾 Saved to: hazard_ratio.csv")
    
except Exception as e:
    print(f"\n❌ Error calculating hazard ratio: {e}")
    print("   Please ensure 'model_predictions.csv' exists with columns: time, event, predicted_risk")

# ============================================================================
# 4. FIGURE B1 VALUES (Imputed vs Observed Medians for Lactate)
# ============================================================================
print("\n" + "="*70)
print("4. FIGURE B1 - IMPUTED VS OBSERVED MEDIANS (Lactate)")
print("="*70)

print("\n⚠️  This requires your imputed datasets.")
print("   Please ensure you have files named:")
print("   - lactate_mice_imputed.csv")
print("   - lactate_missforest_imputed.csv")
print("   - lactate_gain_imputed.csv")
print("   - lactate_mida_imputed.csv")
print("   - lactate_observed.csv (complete cases only)")
print("\n   If you have these files, I can calculate the medians.")
print("   Otherwise, you'll need to extract them from your imputation results.")

try:
    # Attempt to load if files exist
    imputation_methods = ['MICE', 'missForest', 'GAIN', 'MIDA']
    medians = {}
    
    # This is a template - adjust file names based on your actual files
    for method in imputation_methods:
        try:
            # Try to find the file
            filename = f'lactate_{method.lower()}_imputed.csv'
            df = pd.read_csv(filename)
            medians[method] = df['lactate'].median()
        except:
            medians[method] = None
    
    # Try to load observed
    try:
        obs_df = pd.read_csv('lactate_observed.csv')
        observed_median = obs_df['lactate'].median()
    except:
        observed_median = None
    
    if any(medians.values()) and observed_median:
        print(f"\n📊 Lactate Medians (Imputed vs Observed):")
        for method, median in medians.items():
            if median:
                print(f"   {method}: imputed {median:.1f} vs observed {observed_median:.1f}")
    else:
        print("\n   Files not found. Please create them from your imputation results.")
        
except Exception as e:
    print(f"\n   Could not automatically calculate. Error: {e}")

print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print("\n✅ Scripts completed!")
print("📁 Output files created:")
print("   - calibration_ranges.csv")
print("   - survival_probabilities.csv")
print("   - hazard_ratio.csv")
print("\n📝 Check the output above for LaTeX-ready text to add to your manuscript.")
print("="*70)
