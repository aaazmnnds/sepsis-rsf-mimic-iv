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
    filename <- paste0("imputed_mice", i, "_", output_prefix, ".csv")
    write.csv(imputed_data, filename, row.names = FALSE)
    message(paste("Saved:", filename))
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

# Get list of synthetic datasets (mcar, mar, mnar)
files <- list.files(pattern = "synthetic_.*\\.csv")
files <- files[!grepl("complete", files)]

if (file.exists("mimic_sepsis_cohort_full.csv")) {
  files <- c(files, "mimic_sepsis_cohort_full.csv")
}

if (length(files) == 0) {
  warning("No synthetic_*.csv files found. Please run data_simulation.R first.")
}

for (file in files) {
  # Extract mechanism name
  mechanism <- gsub("synthetic_|\\.csv", "", file)
  message(paste("Processing mechanism:", mechanism))

  # Read data
  data <- read.csv(file)

  # RENAME COLUMNS: Time -> Survival_Time, Event -> Status
  if ("Time" %in% names(data)) names(data)[names(data) == "Time"] <- "Survival_Time"
  if ("Event" %in% names(data)) names(data)[names(data) == "Event"] <- "Status"

  # 1. Run MICE
  tryCatch(
    {
      run_mice(data, output_prefix = mechanism, m = 5)
    },
    error = function(e) {
      message(paste("Error in MICE for", mechanism, ":", e$message))
    }
  )

  # 2. Run missForest
  tryCatch(
    {
      missforest_imputed <- run_missforest(data)
      missforest_filename <- paste0("imputed_missForest_", mechanism, ".csv")
      write.csv(missforest_imputed, missforest_filename, row.names = FALSE)
      message(paste("Saved:", missforest_filename))
    },
    error = function(e) {
      message(paste("Error in missForest for", mechanism, ":", e$message))
    }
  )
}

# ============================================================================
# Process Real MIMIC Data
# ============================================================================

mimic_file <- "mimic_sepsis_cohort_full.csv"

if (file.exists(mimic_file)) {
  message(paste("Processing real MIMIC data:", mimic_file))

  # Read real MIMIC data
  data_full <- read.csv(mimic_file)

  # Rename columns if needed for consistency
  if ("Time" %in% names(data_full)) names(data_full)[names(data_full) == "Time"] <- "Survival_Time"
  if ("Event" %in% names(data_full)) names(data_full)[names(data_full) == "Event"] <- "Status"

  # 1. Run MICE FULL
  tryCatch(
    {
      run_mice(data_full, output_prefix = "full", m = 5)
    },
    error = function(e) {
      message(paste("Error in MICE for real MIMIC data:", e$message))
    }
  )

  # 2. Run missForest
  tryCatch(
    {
      missforest_imputed_full <- run_missforest(data_full)
      missforest_filename_full <- "imputed_missForest_full.csv"
      write.csv(missforest_imputed_full, missforest_filename_full, row.names = FALSE)
      message(paste("Saved:", missforest_filename_full))
    },
    error = function(e) {
      message(paste("Error in missForest for real MIMIC data:", e$message))
    }
  )
} else {
  warning(paste("Real MIMIC data file not found:", mimic_file))
}

message("R imputation script completed.")
