import pandas as pd

df = pd.read_csv("model_predictions.csv")
print(f"Total rows in model_predictions: {len(df)}")

# Standard evaluation uses the 'full' mechanism for the main cohort usually.
# Let's see some samples to understand the structure.
print("\nFirst 5 rows:")
print(df.head())

# Filter for the test set.
# In this project, usually the predictions are only for the test set if it's 'model_predictions.csv'.
# Let's check the number of unique subjects.
print(f"\nUnique subjects: {df['Subject_ID'].nunique()}")

# Filter for Day 7 events.
day7_events = df[(df['Observed_Status'] == 1) & (df['Observed_Time'] <= 7)]
print(f"\nTotal events in dataset with Time <= 7: {len(day7_events)}")

# If the predictions are per model/imputation, we need to check one specific combination (e.g., RSF-GAIN).
rsf_gain = df[(df['Model'] == 'RSF') & (df['Imputation'] == 'GAIN')]
print(f"\nRSF-GAIN test set size: {len(rsf_gain)}")
rsf_gain_day7 = rsf_gain[(rsf_gain['Observed_Status'] == 1) & (rsf_gain['Observed_Time'] <= 7)]
print(f"RSF-GAIN events with Time <= 7: {len(rsf_gain_day7)}")

# Let's check DeepSurv-GAIN too.
ds_gain = df[(df['Model'] == 'DeepSurv') & (df['Imputation'] == 'GAIN')]
print(f"\nDeepSurv-GAIN test set size: {len(ds_gain)}")
ds_gain_day7 = ds_gain[(ds_gain['Observed_Status'] == 1) & (ds_gain['Observed_Time'] <= 7)]
print(f"DeepSurv-GAIN events with Time <= 7: {len(ds_gain_day7)}")