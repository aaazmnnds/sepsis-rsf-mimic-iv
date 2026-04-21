"""
Generate BMC LaTeX Tables from CSV Files with Time-Dependent AUC
Reads the actual CSV files and creates publication-ready LaTeX tables
"""

import pandas as pd
import numpy as np

# Load all tables
print("Loading CSV files...")
table1 = pd.read_csv('Table1_main_results_with_AUC.csv')
table2 = pd.read_csv('Table2_imputation_comparison.csv')
table3 = pd.read_csv('Table3_model_ranking_with_AUC.csv')
table4 = pd.read_csv('Table4_variable_importance.csv')
table5 = pd.read_csv('Table5_AUC_summary.csv')

print("All CSV files loaded successfully\n")

# ============================================================================
# TABLE 1: MAIN RESULTS WITH AUC
# ============================================================================

def generate_table1_latex():
    """Generate Table 1: Main Results on Real MIMIC-IV Data"""

    latex = []
    latex.append(r"% Table 1: Model Performance on Real MIMIC-IV Data with Time-Dependent AUC")
    latex.append(r"\begin{table*}[!ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Model performance on real MIMIC-IV sepsis cohort with time-dependent AUC (n=852)}")
    latex.append(r"\label{tab:main_results_auc}")
    latex.append(r"\small")
    latex.append(r"\begin{tabular}{@{}lcccccccc@{}}")
    latex.append(r"\toprule")
    latex.append(r"& \multicolumn{2}{c}{\textbf{RSF}} & \multicolumn{2}{c}{\textbf{XGBoost}} & \multicolumn{2}{c}{\textbf{Gradient Boosting}} & \multicolumn{2}{c}{\textbf{DeepSurv}} \\")
    latex.append(r"\cmidrule(lr){2-3} \cmidrule(lr){4-5} \cmidrule(lr){6-7} \cmidrule(lr){8-9}")
    latex.append(r"\textbf{Imputation} & \textbf{CV} & \textbf{Test} & \textbf{CV} & \textbf{Test} & \textbf{CV} & \textbf{Test} & \textbf{CV} & \textbf{Test} \\")
    latex.append(r"\midrule")

    models = ['RSF', 'XGBoost', 'GradientBoosting', 'DeepSurv']

    for _, row in table1.iterrows():
        imp = row['Imputation'].replace('_', r'\_')

        # Build row with CV and Test for each model
        row_vals = [imp]
        for model in models:
            cv = row[f'{model}_CV']
            test = row[f'{model}_Test']
            row_vals.extend([cv, test])

        latex.append("  & " + " & ".join([str(x) for x in row_vals[1:]]) + r" \\")

        # Add CI line (extract from CV values)
        ci_vals = ['']
        for model in models:
            cv_full = str(row[f'{model}_CV'])
            if '(' in cv_full:
                ci = cv_full.split('(')[1].replace(')', '')
                ci_vals.extend([r"\scriptsize (" + ci + ")", ''])
            else:
                ci_vals.extend(['', ''])

        latex.append("  & " + " & ".join(ci_vals[1:]) + r" \\[0.5ex]")

    latex.append(r"\midrule")
    latex.append(r"\multicolumn{9}{l}{\textbf{Integrated Brier Score (IBS)}} \\")
    latex.append(r"\midrule")

    # IBS row
    ibs_vals = [r'\textbf{IBS}']
    for model in models:
        ibs_col = f'{model}_IBS'
        ibs_data = table1[ibs_col].values
        ibs_data = [x for x in ibs_data if x != '—']
        if ibs_data:
            ibs_min = min([float(x) for x in ibs_data])
            ibs_max = max([float(x) for x in ibs_data])
            ibs_vals.append(r"\multicolumn{2}{c}{" + f"{ibs_min:.3f}--{ibs_max:.3f}" + r"}")
        else:
            ibs_vals.append(r"\multicolumn{2}{c}{—}")

    latex.append("  & " + " & ".join(ibs_vals[1:]) + r" \\")

    latex.append(r"\midrule")
    latex.append(r"\multicolumn{9}{l}{\textbf{Time-Dependent AUC (Averaged Across Imputations)}} \\")
    latex.append(r"\midrule")

    # AUC rows
    for day in [3, 7, 14]:
        auc_vals = [f'Day {day}']
        for model in models:
            auc_col = f'{model}_AUC{day}'
            auc_data = table1[auc_col].values
            auc_data = [float(x) for x in auc_data if x != '—']
            if auc_data:
                auc_mean = np.mean(auc_data)
                auc_vals.append(r"\multicolumn{2}{c}{" + f"{auc_mean:.3f}" + r"}")
            else:
                auc_vals.append(r"\multicolumn{2}{c}{—}")

        latex.append("  & " + " & ".join(auc_vals[1:]) + r" \\")

    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\begin{flushleft}")
    latex.append(r"\footnotesize")
    latex.append("CV = Cross-validated C-index (10-fold), reported as Mean with 95\\% CI in parentheses. Test = C-index on held-out test set (10\\%). IBS = Integrated Brier Score (range across imputation methods; lower is better). Time-dependent AUC shown at 3, 7, and 14 days post-surgery, averaged across imputation methods. For MICE, Rubin's pooled estimates shown. — indicates metric not available for model.")
    latex.append(r"\end{flushleft}")
    latex.append(r"\end{table*}")

    return "\n".join(latex)

# ============================================================================
# TABLE 2: IMPUTATION COMPARISON
# ============================================================================

def generate_table2_latex():
    """Generate Table 2: Imputation Comparison"""

    latex = []
    latex.append(r"\begin{table}[!ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Random Survival Forest C-index across missing data mechanisms (simulated data, n=852)}")
    latex.append(r"\label{tab:imputation_comparison}")
    latex.append(r"\begin{tabular}{@{}lcccc@{}}")
    latex.append(r"\toprule")

    # Get column names (imputation methods)
    cols = [c for c in table2.columns if c != 'Mechanism']
    header = r"\textbf{Mechanism} & " + " & ".join([r"\textbf{" + c.replace('_', r'\_') + r"}" for c in cols])
    latex.append(header + r" \\")
    latex.append(r"\midrule")

    for _, row in table2.iterrows():
        mech = row['Mechanism'].upper()
        vals = [mech]
        for col in cols:
            val = str(row[col])
            vals.append(val)

        latex.append(" & ".join(vals) + r" \\")

        # CI line
        ci_vals = ['']
        for col in cols:
            val = str(row[col])
            if '(' in val:
                ci = val.split('(')[1].replace(')', '')
                ci_vals.append(r"\scriptsize (" + ci + ")")
            else:
                ci_vals.append('')

        latex.append("     & " + " & ".join(ci_vals[1:]) + r" \\[0.5ex]")

    # Calculate average
    latex.append(r"\midrule")
    avg_vals = [r'\textbf{Average}']
    for col in cols:
        vals = []
        for val_str in table2[col].values:
            if '(' in str(val_str):
                mean_str = str(val_str).split('(')[0].strip()
                try:
                    vals.append(float(mean_str))
                except:
                    pass
        if vals:
            avg_vals.append(f"\\textbf{{{np.mean(vals):.3f}}}")
        else:
            avg_vals.append('—')

    latex.append(" & ".join(avg_vals) + r" \\")
    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\begin{flushleft}")
    latex.append(r"\footnotesize")
    latex.append("Values are cross-validated C-index as Mean with 95\\% CI (10-fold CV). MCAR = Missing Completely At Random, MAR = Missing At Random, MNAR = Missing Not At Random. Deep learning methods (GAIN, MIDA) outperformed traditional methods (MICE, missForest) across all mechanisms.")
    latex.append(r"\end{flushleft}")
    latex.append(r"\end{table}")

    return "\n".join(latex)

# ============================================================================
# TABLE 3: MODEL RANKING WITH AUC
# ============================================================================

def generate_table3_latex():
    """Generate Table 3: Model Ranking with AUC"""

    latex = []
    latex.append(r"\begin{table}[!ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Comparative performance of survival models on real MIMIC-IV data with time-dependent AUC}")
    latex.append(r"\label{tab:model_ranking_auc}")
    latex.append(r"\small")
    latex.append(r"\begin{tabular}{@{}clcccccc@{}}")
    latex.append(r"\toprule")
    latex.append(r"\textbf{Rank} & \textbf{Model} & \textbf{Best Imputation} & \textbf{CV C-index} & \textbf{Test C-index} & \textbf{IBS} & \textbf{AUC (Day 7)} & \textbf{AUC (Day 14)} \\")
    latex.append(r"\midrule")

    for _, row in table3.iterrows():
        rank = int(row['Rank'])
        model = row['Model']
        imp = row['Best Imputation'].replace('_', r'\_')
        cv = row['CV C-index']
        test = row['Test C-index']
        ibs = row['IBS']
        auc7 = row['AUC Day 7']
        auc14 = row['AUC Day 14']

        latex.append(f"{rank} & {model} & {imp} & {cv} & {test} & {ibs} & {auc7} & {auc14} " + r"\\")

        # CI line
        if '(' in str(cv):
            ci = str(cv).split('(')[1].replace(')', '')
            latex.append(f"  &   &    & \\scriptsize ({ci}) &  &  &  &  " + r"\\[0.5ex]")
        else:
            latex.append(r"[0.5ex]")

    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\begin{flushleft}")
    latex.append(r"\footnotesize")
    latex.append("Models ranked by test C-index using optimal imputation. CV C-index: Mean (95\\% CI) from 10-fold CV. IBS = Integrated Brier Score (lower is better). AUC shown at 7 and 14 days post-surgery. — indicates metric unavailable.")
    latex.append(r"\end{flushleft}")
    latex.append(r"\end{table}")

    return "\n".join(latex)

# ============================================================================
# TABLE 4: VARIABLE IMPORTANCE
# ============================================================================

def generate_table4_latex():
    """Generate Table 4: Variable Importance"""

    # Feature name mapping
    feature_names = {
        'Plt': 'Platelet count (Plt)',
        'GCS': 'Glasgow Coma Scale (GCS)',
        'Lac': 'Lactate (Lac)',
        'RR': 'Respiratory rate (RR)',
        'Cl': 'Chloride (Cl)',
        'ALT': 'Alanine aminotransferase (ALT)',
        'Na': 'Sodium (Na)',
        'subject_id': r'Subject ID$^{\text{a}}$',
        'AST': 'Aspartate aminotransferase (AST)',
        'HR': 'Heart rate (HR)',
        'Age': 'Age',
        'Sex': 'Sex',
        'Sex_M': 'Sex (Male)'
    }

    latex = []
    latex.append(r"\begin{table}[!ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Top 10 predictive features from Random Survival Forest (MIMIC-IV data)}")
    latex.append(r"\label{tab:variable_importance}")
    latex.append(r"\begin{tabular}{@{}clcc@{}}")
    latex.append(r"\toprule")
    latex.append(r"\textbf{Rank} & \textbf{Feature} & \textbf{Importance} & \textbf{Std. Dev.} \\")
    latex.append(r"\midrule")

    for _, row in table4.iterrows():
        rank = int(row['Rank'])
        feature_raw = row['Feature']
        feature = feature_names.get(feature_raw, feature_raw)
        importance = row['Importance']
        std = row['Std']

        latex.append(f"{rank} & {feature} & {importance} & {std} " + r"\\")

    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\begin{flushleft}")
    latex.append(r"\footnotesize")
    latex.append("Variable importance via permutation importance on test set (n=5 repetitions). Values represent mean decrease in C-index when feature values are randomly permuted. $^{\\text{a}}$Subject ID is a data artifact; exclude in clinical deployment.")
    latex.append(r"\end{flushleft}")
    latex.append(r"\end{table}")

    return "\n".join(latex)

# ============================================================================
# TABLE 5: TIME-DEPENDENT AUC SUMMARY (NEW!)
# ============================================================================

def generate_table5_latex():
    """Generate Table 5: Time-Dependent AUC Summary"""

    latex = []
    latex.append(r"\begin{table*}[!ht]")
    latex.append(r"\centering")
    latex.append(r"\caption{Time-dependent AUC across missing data mechanisms and survival models}")
    latex.append(r"\label{tab:auc_summary}")
    latex.append(r"\small")
    latex.append(r"\begin{tabular}{@{}llccc@{}}")
    latex.append(r"\toprule")
    latex.append(r"\textbf{Dataset} & \textbf{Model} & \textbf{AUC Day 3} & \textbf{AUC Day 7} & \textbf{AUC Day 14} \\")
    latex.append(r"\midrule")

    # Group by mechanism
    for mech in table5['Mechanism'].unique():
        latex.append(r"\multicolumn{5}{l}{\textit{" + mech + r"}} \\")

        mech_data = table5[table5['Mechanism'] == mech]
        for _, row in mech_data.iterrows():
            model = row['Model']
            auc3 = row['AUC Day 3']
            auc7 = row['AUC Day 7']
            auc14 = row['AUC Day 14']

            latex.append(f"  & {model} & {auc3} & {auc7} & {auc14} " + r"\\")

        latex.append(r"[0.3ex]")

    latex.append(r"\bottomrule")
    latex.append(r"\end{tabular}")
    latex.append(r"\begin{flushleft}")
    latex.append(r"\footnotesize")
    latex.append("Time-dependent AUC (area under ROC curve) at 3, 7, and 14 days post-surgery, averaged across imputation methods. Real Data = MIMIC-IV; MCAR, MAR, MNAR = simulated missing data mechanisms. AUC ranges from 0 (poor) to 1 (perfect discrimination). Values near 1.0 indicate excellent predictive ability at that time point.")
    latex.append(r"\end{flushleft}")
    latex.append(r"\end{table*}")

    return "\n".join(latex)

# ============================================================================
# GENERATE ALL TABLES
# ============================================================================

print("="*70)
print("GENERATING BMC LaTeX TABLES")
print("="*70)

table1_tex = generate_table1_latex()
with open('Table1_BMC_LaTeX_AUC.tex', 'w') as f:
    f.write(table1_tex)
print("Generated: Table1_BMC_LaTeX_AUC.tex")

table2_tex = generate_table2_latex()
with open('Table2_BMC_LaTeX_AUC.tex', 'w') as f:
    f.write(table2_tex)
print("Generated: Table2_BMC_LaTeX_AUC.tex")

table3_tex = generate_table3_latex()
with open('Table3_BMC_LaTeX_AUC.tex', 'w') as f:
    f.write(table3_tex)
print("Generated: Table3_BMC_LaTeX_AUC.tex")

table4_tex = generate_table4_latex()
with open('Table4_BMC_LaTeX_AUC.tex', 'w') as f:
    f.write(table4_tex)
print("Generated: Table4_BMC_LaTeX_AUC.tex")

table5_tex = generate_table5_latex()
with open('Table5_BMC_LaTeX_AUC.tex', 'w') as f:
    f.write(table5_tex)
print("Generated: Table5_BMC_LaTeX_AUC.tex")

# Create complete document
complete_doc = r"""\documentclass{article}
\usepackage{booktabs}
\usepackage{multirow}
\usepackage{array}
\usepackage[table]{xcolor}
\usepackage[margin=1in]{geometry}

\begin{document}

\section*{Tables for Results Section (WITH TIME-DEPENDENT AUC)}

"""

complete_doc += table1_tex + "\n\n\\clearpage\n\n"
complete_doc += table2_tex + "\n\n\\clearpage\n\n"
complete_doc += table3_tex + "\n\n\\clearpage\n\n"
complete_doc += table4_tex + "\n\n\\clearpage\n\n"
complete_doc += table5_tex + "\n\n"
complete_doc += r"\end{document}"

with open('All_BMC_Tables_with_AUC_Complete.tex', 'w') as f:
    f.write(complete_doc)
print("Generated: All_BMC_Tables_with_AUC_Complete.tex")

print("\n" + "="*70)
print("ALL BMC LaTeX TABLES GENERATED!")
print("="*70)
print("\nGenerated files:")
print("  1. Table1_BMC_LaTeX_AUC.tex (Main results with AUC)")
print("  2. Table2_BMC_LaTeX_AUC.tex (Imputation comparison)")
print("  3. Table3_BMC_LaTeX_AUC.tex (Model ranking with AUC)")
print("  4. Table4_BMC_LaTeX_AUC.tex (Variable importance)")
print("  5. Table5_BMC_LaTeX_AUC.tex (Time-dependent AUC summary)")
print("  6. All_BMC_Tables_with_AUC_Complete.tex (Complete document)")
print("\nAll tables include time-dependent AUC at Days 3, 7, and 14!")
print("Ready for BMC journal submission!")