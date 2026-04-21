#!/usr/bin/env Rscript
# Corrected Full Cohort Analysis with Proper Risk Score Calculation
# ==================================================================

library(survival)
library(dplyr)

cat("================================================================================\n")
cat("CORRECTED FULL COHORT ANALYSIS (n=852)\n")
cat("================================================================================\n\n")

# Load predictions
data <- read.csv("full_cohort_rsf_predictions.csv")
cat(sprintf("Loaded predictions: n=%d\n", nrow(data)))

# CORRECT THE RISK SCORES
# RSF predicts survival time, so INVERT it to get risk scores
# Lower predicted time = Higher risk
data$Predicted_Risk_Corrected <- -data$Predicted_Risk # Negative = higher risk for lower survival time

# Recreate risk groups with corrected scores
median_risk <- median(data$Predicted_Risk_Corrected)
data$Risk_Group_Corrected <- ifelse(data$Predicted_Risk_Corrected >= median_risk, "High", "Low")

cat("\nCorrected Risk Groups:\n")
for (group in c("High", "Low")) {
    subset <- data[data$Risk_Group_Corrected == group, ]
    cat(sprintf(
        "  %s: n=%d, events=%d (%.1f%%)\n",
        group, nrow(subset), sum(subset$Observed_Status), 100 * mean(subset$Observed_Status)
    ))
}

# Calculate Hazard Ratio with corrected groups
data$is_high_risk <- ifelse(data$Risk_Group_Corrected == "High", 1, 0)
cox_fit <- coxph(Surv(Observed_Time, Observed_Status) ~ is_high_risk, data = data)
hr <- exp(coef(cox_fit))
ci <- exp(confint(cox_fit))
p <- summary(cox_fit)$coefficients[, "Pr(>|z|)"]

cat(sprintf("\nCorrected Hazard Ratio:\n"))
cat(sprintf("  HR: %.2f (95%% CI: %.2f-%.2f), p=%.4f\n", hr, ci[1], ci[2], p))
cat(sprintf("  Significant: %s\n", ifelse(p < 0.05, "YES", "NO")))

# Save corrected results
hr_result <- data.frame(
    HR = hr,
    CI_Lower = ci[1],
    CI_Upper = ci[2],
    P_Value = p,
    Significant = ifelse(p < 0.05, "YES", "NO")
)
write.csv(hr_result, "full_cohort_hazard_ratio_corrected.csv", row.names = FALSE)

# Calculate survival probabilities with corrected groups
results_surv <- data.frame()

for (group in c("High", "Low")) {
    sub <- data[data$Risk_Group_Corrected == group, ]
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

write.csv(results_surv, "full_cohort_survival_probs_corrected.csv", row.names = FALSE)
cat("\nSurvival Probabilities (Corrected):\n")
print(results_surv)

cat("\n================================================================================\n")
cat("CORRECTED ANALYSIS COMPLETE\n")
cat("================================================================================\n")