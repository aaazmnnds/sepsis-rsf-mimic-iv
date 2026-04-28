# Load necessary libraries
if (!require(mice)) install.packages("mice")
if (!require(missForest)) install.packages("missForest")
if (!require(tidyverse)) install.packages("tidyverse")
library(mice)
library(missForest)
library(tidyverse)

# Define function for MICE imputation - SAVE 5 SEPARATE DATASETS (NO POOLING)
# Define function for MICE imputation - SAVE 5 SEPARATE DATASETS (NO POOLING)
run_mice <- function(data, output_prefix, m = 5, maxit = 20, seed = 123) {
  message("Running MICE imputation...")

  # Run MICE with Random Forest method
  # Note: remove.collinear=FALSE is crucial here because some variables (e.g., AST/ALT) are highly correlated
  imp <- mice(data, m = m, maxit = maxit, method = "rf", seed = seed, print = FALSE, remove.collinear = FALSE)

  # Save each of the m=5 imputed datasets separately
  for (i in 1:m) {
    imputed_data <- complete(imp, i)
    filename <- paste0("mice", i, "_", output_prefix, ".csv")
    full_path <- file.path(output_dir, filename)
    write.csv(imputed_data, full_path, row.names = FALSE)
    message(paste("Saved:", full_path))
  }
}

# Define function for missForest imputation
run_missforest <- function(data, seed = 123) {
  message("Running missForest imputation...")
  set.seed(seed)

  # Convert character columns to factors (missForest requirement)
  data_converted <- data
  char_cols <- sapply(data_converted, is.character)
  data_converted[char_cols] <- lapply(data_converted[char_cols], as.factor)

  imp <- missForest(data_converted)
  return(imp$ximp)
}

# Output Configuration
ROOT_DIR <- "/Users/nazu.ds/Documents/Research Collections/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
data_dir <- file.path(ROOT_DIR, "Results sensitivity")
output_dir <- file.path(ROOT_DIR, "Results sensitivity")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

# Parse command line arguments for specific rates
args <- commandArgs(trailingOnly = TRUE)
target_rates <- if (length(args) > 0) args else NULL

# Get list of synthetic datasets (mcar, mar, mnar)
files <- list.files(path = data_dir, pattern = "synthetic_.*\\.csv", full.names = TRUE)
files <- files[!grepl("complete", files)]

# Filter by rates if specified
if (!is.null(target_rates)) {
  cat(sprintf("Filtering for specific rates: %s\n", paste(target_rates, collapse=", ")))
  # Match _rate.csv (e.g., _10.csv)
  pattern <- paste0("_", target_rates, ".csv", collapse="|")
  files <- files[grepl(pattern, files)]
  cat(sprintf("Files remaining after filtering: %d\n", length(files)))
}

if (length(files) == 0) {
  warning("No matching synthetic_*.csv files found.")
}

for (file in files) {
  # Extract mechanism name (e.g., mcar_10)
  mechanism <- gsub("synthetic_|\\.csv", "", basename(file))
  message(paste("\nProcessing mechanism:", mechanism))

  # Read data
  data <- read.csv(file)

  # RENAME COLUMNS: Time -> Survival_Time, Event -> Status
  if ("Time" %in% names(data)) names(data)[names(data) == "Time"] <- "Survival_Time"
  if ("Event" %in% names(data)) names(data)[names(data) == "Event"] <- "Status"

  # 1. Run MICE
  mice_check <- file.path(output_dir, paste0("mice1_", mechanism, ".csv"))
  if (file.exists(mice_check)) {
    message(paste("Skipping MICE for", mechanism, "- already exists"))
  } else {
    tryCatch(
      {
        run_mice(data, output_prefix = mechanism, m = 5)
      },
      error = function(e) {
        message(paste("Error in MICE for", mechanism, ":", e$message))
      }
    )
  }

  # 2. Run missForest
  missforest_filename <- paste0("missForest_", mechanism, ".csv")
  full_path_mf <- file.path(output_dir, missforest_filename)
  
  if (file.exists(full_path_mf)) {
    message(paste("Skipping missForest for", mechanism, "- already exists"))
  } else {
    tryCatch(
      {
        missforest_imputed <- run_missforest(data)
        write.csv(missforest_imputed, full_path_mf, row.names = FALSE)
        message(paste("Saved:", full_path_mf))
      },
      error = function(e) {
        message(paste("Error in missForest for", mechanism, ":", e$message))
      }
    )
  }
}

# ============================================================================
# Process Real MIMIC Data
# ============================================================================

mimic_file <- file.path(ROOT_DIR, "mimic_sepsis_cohort_full.csv")

if (file.exists(mimic_file)) {
  message(paste("\nProcessing real MIMIC data:", mimic_file))

  # Read real MIMIC data
  data_full <- read.csv(mimic_file)

  # Rename columns if needed for consistency
  if ("Time" %in% names(data_full)) names(data_full)[names(data_full) == "Time"] <- "Survival_Time"
  if ("Event" %in% names(data_full)) names(data_full)[names(data_full) == "Event"] <- "Status"

  # 1. Run MICE FULL
  mice_full_check <- file.path(output_dir, "mice1_full.csv")
  if (file.exists(mice_full_check)) {
    message("Skipping MICE for real MIMIC data - already exists")
  } else {
    tryCatch(
      {
        run_mice(data_full, output_prefix = "full", m = 5)
      },
      error = function(e) {
        message(paste("Error in MICE for real MIMIC data:", e$message))
      }
    )
  }

  # 2. Run missForest
  mf_full_filename <- "missForest_full.csv"
  mf_full_path <- file.path(output_dir, mf_full_filename)
  if (file.exists(mf_full_path)) {
    message("Skipping missForest for real MIMIC data - already exists")
  } else {
    tryCatch(
      {
        missforest_imputed_full <- run_missforest(data_full)
        write.csv(missforest_imputed_full, mf_full_path, row.names = FALSE)
        message(paste("Saved:", mf_full_path))
      },
      error = function(e) {
        message(paste("Error in missForest for real MIMIC data:", e$message))
      }
    )
  }
} else {
  warning(paste("Real MIMIC data file not found:", mimic_file))
}

message("R imputation script completed.")