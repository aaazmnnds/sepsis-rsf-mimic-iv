
import pandas as pd
import os

files = ["model_performance_results.csv", "model_performance_summary.csv", "variable_importance.csv"]

print(f"{'File':<35} | {'Exists':<8} | {'Models Found'}")
print("-" * 70)

for f in files:
    if os.path.exists(f):
        try:
            df = pd.read_csv(f)
            if "Model" in df.columns:
                models = df["Model"].unique().tolist()
                print(f"{f:<35} | Yes      | {models}")
            else:
                print(f"{f:<35} | Yes      | [No 'Model' column]")
        except Exception as e:
            print(f"{f:<35} | Yes      | Error reading: {e}")
    else:
        print(f"{f:<35} | No       | -")
