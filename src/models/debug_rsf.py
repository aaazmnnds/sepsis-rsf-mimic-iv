
import pandas as pd
import numpy as np
from sklearn.inspection import permutation_importance
from sksurv.ensemble import RandomSurvivalForest
from sksurv.util import Surv
from sklearn.model_selection import train_test_split

print("Starting Debug Script...")

try:
    # Generate dummy survival data
    X = pd.DataFrame(np.random.rand(100, 5), columns=[f"feat_{i}" for i in range(5)])
    time = np.random.uniform(10, 100, 100)
    event = np.random.randint(0, 2, 100).astype(bool)
    y = Surv.from_arrays(event=event, time=time)

    print("Data generated. Training RSF...")

    # Train RSF
    rsf = RandomSurvivalForest(n_estimators=10, random_state=42)
    rsf.fit(X, y)
    print("RSF Trained.")

    # Check VIMP
    print("Calculating Permutation Importance...")
    result = permutation_importance(rsf, X, y, n_repeats=2, random_state=42)
    print("Permutation Importance calculated:")
    print(result.importances_mean)

    print("SUCCESS: Environment is working.")

except Exception as e:
    print(f"FAILURE: {e}")