"""
Fix Dataset Column Names
========================
Standardizes column names for survival analysis scripts.
Renames 'Time' -> 'Survival_Time' and 'Event' -> 'Status'.
"""

import pandas as pd
import glob
import os

def fix_columns():
    # Get all imputed files
    files = glob.glob("imputed_*.csv")
    
    # Also include the primary dataset if it exists
    if os.path.exists("mimic_sepsis_cohort_full.csv"):
        files.append("mimic_sepsis_cohort_full.csv")
        
    print(f"Found {len(files)} files to fix...")

    for file in files:
        try:
            df = pd.read_csv(file)
            changed = False
            
            # Rename Time -> Survival_Time
            if 'Time' in df.columns:
                df = df.rename(columns={'Time': 'Survival_Time'})
                changed = True
                
            # Rename Event -> Status
            if 'Event' in df.columns:
                df = df.rename(columns={'Event': 'Status'})
                changed = True
            
            if changed:
                # Save back
                df.to_csv(file, index=False)
                print(f"Fixed columns in: {file}")
            else:
                print(f"No changes needed for: {file}")
                
        except Exception as e:
            print(f"Error processing {file}: {e}")

    print("\nAll files checked and fixed! Columns 'Survival_Time' and 'Status' are ready.")

if __name__ == "__main__":
    fix_columns()
