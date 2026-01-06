"""
Generate Publication Tables (CSV Format) with Time-Dependent AUC
Author: Results Reporting Script
Date: 2026-01-06
"""

import pandas as pd
import numpy as np

# Load data
print("="*70)
print("Loading data files...")
print("="*70)
summary = pd.read_csv('model_performance_summary.csv')
vimp = pd.read_csv('variable_importance.csv')

print(f"Summary data: {len(summary)} rows")
print(f"Variable importance data: {len(vimp)} rows")

# ============================================================================
# TABLE 1: MAIN RESULTS - REAL MIMIC DATA (WITH TIME-DEPENDENT AUC)
# ============================================================================

print("\n" + "="*70)
print("TABLE 1: Main Results on Real MIMIC-IV Data (WITH AUC)")
print("="*70)

# Filter for real data
df_real = summary[summary['Mechanism'] == 'full'].copy()

# Separate metrics
cv_data = df_real[df_real['Metric'] == 'C-index (CV)'][['Imputation', 'Model', 'Formatted', 'Mean']]
test_data = df_real[df_real['Metric'] == 'C-index (Test)'][['Imputation', 'Model', 'Mean']]
ibs_data = df_real[df_real['Metric'] == 'IBS (Test)'][['Imputation', 'Model', 'Mean']]
auc3_data = df_real[df_real['Metric'] == 'AUC_Day3'][['Imputation', 'Model', 'Mean']]
auc7_data = df_real[df_real['Metric'] == 'AUC_Day7'][['Imputation', 'Model', 'Mean']]
auc14_data = df_real[df_real['Metric'] == 'AUC_Day14'][['Imputation', 'Model', 'Mean']]

# Build table
table1_data = []
for imp in ['MICE (pooled)', 'missForest', 'GAIN', 'MIDA']:
    row = {'Imputation': imp}
    
    for model in ['RSF', 'XGBoost', 'GradientBoosting', 'DeepSurv']:
        # CV C-index
        cv_val = cv_data[(cv_data['Imputation']==imp) & (cv_data['Model']==model)]['Formatted'].values
        row[f'{model}_CV'] = cv_val[0] if len(cv_val) > 0 else '—'
        
        # Test C-index
        test_val = test_data[(test_data['Imputation']==imp) & (test_data['Model']==model)]['Mean'].values
        row[f'{model}_Test'] = f"{test_val[0]:.3f}" if len(test_val) > 0 else '—'
        
        # IBS
        ibs_val = ibs_data[(ibs_data['Imputation']==imp) & (ibs_data['Model']==model)]['Mean'].values
        row[f'{model}_IBS'] = f"{ibs_val[0]:.3f}" if len(ibs_val) > 0 else '—'
        
        # AUC Day 3
        auc3_val = auc3_data[(auc3_data['Imputation']==imp) & (auc3_data['Model']==model)]['Mean'].values
        row[f'{model}_AUC3'] = f"{auc3_val[0]:.3f}" if len(auc3_val) > 0 else '—'
        
        # AUC Day 7
        auc7_val = auc7_data[(auc7_data['Imputation']==imp) & (auc7_data['Model']==model)]['Mean'].values
        row[f'{model}_AUC7'] = f"{auc7_val[0]:.3f}" if len(auc7_val) > 0 else '—'
        
        # AUC Day 14
        auc14_val = auc14_data[(auc14_data['Imputation']==imp) & (auc14_data['Model']==model)]['Mean'].values
        row[f'{model}_AUC14'] = f"{auc14_val[0]:.3f}" if len(auc14_val) > 0 else '—'
    
    table1_data.append(row)

table1 = pd.DataFrame(table1_data)
table1.to_csv('Table1_main_results_with_AUC.csv', index=False)
print("\nSaved: Table1_main_results_with_AUC.csv")
print("\nPreview:")
print(table1.head())

# ============================================================================
# TABLE 2: IMPUTATION COMPARISON BY MECHANISM (UNCHANGED)
# ============================================================================

print("\n" + "="*70)
print("TABLE 2: Imputation Comparison Across Mechanisms")
print("="*70)

df_rsf = summary[
    (summary['Model'] == 'RSF') & 
    (summary['Metric'] == 'C-index (CV)') &
    (summary['Mechanism'].isin(['mcar', 'mar', 'mnar']))
].copy()

table2 = df_rsf.pivot_table(
    index='Mechanism',
    columns='Imputation',
    values='Formatted',
    aggfunc='first'
)

# Reorder columns
col_order = ['MICE (pooled)', 'missForest', 'GAIN', 'MIDA']
table2 = table2[[c for c in col_order if c in table2.columns]]

table2.to_csv('Table2_imputation_comparison.csv')
print("\nSaved: Table2_imputation_comparison.csv")
print("\nPreview:")
print(table2)

# ============================================================================
# TABLE 3: MODEL RANKING (WITH AUC)
# ============================================================================

print("\n" + "="*70)
print("TABLE 3: Model Ranking with Time-Dependent AUC")
print("="*70)

# Find best imputation for each model
best_performers = []

for model in ['RSF', 'XGBoost', 'GradientBoosting', 'DeepSurv']:
    model_data = summary[
        (summary['Model'] == model) & 
        (summary['Metric'] == 'C-index (Test)') &
        (summary['Mechanism'] == 'full')
    ].copy()
    
    if len(model_data) > 0:
        best_row = model_data.loc[model_data['Mean'].idxmax()]
        
        # Get CV C-index
        cv_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'C-index (CV)')
        ]
        
        # Get IBS
        ibs_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'IBS (Test)')
        ]
        
        # Get AUC Day 3
        auc3_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'AUC_Day3')
        ]
        
        # Get AUC Day 7
        auc7_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'AUC_Day7')
        ]
        
        # Get AUC Day 14
        auc14_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'AUC_Day14')
        ]
        
        best_performers.append({
            'Model': model,
            'Best Imputation': best_row['Imputation'],
            'CV C-index': cv_row['Formatted'].values[0] if len(cv_row) > 0 else '—',
            'Test C-index': f"{best_row['Mean']:.3f}",
            'IBS': f"{ibs_row['Mean'].values[0]:.3f}" if len(ibs_row) > 0 else '—',
            'AUC Day 3': f"{auc3_row['Mean'].values[0]:.3f}" if len(auc3_row) > 0 else '—',
            'AUC Day 7': f"{auc7_row['Mean'].values[0]:.3f}" if len(auc7_row) > 0 else '—',
            'AUC Day 14': f"{auc14_row['Mean'].values[0]:.3f}" if len(auc14_row) > 0 else '—'
        })

table3 = pd.DataFrame(best_performers)
table3 = table3.sort_values('Test C-index', ascending=False).reset_index(drop=True)
table3['Rank'] = range(1, len(table3) + 1)

# Reorder columns
table3 = table3[['Rank', 'Model', 'Best Imputation', 'CV C-index', 'Test C-index', 
                 'IBS', 'AUC Day 3', 'AUC Day 7', 'AUC Day 14']]

table3.to_csv('Table3_model_ranking_with_AUC.csv', index=False)
print("\nSaved: Table3_model_ranking_with_AUC.csv")
print("\nPreview:")
print(table3)

# ============================================================================
# TABLE 4: VARIABLE IMPORTANCE (UNCHANGED)
# ============================================================================

print("\n" + "="*70)
print("TABLE 4: Variable Importance")
print("="*70)

df_vimp = vimp[
    (vimp['Mechanism'] == 'full') & 
    (vimp['Model'] == 'RSF')
].copy()

vimp_summary = df_vimp.groupby('Feature').agg({
    'Importance_Mean': 'mean',
    'Importance_Std': 'mean'
}).reset_index()

vimp_summary = vimp_summary.sort_values('Importance_Mean', ascending=False).head(10)
vimp_summary['Rank'] = range(1, len(vimp_summary) + 1)

# Format for publication
vimp_summary['Importance'] = vimp_summary['Importance_Mean'].apply(lambda x: f"{x:.4f}")
vimp_summary['Std'] = vimp_summary['Importance_Std'].apply(lambda x: f"{x:.4f}")

table4 = vimp_summary[['Rank', 'Feature', 'Importance', 'Std']]

table4.to_csv('Table4_variable_importance.csv', index=False)
print("\nSaved: Table4_variable_importance.csv")
print("\nPreview:")
print(table4)

# ============================================================================
# TABLE 5 (NEW): TIME-DEPENDENT AUC SUMMARY ACROSS ALL CONDITIONS
# ============================================================================

print("\n" + "="*70)
print("TABLE 5 (BONUS): Time-Dependent AUC Summary")
print("="*70)

# Get all AUC data
auc_all = summary[summary['Metric'].str.contains('AUC', na=False)].copy()

# Create summary
auc_summary_data = []

for mechanism in ['full', 'mcar', 'mar', 'mnar']:
    for model in ['RSF', 'XGBoost', 'GradientBoosting', 'DeepSurv']:
        row = {
            'Mechanism': mechanism.upper() if mechanism != 'full' else 'Real Data',
            'Model': model
        }
        
        for day in [3, 7, 14]:
            metric = f'AUC_Day{day}'
            auc_vals = auc_all[
                (auc_all['Mechanism'] == mechanism) &
                (auc_all['Model'] == model) &
                (auc_all['Metric'] == metric)
            ]['Mean'].values
            
            if len(auc_vals) > 0:
                # Average across imputations
                row[f'AUC Day {day}'] = f"{auc_vals.mean():.3f}"
            else:
                row[f'AUC Day {day}'] = '—'
        
        auc_summary_data.append(row)

table5 = pd.DataFrame(auc_summary_data)

table5.to_csv('Table5_AUC_summary.csv', index=False)
print("\nSaved: Table5_AUC_summary.csv")
print("\nPreview:")
print(table5.head(12))

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================

print("\n" + "="*70)
print("SUMMARY STATISTICS FOR TEXT")
print("="*70)

# Best overall performance
best_overall = summary[
    (summary['Metric'] == 'C-index (Test)') &
    (summary['Mechanism'].isin(['full', 'mcar', 'mar', 'mnar']))
].sort_values('Mean', ascending=False).iloc[0]

print(f"\nBEST OVERALL PERFORMANCE:")
print(f"   Model: {best_overall['Model']}")
print(f"   Imputation: {best_overall['Imputation']}")
print(f"   Mechanism: {best_overall['Mechanism']}")
print(f"   Test C-index: {best_overall['Mean']:.3f}")

# Best on real data
best_real = summary[
    (summary['Metric'] == 'C-index (Test)') &
    (summary['Mechanism'] == 'full')
].sort_values('Mean', ascending=False).iloc[0]

print(f"\nBEST ON REAL MIMIC-IV DATA:")
print(f"   Model: {best_real['Model']}")
print(f"   Imputation: {best_real['Imputation']}")
print(f"   Test C-index: {best_real['Mean']:.3f}")

# Best AUC Day 7 (most clinically relevant)
best_auc7 = summary[
    (summary['Metric'] == 'AUC_Day7') &
    (summary['Mechanism'] == 'full')
].sort_values('Mean', ascending=False).iloc[0]

print(f"\nBEST TIME-DEPENDENT AUC (Day 7):")
print(f"   Model: {best_auc7['Model']}")
print(f"   Imputation: {best_auc7['Imputation']}")
print(f"   AUC Day 7: {best_auc7['Mean']:.3f}")

# Average AUC across time points for best model
best_model = best_real['Model']
best_imp = best_real['Imputation']

print(f"\nTIME-DEPENDENT AUC for {best_model} + {best_imp}:")
for day in [3, 7, 14]:
    auc_val = summary[
        (summary['Model'] == best_model) &
        (summary['Imputation'] == best_imp) &
        (summary['Mechanism'] == 'full') &
        (summary['Metric'] == f'AUC_Day{day}')
    ]['Mean'].values
    
    if len(auc_val) > 0:
        print(f"   Day {day}: {auc_val[0]:.3f}")

print("\n" + "="*70)
print("ALL TABLES GENERATED SUCCESSFULLY!")
print("="*70)
print("\nGenerated CSV files:")
print("  1. Table1_main_results_with_AUC.csv")
print("  2. Table2_imputation_comparison.csv")
print("  3. Table3_model_ranking_with_AUC.csv")
print("  4. Table4_variable_importance.csv")
print("  5. Table5_AUC_summary.csv")
print("\nAll tables now include time-dependent AUC metrics!")
print("Use these CSV files to create your publication tables!")
