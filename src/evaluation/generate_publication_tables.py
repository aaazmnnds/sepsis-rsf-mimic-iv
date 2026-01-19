"""
Generate Publication Tables from Survival Analysis Results
Author: Results Reporting Script
Date: 2026-01-06
"""

import pandas as pd
import numpy as np

# Load data
summary = pd.read_csv('model_performance_summary.csv')
vimp = pd.read_csv('variable_importance.csv')

print("="*70)
print("TABLE 1: MAIN RESULTS - REAL MIMIC-IV DATA")
print("="*70)

# Filter for real data
df_real = summary[summary['Mechanism'] == 'full'].copy()

# Separate metrics
cv_data = df_real[df_real['Metric'] == 'C-index (CV)'][['Imputation', 'Model', 'Formatted']]
test_data = df_real[df_real['Metric'] == 'C-index (Test)'][['Imputation', 'Model', 'Mean']]
ibs_data = df_real[df_real['Metric'] == 'IBS (Test)'][['Imputation', 'Model', 'Mean']]

# Create combined table
table1_data = []
for imp in ['MICE (pooled)', 'missForest', 'GAIN', 'MIDA']:
    row = {'Imputation': imp}
    for model in ['RSF', 'XGBoost', 'GradientBoosting', 'DeepSurv']:
        # CV C-index with CI
        cv_val = cv_data[(cv_data['Imputation']==imp) & (cv_data['Model']==model)]['Formatted'].values
        cv_str = cv_val[0] if len(cv_val) > 0 else '—'
        
        # Test C-index
        test_val = test_data[(test_data['Imputation']==imp) & (test_data['Model']==model)]['Mean'].values
        test_str = f"{test_val[0]:.3f}" if len(test_val) > 0 else '—'
        
        # IBS
        ibs_val = ibs_data[(ibs_data['Imputation']==imp) & (ibs_data['Model']==model)]['Mean'].values
        ibs_str = f"{ibs_val[0]:.3f}" if len(ibs_val) > 0 else '—'
        
        row[f'{model}_CV'] = cv_str
        row[f'{model}_Test'] = test_str
        row[f'{model}_IBS'] = ibs_str
    
    table1_data.append(row)

table1 = pd.DataFrame(table1_data)
print("\nTable 1: Model Performance on MIMIC-IV Data (n=852)")
print(table1.to_string(index=False))

# Save to CSV and LaTeX
table1.to_csv('Table1_main_results.csv', index=False)
print("\nSaved to Table1_main_results.csv")

print("\n" + "="*70)
print("TABLE 2: IMPUTATION METHOD COMPARISON BY MECHANISM")
print("="*70)

# Focus on RSF (primary model) across mechanisms
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

print("\nTable 2: RSF C-index (CV) Across Missing Data Mechanisms")
print(table2)

table2.to_csv('Table2_imputation_comparison.csv')
print("\nSaved to Table2_imputation_comparison.csv")

print("\n" + "="*70)
print("TABLE 3: MODEL RANKING SUMMARY")
print("="*70)

# Average performance across best imputation method
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
        
        # Get corresponding CV and IBS
        cv_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'C-index (CV)')
        ]
        
        ibs_row = summary[
            (summary['Model'] == model) &
            (summary['Imputation'] == best_row['Imputation']) &
            (summary['Mechanism'] == 'full') &
            (summary['Metric'] == 'IBS (Test)')
        ]
        
        best_performers.append({
            'Model': model,
            'Best Imputation': best_row['Imputation'],
            'CV C-index': cv_row['Formatted'].values[0] if len(cv_row) > 0 else '—',
            'Test C-index': f"{best_row['Mean']:.3f}",
            'IBS': f"{ibs_row['Mean'].values[0]:.3f}" if len(ibs_row) > 0 else '—'
        })

table3 = pd.DataFrame(best_performers)
table3 = table3.sort_values('Test C-index', ascending=False)
table3['Rank'] = range(1, len(table3) + 1)

print("\nTable 3: Model Performance Summary (Best Imputation per Model)")
print(table3.to_string(index=False))

table3.to_csv('Table3_model_ranking.csv', index=False)
print("\nSaved to Table3_model_ranking.csv")

print("\n" + "="*70)
print("TABLE 4: VARIABLE IMPORTANCE (Top 10)")
print("="*70)

# Focus on real MIMIC data with best performing combination
# From your results, MIDA or GAIN with RSF performed best
# Let's use the full dataset results

df_vimp = vimp[
    (vimp['Mechanism'] == 'full') & 
    (vimp['Model'] == 'RSF')
].copy()

# Average across imputations if multiple exist
vimp_summary = df_vimp.groupby('Feature').agg({
    'Importance_Mean': 'mean',
    'Importance_Std': 'mean'
}).reset_index()

# Sort and take top 10
vimp_summary = vimp_summary.sort_values('Importance_Mean', ascending=False).head(10)
vimp_summary['Rank'] = range(1, len(vimp_summary) + 1)

# Format for publication
vimp_summary['Importance'] = vimp_summary['Importance_Mean'].apply(lambda x: f"{x:.4f}")
vimp_summary['Std'] = vimp_summary['Importance_Std'].apply(lambda x: f"{x:.4f}")

table4 = vimp_summary[['Rank', 'Feature', 'Importance', 'Std']]

print("\nTable 4: Top 10 Predictive Features (RSF Permutation Importance)")
print(table4.to_string(index=False))

table4.to_csv('Table4_variable_importance.csv', index=False)
print("\nSaved to Table4_variable_importance.csv")

print("\n" + "="*70)
print("SUMMARY STATISTICS FOR TEXT")
print("="*70)

# Best overall result
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

# MICE performance (important baseline)
mice_rsf_real = summary[
    (summary['Imputation'] == 'MICE (pooled)') &
    (summary['Model'] == 'RSF') &
    (summary['Mechanism'] == 'full') &
    (summary['Metric'] == 'C-index (CV)')
]

if len(mice_rsf_real) > 0:
    print(f"\nMICE + RSF ON REAL DATA (Baseline):")
    print(f"   CV C-index: {mice_rsf_real['Formatted'].values[0]}")
    
    mice_test = summary[
        (summary['Imputation'] == 'MICE (pooled)') &
        (summary['Model'] == 'RSF') &
        (summary['Mechanism'] == 'full') &
        (summary['Metric'] == 'C-index (Test)')
    ]
    if len(mice_test) > 0:
        print(f"   Test C-index: {mice_test['Mean'].values[0]:.3f}")

# Performance difference between best and worst imputation
for model in ['RSF']:
    model_full = summary[
        (summary['Model'] == model) &
        (summary['Mechanism'] == 'full') &
        (summary['Metric'] == 'C-index (Test)')
    ].copy()
    
    if len(model_full) > 0:
        best = model_full['Mean'].max()
        worst = model_full['Mean'].min()
        diff = best - worst
        
        print(f"\n{model} - IMPUTATION IMPACT:")
        print(f"   Best: {best:.3f}")
        print(f"   Worst: {worst:.3f}")
        print(f"   Difference: {diff:.3f} ({diff/worst*100:.1f}% relative improvement)")

print("\n" + "="*70)
print("ALL TABLES GENERATED")
print("="*70)
print("\nGenerated files:")
print("  - Table1_main_results.csv")
print("  - Table2_imputation_comparison.csv")
print("  - Table3_model_ranking.csv")
print("  - Table4_variable_importance.csv")
print("\nUse these for your manuscript!")
