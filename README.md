# Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests

[![DOI](https://img.shields.io/badge/DOI-10.XXXX%2FXXXXXX-blue)](https://doi.org/10.XXXX/XXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This repository contains the analysis code for the manuscript:

**"Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests: A MIMIC-IV Database Study with Methodological Validation"**

### Methodology Summary
This study compares random survival forests (RSF) with XGBoost, DeepSurv, component-wise gradient boosting, and elastic-net and ridge Cox models under four imputation methods (MICE, missForest, GAIN, MIDA), in MIMIC-IV and in simulated data with MCAR, MAR, and MNAR missingness.

### Key Features
- Comparison of 6 survival models: RSF, XGBoost, DeepSurv, component-wise gradient boosting, elastic-net Cox, ridge Cox
- Comparison of 4 imputation methods: MICE, missForest, GAIN, MIDA
- Repeated 5x10-fold cross-validation, bootstrap confidence intervals, calibration, and a simulation study (MCAR, MAR, MNAR)

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

### Data Availability

The primary dataset (`mimic_sepsis_cohort_full.csv`) is derived from **MIMIC-IV v2.2**. 
- MIMIC-IV data available at **PhysioNet**: [https://physionet.org/content/mimiciv/2.2/](https://physionet.org/content/mimiciv/2.2/)
- Users must complete CITI training and request access via PhysioNet.
- Follow the extraction guide in `docs/MIMIC_IV_data_extraction.md` for local setup.

---

## Reproduction Workflow

Data: MIMIC-IV requires PhysioNet credentialed access; data files are not in the repository. Extraction: src/data_loading/extract_mimic_data.py.

Run order: (1) src/missingness/data_simulation.R; (2) src/missingness/imputation_r.R (MICE, missForest); (3) src/missingness/imputation_python.py (GAIN, MIDA); (4) OMP_NUM_THREADS=1 python src/models/survival_models.py; (5) src/evaluation/statistical_tests.py (run from the Results sensitivity folder); (6) src/evaluation/extract_lactate_medians.py; (7) src/visualization scripts.

Note: set OMP_NUM_THREADS=1 to avoid a native threading crash on macOS; random seed 42 is set in each script.

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
