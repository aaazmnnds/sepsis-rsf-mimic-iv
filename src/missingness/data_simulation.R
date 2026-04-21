# Load necessary libraries
library(tidyverse)
library(mice)

# Set seed for reproducibility
set.seed(42)

# Set sample size (matching MIMIC-IV cohort)
n <- 852

# ---------------------------------------------------------
# 1. Generate Synthetic Data (Complete)
# ---------------------------------------------------------
data1 <- data.frame(
  # Age: Mean = 65, sd = 15
  Age = rnorm(n, mean = 65, sd = 15),

  # ALT (Alanine Aminotransferase): Log-normal
  ALT = rlnorm(n, meanlog = log(35), sdlog = log(1.6)),

  # Sex: Binary categorical (M/F)
  Sex = sample(c("M", "F"), n, replace = TRUE, prob = c(0.5, 0.5)),

  # Heart Rate (HR): Normal, mean 75, sd 10
  HR = rnorm(n, mean = 75, sd = 10),

  # Respiratory Rate (RR): Normal, mean 18, sd 4
  RR = rnorm(n, mean = 18, sd = 4),

  # Glasgow Coma Scale (GCS): Normal, mean 13, sd 3
  GCS = rnorm(n, mean = 13, sd = 3),

  # Chloride (Cl): Normal, mean 104, sd 5
  Cl = rnorm(n, mean = 104, sd = 5),

  # Lactate (Lac): Log-normal
  Lac = rlnorm(n, meanlog = log(1.5), sdlog = log(1.4)),

  # Platelet count (Plt): Log-normal
  Plt = rlnorm(n, meanlog = log(220), sdlog = log(1.3))
)

# Derived variables with noise
# Sodium (Na): Related to Cl
data1$Na <- 1.2 * data1$Cl + rnorm(n, mean = 0, sd = 1.5)

# AST: Related to ALT
data1$AST <- data1$ALT + 0.5 * rnorm(n, mean = 0, sd = 1)

# Survival outcomes
# Time-to-event (Time): Exponential
data1$Time <- rexp(n, rate = 0.02)

# Event indicator (Event): Binary
data1$Event <- rbinom(n, 1, 0.069)

# Ensure logical bounds (e.g., GCS between 3 and 15, Age > 0)
data1$GCS <- pmin(pmax(round(data1$GCS), 3), 15)
data1$Age <- pmax(data1$Age, 18) # Assume adult cohort
data1$RR <- pmax(data1$RR, 0)
data1$HR <- pmax(data1$HR, 0)

# Save Complete Data
write.csv(data1, "synthetic_complete.csv", row.names = FALSE)
cat("Created 'synthetic_complete.csv' (n =", n, ")\n")

# ---------------------------------------------------------
# 2. Amputation (Simulate Variable-Specific Missingness)
# ---------------------------------------------------------
# Variable-specific missingness rates matching MIMIC-IV dataset:
# ALT: 57.04%, AST: 56.22%, GCS: 55.99%, HR: 55.63%, RR: 55.63%
# Lac: 46.83%, Na: 7.28%, Cl: 7.28%, Plt: 6.57%
# Overall: 23.23%

# Define missingness rates for each variable
miss_rates <- list(
  ALT = 0.5704,
  AST = 0.5622,
  GCS = 0.5599,
  HR = 0.5563,
  RR = 0.5563,
  Lac = 0.4683,
  Na = 0.0728,
  Cl = 0.0728,
  Plt = 0.0657
)

# Helper function to apply variable-specific missingness
apply_variable_specific_missingness <- function(data, miss_rates, mechanism = "MCAR") {
  data_miss <- data

  for (var in names(miss_rates)) {
    n_miss <- round(nrow(data) * miss_rates[[var]])

    if (mechanism == "MCAR") {
      # Completely random
      miss_idx <- sample(seq_len(nrow(data)), n_miss)

    } else if (mechanism == "MAR") {
      # Depends on OTHER observed variables
      # Older patients and those with abnormal vitals more likely to have missing labs
      # Use directional relationships (not absolute values)

      # Standardize Age (higher age = higher probability)
      age_scaled <- scale(data$Age)[,1]

      # Abnormal HR (far from mean of 75)
      hr_abnormal <- abs(data$HR - 75) / sd(data$HR)

      # Create probability: higher for older patients and abnormal vitals
      prob_miss <- plogis(age_scaled + 0.5 * hr_abnormal)  # Use logistic to keep in [0,1]
      prob_miss <- prob_miss / sum(prob_miss)

      miss_idx <- sample(seq_len(nrow(data)), n_miss, prob = prob_miss)

    } else if (mechanism == "MNAR") {
      # Depends on the variable itself
      # Higher values more likely to be missing (sicker patients)

      if (is.numeric(data[[var]])) {
        # For clinical labs: higher values (worse outcomes) more likely missing
        # For GCS: LOWER values (worse) more likely missing

        if (var == "GCS") {
          # Lower GCS (worse neurological status) more likely to be missing
          var_scaled <- -scale(data[[var]])[,1]  # Negative so lower = higher probability
        } else {
          # Higher lab values (abnormal) more likely to be missing
          var_scaled <- scale(data[[var]])[,1]
        }

        # Convert to probabilities using logistic function
        prob_miss <- plogis(var_scaled)
        prob_miss <- prob_miss / sum(prob_miss)

        miss_idx <- sample(seq_len(nrow(data)), n_miss, prob = prob_miss)
      } else {
        # For non-numeric, use random
        miss_idx <- sample(seq_len(nrow(data)), n_miss)
      }
    }

    data_miss[miss_idx, var] <- NA
  }

  return(data_miss)
}

# --- MCAR (Missing Completely at Random) ---
cat("\nGenerating MCAR dataset with variable-specific missingness...\n")
data_mcar <- apply_variable_specific_missingness(data1, miss_rates, mechanism = "MCAR")
write.csv(data_mcar, "synthetic_mcar.csv", row.names = FALSE)
cat("Created 'synthetic_mcar.csv'\n")

# --- MAR (Missing at Random) ---
cat("\nGenerating MAR dataset with variable-specific missingness...\n")
data_mar <- apply_variable_specific_missingness(data1, miss_rates, mechanism = "MAR")
write.csv(data_mar, "synthetic_mar.csv", row.names = FALSE)
cat("Created 'synthetic_mar.csv'\n")

# --- MNAR (Missing Not at Random) ---
cat("\nGenerating MNAR dataset with variable-specific missingness...\n")
data_mnar <- apply_variable_specific_missingness(data1, miss_rates, mechanism = "MNAR")
write.csv(data_mnar, "synthetic_mnar.csv", row.names = FALSE)
cat("Created 'synthetic_mnar.csv'\n")

# ---------------------------------------------------------
# 3. Validation Summary
# ---------------------------------------------------------
cat("\n======================================================================\n")
cat("                    MISSINGNESS VALIDATION SUMMARY                    \n")
cat("======================================================================\n\n")

check_miss_detailed <- function(df, name) {
  cat("--- ", name, " Dataset ---\n", sep = "")
  # Overall missingness
  overall_miss <- mean(is.na(df))
  cat("Overall Missingness: ", round(overall_miss * 100, 2), "%\n\n", sep = "")

  # Variable-specific missingness
  cat("Variable-Specific Missingness:\n")
  for (var in names(miss_rates)) {
    var_miss <- sum(is.na(df[[var]])) / nrow(df) * 100
    expected <- miss_rates[[var]] * 100
    cat(sprintf("  %-6s: %5.2f%% (Expected: %5.2f%%)\n", var, var_miss, expected))
  }
  cat("\n")
}

check_miss_detailed(data_mcar, "MCAR")
check_miss_detailed(data_mar, "MAR")
check_miss_detailed(data_mnar, "MNAR")

cat("======================================================================\n")