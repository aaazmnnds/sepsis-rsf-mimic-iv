import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sksurv.ensemble import RandomSurvivalForest
from sksurv.util import Surv
from lifelines import KaplanMeierFitter
from sklearn.preprocessing import OneHotEncoder

def generate_km_curves():
    print("Loading data from 'synthetic_complete.csv'...")
    df = pd.read_csv("synthetic_complete.csv")
    
    # Preprocessing
    # 1. Encode Categorical (Sex)
    df = pd.get_dummies(df, columns=["Sex"], drop_first=True)
    
    # 2. X and y
    X = df.drop(columns=["Time", "Event"])
    y = Surv.from_dataframe("Event", "Time", df)
    
    print(f"Training Random Survival Forest on n={len(df)} subjects...")
    # Use OOB Score to get unbiased predictions for the training set
    rsf = RandomSurvivalForest(
        n_estimators=1000,
        min_samples_split=10,
        min_samples_leaf=15,
        n_jobs=-1,
        random_state=42,
        oob_score=True 
    )
    rsf.fit(X, y)
    
    print("Generating Risk Scores...")
    # Try to use OOB predictions if available, else standard predict
    try:
        risk_scores = rsf.oob_prediction_
        print("Using OOB predictions.")
    except AttributeError:
        print("OOB predictions not available (check sksurv version). Using standard prediction.")
        risk_scores = rsf.predict(X)
        
    # Create Risk Groups (Median Split)
    median_risk = np.median(risk_scores)
    risk_group = np.where(risk_scores >= median_risk, "High Risk", "Low Risk")
    
    # Prepare Data for Lifelines
    T = df["Time"]
    E = df["Event"]
    
    kmf = KaplanMeierFitter()
    
    plt.figure(figsize=(10, 8))
    sns.set_style("whitegrid")
    
    # Plot High Risk
    mask_high = risk_group == "High Risk"
    kmf.fit(T[mask_high], E[mask_high], label=f"High Risk (n={sum(mask_high)})")
    kmf.plot_survival_function(color="red", ci_show=True)
    
    # Plot Low Risk
    mask_low = risk_group == "Low Risk"
    kmf.fit(T[mask_low], E[mask_low], label=f"Low Risk (n={sum(mask_low)})")
    kmf.plot_survival_function(color="blue", ci_show=True)
    
    plt.title("Kaplan-Meier Survival Curves by RSF Predicted Risk (Simulated Cohort, n=852)", fontsize=14)
    plt.xlabel("Time (days)", fontsize=12)
    plt.ylabel("Survival Probability", fontsize=12)
    plt.legend(title="Risk Group", loc="upper right")
    plt.ylim(0, 1.05)
    
    output_file = "survival_curves_all_subjects1.png"
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Saved '{output_file}'")

if __name__ == "__main__":
    generate_km_curves()
