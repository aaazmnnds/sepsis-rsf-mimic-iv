# Load necessary libraries
library(tidyverse)
library(mice)

# Set seed for reproducibility
set.seed(42)

# Output Configuration
ROOT_DIR <- "/Users/nazu.ds/Documents/Research Collections/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
output_dir <- file.path(ROOT_DIR, "Results sensitivity")
dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)

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
# Time-to-event (Survival_Time): Exponential
data1$Survival_Time <- rexp(n, rate = 0.02)

# Event indicator (Status): Binary
data1$Status <- rbinom(n, 1, 0.069)

# Ensure logical bounds (e.g., GCS between 3 and 15, Age > 0)
data1$GCS <- pmin(pmax(round(data1$GCS), 3), 15)
data1$Age <- pmax(data1$Age, 18) # Assume adult cohort
data1$RR <- pmax(data1$RR, 0)
data1$HR <- pmax(data1$HR, 0)

# Save Complete Data
write.csv(data1, file.path(output_dir, "synthetic_complete.csv"), row.names = FALSE)
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

# Define target missingness rates for sensitivity analysis (Response to Reviewer 2.10)
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 0) {
  # Convert e.g., "10" "40" to 0.10, 0.40
  # Note: Use 26.8 for the baseline rate
  target_rates <- as.numeric(args) / 100
  cat(sprintf("Running simulation for specified rates: %s%%\n", paste(args, collapse=", ")))
} else {
  target_rates <- c(0.1000, 0.268, 0.4001, 0.5498)
  cat("No rates specified. Running full suite: 10.00%, 26.8%, 40.01%, 54.98%\n")
}

# Proportional Scaling Formula:
# ScaleFactor = TargetRate / 0.268
# This maintains the clinical hierarchy (e.g., ALT always higher missingness than Sodium)

# Function to find the optimal scaling factor to hit an OVERALL target rate
# across 13 variables, even when some are capped at 95%
get_scaled_rates <- function(baseline_rates, target_total_rate, n_total_vars) {
  target_sum <- target_total_rate * n_total_vars
  
  # Optimization function: Difference between achieved sum and target sum
  f <- function(k) {
    sum(pmin(unlist(baseline_rates) * k, 0.95)) - target_sum
  }
  
  # Find optimal k using uniroot (search between 0.1 and 20x scaling)
  # If target is impossible (e.g. > 65%), it will catch at the upper bound
  k_opt <- tryCatch({
    uniroot(f, lower=0.1, upper=50)$root
  }, error = function(e) 50)
  
  return(lapply(baseline_rates, function(r) min(r * k_opt, 0.95)))
}

for (target_rate in target_rates) {
  cat(sprintf("\n\n>>> GENERATING DATASETS FOR TARGET RATE: %.1f%% <<<\n", target_rate * 100))
  
  # Use target-seeking scaling instead of simple multiplication
  current_miss_rates <- get_scaled_rates(miss_rates, target_rate, 13)
  
  # Log the new "effective" scaling for transparency
  actual_sum <- sum(unlist(current_miss_rates))
  cat(sprintf("Targeting total missingness sum: %.2f (Avg: %.2f%% across 13 variables)\n", 
              actual_sum, (actual_sum/13)*100))
  
  mechanisms <- c("MCAR", "MAR", "MNAR")
  
  for (mech in mechanisms) {
    # 1. Apply missingness
    data_miss <- apply_variable_specific_missingness(data1, current_miss_rates, mechanism = mech)
    
    # 2. Verify achieved rate
    # Total cells = N * 13 (Age, Sex, ALT, AST, Lac, Na, Cl, Plt, HR, RR, GCS, Time, Event)
    actual_rate <- mean(is.na(data_miss[, c("Age", "Sex", "ALT", "AST", "Lac", "Na", "Cl", "Plt", "HR", "RR", "GCS", "Time", "Event")]))
    
    # 3. Save file with rate-specific naming
    # Use '26.8' for baseline, others as integers for cleaner naming
    rate_label <- if(target_rate == 0.268) "26.8" else as.character(target_rate * 100)
    filename <- sprintf("synthetic_%s_%s.csv", tolower(mech), rate_label)
    full_path <- file.path(output_dir, filename)
    
    write.csv(data_miss, full_path, row.names = FALSE)
    
    # 4. Report status
    status <- if(abs(actual_rate - target_rate) < 0.005) "PASSED" else "WARNING: OFF-TARGET"
    cat(sprintf("  [%s] Saved %-25s | Actual Rate: %5.2f%% | Target: %5.1f%% | %s\n", 
                mech, filename, actual_rate * 100, target_rate * 100, status))
  }
}

cat("\n\n======================================================================\n")
cat("SENSITIVITY ANALYSIS DATA GENERATION COMPLETED\n")
cat("Formula used: r_scaled = min(r_baseline * (target / 0.268), 0.95)\n")
cat("Reference: Response to Reviewer 2.10\n")
cat("======================================================================\n")