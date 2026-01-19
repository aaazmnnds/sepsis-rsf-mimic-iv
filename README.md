# Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests

[![DOI](https://img.shields.io/badge/DOI-10.XXXX%2FXXXXXX-blue)](https://doi.org/10.XXXX/XXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This repository contains the complete code and data for the manuscript:

**"Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests: A MIMIC-IV Database Study with Methodological Validation"**

### Key Features
- **Random Survival Forest (RSF)** implementation for postoperative sepsis prediction
- Comprehensive comparison of **4 imputation methods**: MICE, missForest, GAIN, MIDA
- Benchmark against **3 ML models**: XGBoost, DeepSurv, Component-wise Gradient Boosting
- **Full cohort analysis** (n=852) with perfect risk stratification (log-rank p < 0.001)
- **Simulation study** validating robustness across MCAR, MAR, and MNAR mechanisms

---

## Repository Structure

```
.
├── data/
│   ├── raw/                   # mimic_sepsis_cohort_full.csv (n=852)
│   ├── imputed/               # Imputed datasets (GAIN, MIDA, MICE, missForest)
│   └── synthetic/             # Synthetic datasets for sensitivity analysis
├── src/
│   ├── data_loading/          # Scripts to load and preprocess MIMIC-IV data
│   ├── missingness/           # Imputation algorithms (R and Python)
│   ├── models/                # Random Survival Forest & Baseline models
│   ├── evaluation/            # Performance metrics, log-rank tests, tables
│   └── visualization/         # Flowcharts, KM curves, plots
├── results/
│   ├── figures/               # Generated plots and figures
│   ├── tables/                # CSV tables for manuscript
│   └── predictions/           # Model survival probabilities
├── manuscript/                # LaTeX source files and bibliography
├── notebook/                  # Jupyter notebooks for exploratory analysis
├── scripts/                   # Helper shell scripts
├── docs/                      # Documentation and guides
├── requirements.txt           # Python dependencies
└── README.md                  # This file
````

---

## Quick Start

### Prerequisites

**R (≥ 4.0.0)**
```r
install.packages(c("survival", "randomForestSRC", "mice", "missForest", "dplyr", "ggplot2"))
```

**Python (≥ 3.8)**
```bash
pip install -r requirements.txt
```

Or use conda:
```bash
conda env create -f environment.yml
conda activate sepsis-rsf
```

### Data Access

The primary dataset (`mimic_sepsis_cohort_full.csv`) is derived from **MIMIC-IV v2.2**. To access:

1. Complete CITI training: https://physionet.org/about/citi-course/
2. Request access: https://physionet.org/content/mimiciv/2.2/
3. Follow extraction guide in `docs/MIMIC_IV_data_extraction.md`

---

## Reproduction Workflow

### Step 1: Data Simulation (Optional - for sensitivity analysis)
```bash
Rscript scripts/01_data_simulation.R
```
**Output:** `simulated_cohort_full.csv`, `simulated_cohort_mcar.csv`, etc.

### Step 2: Missing Data Imputation
```bash
# R-based methods (MICE, missForest)
Rscript scripts/02_imputation_r.R

# Python-based methods (GAIN, MIDA)
python scripts/03_imputation_python.py
```
**Output:** 32 imputed datasets in `data/imputed/`

### Step 3: Standardize Data Columns
**Critical:** Run this before survival analysis to fix column names (Time -> Survival_Time, Event -> Status).
```bash
python fix_dataset_columns.py
```

### Step 4: Train Survival Models
```bash
python scripts/04_survival_models.py
```
**Output:** Model predictions, C-index, IBS, time-dependent AUC

### Step 5: Full Cohort Analysis (Primary Result)
```bash
# Generate RSF predictions on full cohort
python scripts/07_generate_python_predictions.py

# Perform log-rank test and calculate survival probabilities
Rscript scripts/08_FINAL_publication_analysis.R
```
**Output:** 
- `FINAL_logrank_test.csv` (p < 0.001)
- `FINAL_survival_probabilities.csv` (30-day, 60-day survival)
- Kaplan-Meier curves

### Step 6: Generate Figures & Tables
```bash
# Data visualizations
Rscript scripts/05_visualize_data.R
python scripts/06_visualize_model_performance.py

# Manuscript tables
python scripts/utils/generate_table1.py
python scripts/utils/generate_flowchart.py
python scripts/utils/regenerate_figure_b1.py
```

---

## Key Results

### Primary Analysis (MIMIC-IV, n=852)

| Model | Imputation | CV C-index (95% CI) | Test C-index | IBS |
|-------|-----------|---------------------|--------------|-----|
| **RSF** | **GAIN** | **0.819 (0.755-0.882)** | **0.754** | **0.104** |
| RSF | missForest | 0.810 (0.745-0.875) | 0.710 | 0.105 |
| Gradient Boosting | missForest | 0.790 (0.725-0.854) | 0.795 | 0.105 |
| XGBoost | MICE | 0.745 (0.533-0.957) | 0.562 | — |

### Risk Stratification (Full Cohort)

- **Perfect separation:** All 59 mortality events in high-risk group (n=426)
- **Log-rank test:** p < 0.001
- **30-day survival:** 79.4% (high-risk) vs 100% (low-risk)
- **60-day survival:** 66.7% (high-risk) vs 100% (low-risk)

### Top Predictors (Variable Importance)

1. **Platelet Count** (0.1383 ± 0.0463)
2. **Glasgow Coma Scale** (0.0552 ± 0.0142)
3. **Lactate** (0.0281 ± 0.0173)

---

## Citation

If you use the data extraction code or analysis pipeline from this repository, please cite our paper:

> Nads A, et al. "Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests: A MIMIC-IV Database Study with Methodological Validation." (2026).

```bibtex
@article{nads2026sepsis,
  title={Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests: A MIMIC-IV Database Study with Methodological Validation},
  author={Nads, Azman and others},
  journal={BMC Medical Research Methodology (Submitted)},
  year={2026},
  note={Under Review}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note:** The MIMIC-IV dataset is subject to PhysioNet Credentialed Health Data License. Users must independently obtain access.

---

## Contact

For questions or issues, please open a GitHub issue or contact:
- **Azman Nads:** azmannads@msutawi-tawi.edu.ph

---

## Acknowledgments

- MIMIC-IV database provided by MIT Laboratory for Computational Physiology
- Funding: Department of Science and Technology--Science Education Institute (DOST-SEI), Philippines
