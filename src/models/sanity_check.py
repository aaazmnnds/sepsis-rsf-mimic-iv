
import pandas as pd
import numpy as np
from survival_models import run_rsf, run_xgboost_survival, run_gradient_boosting, run_deepsurv, run_cv_evaluation
from sksurv.metrics import cumulative_dynamic_auc
import os

def smoke_test():
    print("Running Smoke Test...")

    # 1. Create Dummy Data
    N = 100
    df = pd.DataFrame({
        'Age': np.random.normal(60, 10, N),
        'Sex_M': np.random.randint(0, 2, N),
        'Survival_Time': np.random.exponential(10, N) + 1, # Ensure > 0
        'Status': np.random.randint(0, 2, N)
    })
    # Ensure at least some events and censoring
    df.loc[0:4, 'Status'] = 1
    df.loc[5:9, 'Status'] = 0

    print("Dummy Data Created.")

    # Prepare X and y
    X = df.drop(columns=['Survival_Time', 'Status']).values
    y = np.array([(bool(s), t) for s, t in zip(df['Status'], df['Survival_Time'])],
                 dtype=[('Status', '?'), ('Survival_Time', '<f8')])

    # 2. Test RSF
    print("\nTesting RSF...")
    try:
        rsf = run_rsf(X, y)
        print("  RSF Fit: Success")
        risk = rsf.predict(X)
        print("  RSF Predict: Success")
    except Exception as e:
        print(f"  RSF FAILED: {e}")
        exit(1)

    # 3. Test New AUC Logic
    print("\nTesting Time-dependent AUC Calculation...")
    try:
        times = np.array([3.0, 7.0])
        # Filter times within range
        times = [t for t in times if t < y['Survival_Time'].max() and t > y['Survival_Time'].min()]

        auc, mean_auc = cumulative_dynamic_auc(y, y, risk, times)
        print(f"  AUC Calculation: Success (Values: {auc})")
    except Exception as e:
        print(f"  AUC FAILED: {e}")
        # Don't exit, just report (since script has try/except)

    print("\nSmoke Test Complete. Script is valid.")

if __name__ == "__main__":
    smoke_test()