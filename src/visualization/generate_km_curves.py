import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

def generate_km_curves():
    print("=" * 80)
    print("GENERATING KAPLAN-MEIER CURVES FROM OOB PREDICTIONS")
    print("=" * 80)

    # 1. LOAD PREDICTIONS
    print("\n1. Loading unbiased OOB predictions...")
    try:
        df = pd.read_csv("full_cohort_rsf_predictions.csv")
        print(f"   Loaded: full_cohort_rsf_predictions.csv (n={len(df)})")
    except FileNotFoundError:
        print("   ERROR: full_cohort_rsf_predictions.csv not found!")
        print("   Please run 'python src/evaluation/generate_full_cohort_predictions.py' first.")
        return

    # 2. IDENTIFY DATA COLUMNS
    T = df["Observed_Time"]
    E = df["Observed_Status"]
    groups = df["Risk_Group"]

    # 3. STATISTICAL TEST (Log-Rank)
    print("\n2. Calculating Log-Rank Test...")
    mask_high = (groups == "High")
    mask_low = (groups == "Low")

    results = logrank_test(T[mask_high], T[mask_low], event_observed_A=E[mask_high], event_observed_B=E[mask_low])
    p_value = results.p_value
    print(f"   Log-Rank p-value: {p_value:.4e}")

    # 4. PLOTTING
    print("\n3. Plotting KM Curves...")
    plt.figure(figsize=(10, 7))
    sns.set_style("whitegrid")

    kmf_high = KaplanMeierFitter()
    kmf_low = KaplanMeierFitter()

    # Plot High Risk
    kmf_high.fit(T[mask_high], E[mask_high], label=f"High Risk (n={sum(mask_high)})")
    ax = kmf_high.plot_survival_function(color="#e74c3c", linewidth=2.5) # Sleek red

    # Plot Low Risk
    kmf_low.fit(T[mask_low], E[mask_low], label=f"Low Risk (n={sum(mask_low)})")
    kmf_low.plot_survival_function(ax=ax, color="#3498db", linewidth=2.5) # Sleek blue

    # Formatting
    plt.title("Risk Stratification for Sepsis Mortality (OOB Predictions)", fontsize=16, fontweight='bold', pad=20)
    plt.xlabel("Days Post-Surgery", fontsize=12)
    plt.ylabel("Survival Probability", fontsize=12)
    plt.ylim(0, 1.05)
    plt.xlim(0, max(T))
    plt.legend(title="Risk Group", fontsize=11, frameon=True)

    # Add p-value to plot
    plt.text(0.05, 0.05, f"Log-Rank p < {p_value:.1e}" if p_value < 0.001 else f"Log-Rank p = {p_value:.3f}",
             transform=ax.transAxes, fontsize=12, fontweight='bold', bbox=dict(facecolor='white', alpha=0.5))

    # 5. SURVIVAL PROBABILITIES AT 30 & 60 DAYS
    print("\n4. Survival Probabilities:")
    for days in [30, 60]:
        print(f"   At Day {days}:")
        try:
            surv_high = kmf_high.predict(days)
            surv_low = kmf_low.predict(days)
            print(f"     High Risk: {surv_high:.1%}")
            print(f"     Low Risk:  {surv_low:.1%}")
        except:
             print(f"     Day {days} is outside observed range for some groups.")

    # 6. SAVE
    output_file = "survival_curves_all_subjects1.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"\nSaved: {output_file}")

    print("\n" + "=" * 80)
    print("KM CURVE GENERATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    generate_km_curves()