import pandas as pd
import numpy as np

def format_cont(series):
    # Check for normality? Simplified: Report Mean (SD) for Age, Median [IQR] for others
    # Actually paper said: "means ± standard deviations for normally distributed... medians [interquartile ranges] for non-normal"
    # We will assume Age is normal, others are skewed (common in sepsis)

    if series.name == "Age":
        return f"{series.mean():.1f} ({series.std():.1f})"
    else:
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        return f"{series.median():.1f} [{q1:.1f}, {q3:.1f}]"

def generate_table1():
    print("Loading data...")
    try:
        df = pd.read_csv("synthetic_complete.csv")
    except FileNotFoundError:
        print("Error: synthetic_complete.csv not found.")
        return

    # Total N
    n_total = len(df)

    # Sex
    n_male = df["Sex"].value_counts().get("M", 0)
    p_male = (n_male / n_total) * 100
    n_female = df["Sex"].value_counts().get("F", 0)
    p_female = (n_female / n_total) * 100

    # Define variables and display names
    vars_map = {
        "Age": "Age (years)",
        "Sex": "Male Sex, n (%)",
        "HR": "Heart Rate (bpm)",
        "RR": "Respiratory Rate (bpm)",
        "GCS": "Glasgow Coma Scale",
        "Lac": "Lactate (mmol/L)",
        "Plt": "Platelet Count (10^9/L)",
        "Cl": "Chloride (mmol/L)",
        "Na": "Sodium (mmol/L)",
        "ALT": "ALT (U/L)",
        "AST": "AST (U/L)",
        "Survival_Time": "Length of Stay (days)"
    }

    # Mappings if columns strictly match CSV headers (Assume they do from head command earlier)
    # Earlier head: Age,ALT,Sex,HR,RR,GCS,Cl,Lac,Plt,Na,AST,Time,Event

    # Rename for easier access
    if "Time" in df.columns: df.rename(columns={"Time": "Survival_Time"}, inplace=True)

    rows = []

    # 1. Demographics
    rows.append(r"\multicolumn{2}{l}{\textbf{Demographics}} \\")
    rows.append(f"Age (years), Mean (SD) & {format_cont(df['Age'])} \\\\")
    rows.append(f"Male Sex, n (\%) & {n_male} ({p_male:.1f}) \\\\")

    # 2. Vitals
    rows.append(r"\multicolumn{2}{l}{\textbf{Vital Signs}} \\")
    rows.append(f"Heart Rate (bpm) & {format_cont(df['HR'])} \\\\")
    rows.append(f"Respiratory Rate (breaths/min) & {format_cont(df['RR'])} \\\\")
    rows.append(f"Glasgow Coma Scale & {format_cont(df['GCS'])} \\\\")

    # 3. Labs
    rows.append(r"\multicolumn{2}{l}{\textbf{Laboratory Values}} \\")
    rows.append(f"Lactate (mmol/L) & {format_cont(df['Lac'])} \\\\")
    rows.append(f"Platelet Count ($10^9$/L) & {format_cont(df['Plt'])} \\\\")
    rows.append(f"Sodium (mmol/L) & {format_cont(df['Na'])} \\\\")
    rows.append(f"Chloride (mmol/L) & {format_cont(df['Cl'])} \\\\")
    rows.append(f"ALT (U/L) & {format_cont(df['ALT'])} \\\\")
    rows.append(f"AST (U/L) & {format_cont(df['AST'])} \\\\")

    # 4. Outcomes
    rows.append(r"\multicolumn{2}{l}{\textbf{Outcomes}} \\")
    n_dead = df["Event"].sum()
    p_dead = (n_dead / n_total) * 100
    rows.append(f"In-hospital Mortality, n (\%) & {n_dead} ({p_dead:.1f}) \\\\")
    rows.append(f"Length of Stay (days) & {format_cont(df['Survival_Time'])} \\\\")

    # Construct LaTeX Table
    latex_table = r"""
\begin{table}[h]
\centering
\caption{Baseline Characteristics of the Study Cohort (n=""" + str(n_total) + r""")}
\label{tab:patient_characteristics}
\begin{tabular}{@{}lc@{}}
\toprule
\textbf{Characteristic} & \textbf{value} \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\multicolumn{2}{l}{\footnotesize Values are Median [IQR] unless outcome/sex (n, \%) or Age (Mean (SD)).}
\end{tabular}
\end{table}
"""

    print("Generated LaTeX Table:")
    print(latex_table)

    with open("table1_content.tex", "w") as f:
        f.write(latex_table)

if __name__ == "__main__":
    generate_table1()