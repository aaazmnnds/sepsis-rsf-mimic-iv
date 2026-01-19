"""
MIMIC-IV Sepsis Cohort Extraction Script
========================================
This script extracts the sepsis cohort from MIMIC-IV database.
It performs the following steps:
1. Extracts base cohort (Sepsis + Surgical + Adults)
2. Extracts Laboratory Values (ALT, AST, Lactate, Sodium, Chloride, Platelets)
3. Extracts Vital Signs (Heart Rate, Respiratory Rate)
4. Extracts GCS Scores
5. Cleans and finalizes the dataset

Author: Azman Nads
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

MIMIC_PATH = '/Users/azmannads/Downloads/Dr. Zhang/mimic-iv-2.2/'
OUTPUT_PATH = '/Users/azmannads/Downloads/Dr. Zhang'
INTERMEDIATE_PATH = os.path.join(OUTPUT_PATH, 'intermediate')
FINAL_PATH = os.path.join(OUTPUT_PATH, 'final')
LOG_PATH = os.path.join(OUTPUT_PATH, 'logs')

# Create directories if they don't exist
Path(INTERMEDIATE_PATH).mkdir(parents=True, exist_ok=True)
Path(FINAL_PATH).mkdir(parents=True, exist_ok=True)
Path(LOG_PATH).mkdir(parents=True, exist_ok=True)

# Parameters
MIN_AGE = 18
SEPSIS_ICD10 = ['A40', 'A41', 'R65']
SEPSIS_ICD9 = ['995', '785']

# Item IDs
LAB_ITEMS = {
    'ALT': [50861],
    'AST': [50878],
    'Lactate': [50813],
    'Sodium': [50983, 50824],
    'Chloride': [50902, 50806],
    'Platelets': [51265]
}

VITAL_ITEMS = {
    'HR': [220045],
    'RR': [220210, 224690],
}

GCS_ITEMS = [220739, 223901, 223900, 198]

print("Configuration loaded successfully!")
print(f"   MIMIC Path: {MIMIC_PATH}")
print(f"   Output Path: {OUTPUT_PATH}")


def check_files():
    """Verify that all required MIMIC-IV files exist."""
    print("\nChecking files...")
    files_to_check = [
        'hosp/patients.csv.gz',
        'hosp/admissions.csv.gz',
        'hosp/diagnoses_icd.csv.gz',
        'hosp/labevents.csv.gz',
        'icu/icustays.csv.gz',
        'icu/chartevents.csv.gz'
    ]
    
    all_exist = True
    for file in files_to_check:
        full_path = os.path.join(MIMIC_PATH, file)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path) / (1024**3)
            print(f"  [OK] {file} ({size:.2f} GB)")
        else:
            print(f"  [MISSING] {file}")
            all_exist = False
    return all_exist


def step1_extract_base_cohort():
    """Extract base cohort of adult surgical sepsis patients."""
    print("\n" + "="*70)
    print("STEP 1: EXTRACTING BASE COHORT")
    print("="*70)

    # Load core tables
    print("\n1. Loading MIMIC-IV tables...")
    patients = pd.read_csv(f'{MIMIC_PATH}hosp/patients.csv.gz', compression='gzip')
    print(f"  Patients: {len(patients):,}")

    admissions = pd.read_csv(f'{MIMIC_PATH}hosp/admissions.csv.gz', compression='gzip')
    print(f"  Admissions: {len(admissions):,}")

    diagnoses = pd.read_csv(f'{MIMIC_PATH}hosp/diagnoses_icd.csv.gz', compression='gzip')
    print(f"  Diagnoses: {len(diagnoses):,}")

    # Identify sepsis
    print("\n2. Identifying sepsis patients...")
    all_sepsis_codes = SEPSIS_ICD10 + SEPSIS_ICD9
    sepsis_diagnoses = diagnoses[
        diagnoses['icd_code'].str.startswith(tuple(all_sepsis_codes), na=False)
    ]
    sepsis_hadm_ids = sepsis_diagnoses['hadm_id'].unique()
    print(f"  Sepsis admissions: {len(sepsis_hadm_ids):,}")

    # Filter surgical
    print("\n3. Filtering for surgical admissions...")
    surgical_sepsis = admissions[
        (admissions['hadm_id'].isin(sepsis_hadm_ids)) &
        (
            (admissions['admission_type'].str.contains('SURGICAL', case=False, na=False)) |
            (admissions['admission_location'].str.contains('SURGERY', case=False, na=False))
        )
    ]
    print(f"  Surgical sepsis: {len(surgical_sepsis):,}")

    # Add demographics
    print("\n4. Adding demographics...")
    cohort = surgical_sepsis.merge(patients, on='subject_id', how='left')

    # Calculate age
    cohort['admittime'] = pd.to_datetime(cohort['admittime'])
    cohort['age'] = cohort['admittime'].dt.year - cohort['anchor_year'] + cohort['anchor_age']
    cohort = cohort[cohort['age'] >= MIN_AGE]
    print(f"  Adults (>= {MIN_AGE}): {len(cohort):,}")

    # Survival variables
    cohort['dischtime'] = pd.to_datetime(cohort['dischtime'])
    cohort['los_days'] = (cohort['dischtime'] - cohort['admittime']).dt.total_seconds() / (24 * 3600)
    cohort['Time'] = cohort['los_days']
    cohort['Event'] = cohort['hospital_expire_flag']

    print(f"  Deaths: {cohort['Event'].sum():,} ({cohort['Event'].mean()*100:.1f}%)")

    # Select columns
    cohort_base = cohort[[
        'subject_id', 'hadm_id', 'age', 'gender', 
        'admittime', 'dischtime', 'Time', 'Event'
    ]].copy()

    cohort_base = cohort_base.rename(columns={'age': 'Age', 'gender': 'Sex'})

    # Save
    cohort_file = os.path.join(INTERMEDIATE_PATH, 'cohort_base.csv')
    cohort_base.to_csv(cohort_file, index=False)
    print(f"\nSaved: {cohort_file}")
    print(f"  Cohort: {len(cohort_base):,} patients")


def step2_extract_labs():
    """Extract laboratory values."""
    print("\n" + "="*70)
    print("STEP 2: EXTRACTING LABORATORY VALUES")
    print("="*70)

    # Load cohort
    cohort = pd.read_csv(os.path.join(INTERMEDIATE_PATH, 'cohort_base.csv'))
    hadm_ids = cohort['hadm_id'].values

    # Get all lab item IDs
    all_lab_ids = [item for items in LAB_ITEMS.values() for item in items]
    item_to_name = {}
    for name, ids in LAB_ITEMS.items():
        for item_id in ids:
            item_to_name[item_id] = name

    print("\n1. Extracting lab values (this may take 5-10 minutes)...")
    labs_list = []
    chunk_count = 0

    for chunk in pd.read_csv(
        f'{MIMIC_PATH}hosp/labevents.csv.gz',
        compression='gzip',
        chunksize=1000000,
        usecols=['hadm_id', 'itemid', 'valuenum']
    ):
        chunk_count += 1
        if chunk_count % 5 == 0:
            print(f"  Processing chunk {chunk_count}...", end='\r')
        
        chunk_filtered = chunk[
            (chunk['hadm_id'].isin(hadm_ids)) &
            (chunk['itemid'].isin(all_lab_ids)) &
            (chunk['valuenum'].notna())
        ]
        
        if len(chunk_filtered) > 0:
            labs_list.append(chunk_filtered)

    print()

    if labs_list:
        labs = pd.concat(labs_list, ignore_index=True)
        print(f"  Extracted {len(labs):,} lab measurements")
        
        # Pivot
        labs['lab_name'] = labs['itemid'].map(item_to_name)
        labs_first = labs.groupby(['hadm_id', 'lab_name'])['valuenum'].first().reset_index()
        labs_wide = labs_first.pivot(
            index='hadm_id',
            columns='lab_name',
            values='valuenum'
        ).reset_index()
        
        # Merge
        cohort = cohort.merge(labs_wide, on='hadm_id', how='left')
        
        # Rename
        cohort = cohort.rename(columns={
            'Lactate': 'Lac',
            'Sodium': 'Na',
            'Chloride': 'Cl',
            'Platelets': 'Plt'
        })
        
        # Coverage
        print("\n2. Lab coverage:")
        for lab in ['ALT', 'AST', 'Lac', 'Na', 'Cl', 'Plt']:
            if lab in cohort.columns:
                pct = cohort[lab].notna().sum() / len(cohort) * 100
                print(f"  {lab}: {cohort[lab].notna().sum():,} ({pct:.1f}%)")

    # Save
    labs_file = os.path.join(INTERMEDIATE_PATH, 'cohort_with_labs.csv')
    cohort.to_csv(labs_file, index=False)
    print(f"\nSaved: {labs_file}")


def step3_extract_vitals():
    """Extract vital signs."""
    print("\n" + "="*70)
    print("STEP 3: EXTRACTING VITAL SIGNS")
    print("="*70)

    # Load cohort
    cohort = pd.read_csv(os.path.join(INTERMEDIATE_PATH, 'cohort_with_labs.csv'))

    # Load ICU stays
    print("\n1. Loading ICU stays...")
    icustays = pd.read_csv(
        f'{MIMIC_PATH}icu/icustays.csv.gz',
        compression='gzip',
        usecols=['subject_id', 'hadm_id', 'stay_id']
    )

    cohort_icu = cohort.merge(icustays, on=['subject_id', 'hadm_id'], how='left')
    stay_ids = cohort_icu['stay_id'].dropna().unique()
    print(f"  ICU stays: {len(stay_ids):,}")

    if len(stay_ids) > 0:
        # Get vital item IDs
        all_vital_ids = [item for items in VITAL_ITEMS.values() for item in items]
        item_to_name = {}
        for name, ids in VITAL_ITEMS.items():
            for item_id in ids:
                item_to_name[item_id] = name
        
        print("\n2. Extracting vitals (this may take 10-15 minutes)...")
        vitals_list = []
        chunk_count = 0
        
        for chunk in pd.read_csv(
            f'{MIMIC_PATH}icu/chartevents.csv.gz',
            compression='gzip',
            chunksize=1000000,
            usecols=['stay_id', 'itemid', 'valuenum']
        ):
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"  Processing chunk {chunk_count}...", end='\r')
            
            chunk_filtered = chunk[
                (chunk['stay_id'].isin(stay_ids)) &
                (chunk['itemid'].isin(all_vital_ids)) &
                (chunk['valuenum'].notna())
            ]
            
            if len(chunk_filtered) > 0:
                vitals_list.append(chunk_filtered)
        
        print()
        
        if vitals_list:
            vitals = pd.concat(vitals_list, ignore_index=True)
            print(f"  Extracted {len(vitals):,} vital measurements")
            
            # Pivot
            vitals['vital_name'] = vitals['itemid'].map(item_to_name)
            vitals_mean = vitals.groupby(['stay_id', 'vital_name'])['valuenum'].mean().reset_index()
            vitals_wide = vitals_mean.pivot(
                index='stay_id',
                columns='vital_name',
                values='valuenum'
            ).reset_index()
            
            # Merge
            cohort_icu = cohort_icu.merge(vitals_wide, on='stay_id', how='left')
            vital_cols = [c for c in ['HR', 'RR'] if c in cohort_icu.columns]
            
            cohort = cohort.merge(
                cohort_icu[['hadm_id'] + vital_cols].drop_duplicates('hadm_id'),
                on='hadm_id',
                how='left'
            )
            
            # Coverage
            print("\n3. Vital coverage:")
            for vital in ['HR', 'RR']:
                if vital in cohort.columns:
                    pct = cohort[vital].notna().sum() / len(cohort) * 100
                    print(f"  {vital}: {cohort[vital].notna().sum():,} ({pct:.1f}%)")

    # Save
    vitals_file = os.path.join(INTERMEDIATE_PATH, 'cohort_with_vitals.csv')
    cohort.to_csv(vitals_file, index=False)
    print(f"\nSaved: {vitals_file}")


def step4_extract_gcs():
    """Extract GCS scores."""
    print("\n" + "="*70)
    print("STEP 4: EXTRACTING GCS SCORES")
    print("="*70)

    # Load cohort
    cohort = pd.read_csv(os.path.join(INTERMEDIATE_PATH, 'cohort_with_vitals.csv'))
    
    # Reload ICU stays needed for merging
    icustays = pd.read_csv(
        f'{MIMIC_PATH}icu/icustays.csv.gz',
        compression='gzip',
        usecols=['subject_id', 'hadm_id', 'stay_id']
    )

    # ICU stays
    cohort_icu = cohort.merge(icustays, on=['subject_id', 'hadm_id'], how='left')
    stay_ids = cohort_icu['stay_id'].dropna().unique()

    if len(stay_ids) > 0:
        print("\n1. Extracting GCS (this may take 10-15 minutes)...")
        gcs_list = []
        chunk_count = 0
        
        for chunk in pd.read_csv(
            f'{MIMIC_PATH}icu/chartevents.csv.gz',
            compression='gzip',
            chunksize=1000000,
            usecols=['stay_id', 'itemid', 'valuenum']
        ):
            chunk_count += 1
            if chunk_count % 10 == 0:
                print(f"  Processing chunk {chunk_count}...", end='\r')
            
            chunk_filtered = chunk[
                (chunk['stay_id'].isin(stay_ids)) &
                (chunk['itemid'].isin(GCS_ITEMS)) &
                (chunk['valuenum'].notna())
            ]
            
            if len(chunk_filtered) > 0:
                gcs_list.append(chunk_filtered)
        
        print()
        
        if gcs_list:
            gcs = pd.concat(gcs_list, ignore_index=True)
            print(f"  Extracted {len(gcs):,} GCS measurements")
            
            # Get total GCS
            gcs_total = gcs[gcs['itemid'] == 198].groupby('stay_id')['valuenum'].min()
            
            if len(gcs_total) == 0:
                gcs['component'] = gcs['itemid'].map({
                    220739: 'eye',
                    223901: 'motor',
                    223900: 'verbal'
                })
                gcs_comp = gcs[gcs['component'].notna()].pivot_table(
                    index='stay_id',
                    columns='component',
                    values='valuenum',
                    aggfunc='min'
                )
                if len(gcs_comp) > 0:
                    gcs_total = gcs_comp.sum(axis=1)
            
            if len(gcs_total) > 0:
                gcs_scores = gcs_total.reset_index().rename(columns={0: 'GCS'})
                cohort_icu = cohort_icu.merge(gcs_scores, on='stay_id', how='left')
                
                cohort = cohort.merge(
                    cohort_icu[['hadm_id', 'GCS']].drop_duplicates('hadm_id'),
                    on='hadm_id',
                    how='left'
                )
                
                pct = cohort['GCS'].notna().sum() / len(cohort) * 100
                print(f"  GCS: {cohort['GCS'].notna().sum():,} ({pct:.1f}%)")

    # Save
    gcs_file = os.path.join(INTERMEDIATE_PATH, 'cohort_with_gcs.csv')
    cohort.to_csv(gcs_file, index=False)
    print(f"\nSaved: {gcs_file}")


def step5_clean_and_finalize():
    """Clean and select final variables."""
    print("\n" + "="*70)
    print("STEP 5: CLEANING AND FINALIZING")
    print("="*70)

    # Load cohort
    cohort = pd.read_csv(os.path.join(INTERMEDIATE_PATH, 'cohort_with_gcs.csv'))

    print(f"\n1. Starting with: {len(cohort):,} patients")

    # Select analysis columns
    analysis_cols = [
        'subject_id', 'hadm_id', 'Age', 'Sex',
        'ALT', 'AST', 'Lac', 'Na', 'Cl', 'Plt',
        'HR', 'RR', 'GCS',
        'Time', 'Event'
    ]

    available_cols = [col for col in analysis_cols if col in cohort.columns]
    cohort_clean = cohort[available_cols].copy()

    print(f"\n2. Selected {len(available_cols)} analysis variables")

    # Convert Sex to numeric
    cohort_clean['Sex'] = cohort_clean['Sex'].map({'M': 1, 'F': 0})

    # Remove invalid times (negative or zero survival times)
    print("\n3. Removing invalid survival times...")
    before = len(cohort_clean)
    cohort_clean = cohort_clean[cohort_clean['Time'] > 0]
    removed = before - len(cohort_clean)
    if removed > 0:
        print(f"  Removed {removed} patients with invalid survival times")

    print(f"\n4. Final cohort: {len(cohort_clean):,} patients")
    print(f"   Events (deaths): {cohort_clean['Event'].sum():,} ({cohort_clean['Event'].mean()*100:.1f}%)")
    print(f"   Censored: {(cohort_clean['Event']==0).sum():,} ({(cohort_clean['Event']==0).mean()*100:.1f}%)")

    # Save full dataset
    full_file = os.path.join(FINAL_PATH, 'mimic_sepsis_cohort_full.csv')
    cohort_clean.to_csv(full_file, index=False)
    print(f"\nSaved complete dataset: {full_file}")

    print("\n" + "="*70)
    print("DATA EXTRACTION COMPLETED!")
    print("="*70)


if __name__ == "__main__":
    if check_files():
        step1_extract_base_cohort()
        step2_extract_labs()
        step3_extract_vitals()
        step4_extract_gcs()
        step5_clean_and_finalize()
    else:
        print("\nERROR: Missing required MIMIC-IV files. Please check the MIMIC_PATH.")
