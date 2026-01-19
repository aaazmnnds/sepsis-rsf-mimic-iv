#!/usr/bin/env Rscript
# Generate Full Cohort RSF Predictions for MIMIC-IV Data
# =======================================================
# Trains RSF on full n=852 cohort and generates predictions for all patients

library(survival)
library(randomForestSRC)
library(dplyr)

cat("================================================================================\n")
cat("GENERATING FULL COHORT RSF PREDICTIONS (n=852)\n")
cat("================================================================================\n\n")

# ============================================================================
# 1. LOAD FULL MIMIC-IV COHORT
# ============================================================================
cat("1. Loading full MIMIC-IV cohort...\n")

data <- read.csv("mimic_sepsis_cohort_full.csv")
cat(sprintf("   Loaded: mimic_sepsis_cohort_full.csv\n"))
cat(sprintf("   Total patients: n=%d\n", nrow(data)))
cat(sprintf("   Total events: %d (%.1f%%)\n", sum(data$Event), 100 * mean(data$Event)))

# ============================================================================
# 2. PREPARE DATA FOR RSF
# ============================================================================
cat("\n2. Preparing data for RSF...\n")

# Remove ID columns
feature_cols <- setdiff(names(data), c("subject_id", "hadm_id", "Time", "Event"))
cat(sprintf("   Features: %d variables\n", length(feature_cols)))
cat(sprintf("   Feature names: %s...\n", paste(feature_cols[1:min(5, length(feature_cols))], collapse = ", ")))

# Handle missing values (impute with median for numeric, mode for categorical)
for (col in feature_cols) {
    if (is.numeric(data[[col]])) {
        data[[col]][is.na(data[[col]])] <- median(data[[col]], na.rm = TRUE)
    } else {
        mode_val <- names(sort(table(data[[col]]), decreasing = TRUE))[1]
        data[[col]][is.na(data[[col]])] <- mode_val
    }
}

# Create formula for RSF
formula_str <- paste("Surv(Time, Event) ~", paste(feature_cols, collapse = " + "))
cat(sprintf("   Formula: %s\n", substr(formula_str, 1, 60)))

# ============================================================================
# 3. TRAIN RSF ON FULL COHORT
# ============================================================================
cat("\n3. Training RSF on full cohort...\n")
cat("   (This may take a few minutes...)\n")

rsf_model <- rfsrc(
    as.formula(formula_str),
    data = data,
    ntree = 1000,
    nodesize = 15,
    splitrule = "logrank",
    importance = TRUE,
    seed = 42
)

cat("   RSF training complete!\n")
cat(sprintf("   OOB C-index: %.3f\n", rsf_model$err.rate[length(rsf_model$err.rate)]))

# ============================================================================
# 4. GENERATE PREDICTIONS FOR ALL PATIENTS
# ============================================================================
cat("\n4. Generating predictions for all patients...\n")

# Get predicted mortality (higher = higher risk)
risk_scores <- rsf_model$predicted.oob

# Create risk groups (median split)
median_risk <- median(risk_scores)
risk_groups <- ifelse(risk_scores >= median_risk, "High", "Low")

# Prepare output dataframe
predictions <- data.frame(
    Patient_ID = 1:nrow(data),
    Observed_Time = data$Time,
    Observed_Status = data$Event,
    Predicted_Risk = risk_scores,
    Risk_Group = risk_groups
)

# Save predictions
write.csv(predictions, "full_cohort_rsf_predictions.csv", row.names = FALSE)
cat(sprintf("   Saved: full_cohort_rsf_predictions.csv (n=%d)\n", nrow(predictions)))

# ============================================================================
# 5. SUMMARY STATISTICS
# ============================================================================
cat("\n5. Summary statistics:\n")

for (group in c("High", "Low")) {
    subset <- predictions[predictions$Risk_Group == group, ]
    cat(sprintf("\n   %s Risk Group:\n", group))
    cat(sprintf("     N = %d\n", nrow(subset)))
    cat(sprintf("     Events = %d\n", sum(subset$Observed_Status)))
    cat(sprintf("     Event Rate = %.1f%%\n", 100 * mean(subset$Observed_Status)))
    cat(sprintf("     Mean Risk Score = %.2f\n", mean(subset$Predicted_Risk)))
}

cat("\n" + "=" * 80)
cat("PREDICTION GENERATION COMPLETE\n")
cat("================================================================================\n")
cat("\nNext step:\n")
cat("  The predictions are ready in: full_cohort_rsf_predictions.csv\n")
cat("  Now calculating survival statistics...\n")
cat("================================================================================\n\n")

# ============================================================================
# 6. CALCULATE SURVIVAL STATISTICS IMMEDIATELY
# ============================================================================
cat("6. Calculating survival statistics on full cohort...\n\n")

# Calibration
predictions$risk_decile <- cut(
    predictions$Predicted_Risk,
    breaks = quantile(predictions$Predicted_Risk, probs = seq(0, 1, 0.1)),
    labels = FALSE,
    include.lowest = TRUE
)

calib <- predictions %>%
    group_by(risk_decile) %>%
    summarise(
        Mean_Predicted_Risk = mean(Predicted_Risk),
        Observed_Event_Rate = mean(Observed_Status)
    )

write.csv(calib, "full_cohort_calibration.csv", row.names = FALSE)
cat(sprintf(
    "   Calibration Range: %.2f%% - %.2f%%\n",
    min(calib$Mean_Predicted_Risk), max(calib$Mean_Predicted_Risk)
))

# Survival Probabilities
results_surv <- data.frame()

for (group in c("High", "Low")) {
    sub <- predictions[predictions$Risk_Group == group, ]
    fit <- survfit(Surv(Observed_Time, Observed_Status) ~ 1, data = sub)
    summ <- summary(fit, times = c(30, 60), extend = TRUE)

    row <- data.frame(
        Group = group,
        N = nrow(sub),
        Events = sum(sub$Observed_Status),
        Surv_30d = if (length(summ$surv) >= 1) summ$surv[1] else NA,
        CI_30d_Lower = if (length(summ$lower) >= 1) summ$lower[1] else NA,
        CI_30d_Upper = if (length(summ$upper) >= 1) summ$upper[1] else NA,
        Surv_60d = if (length(summ$surv) >= 2) summ$surv[2] else NA,
        CI_60d_Lower = if (length(summ$lower) >= 2) summ$lower[2] else NA,
        CI_60d_Upper = if (length(summ$upper) >= 2) summ$upper[2] else NA
    )
    results_surv <- rbind(results_surv, row)
}

write.csv(results_surv, "full_cohort_survival_probs.csv", row.names = FALSE)
cat("\n   Survival Probabilities:\n")
print(results_surv)

# Hazard Ratio
predictions$is_high_risk <- ifelse(predictions$Risk_Group == "High", 1, 0)
cox_fit <- coxph(Surv(Observed_Time, Observed_Status) ~ is_high_risk, data = predictions)
hr <- exp(coef(cox_fit))
ci <- exp(confint(cox_fit))
p <- summary(cox_fit)$coefficients[, "Pr(>|z|)"]

hr_result <- data.frame(
    HR = hr,
    CI_Lower = ci[1],
    CI_Upper = ci[2],
    P_Value = p,
    Significant = ifelse(p < 0.05, "YES", "NO")
)

write.csv(hr_result, "full_cohort_hazard_ratio.csv", row.names = FALSE)
cat(sprintf("\n   HR: %.2f (95%% CI: %.2f-%.2f), p=%.4f\n", hr, ci[1], ci[2], p))
cat(sprintf("   Statistically significant: %s\n\n", hr_result$Significant))

cat("================================================================================\n")
cat("ALL DONE! Results saved to CSV files.\n")
cat("================================================================================\n")
