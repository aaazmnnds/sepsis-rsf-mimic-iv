#!/usr/bin/env Rscript
# Extract Full Test Set Statistics from model_predictions.csv
# ===========================================================

library(survival)
library(dplyr)

cat("================================================================================\n")
cat("EXTRACTING FULL TEST SET STATISTICS\n")
cat("================================================================================\n\n")

# ============================================================================
# 1. LOAD FULL MODEL PREDICTIONS
# ============================================================================
cat("1. Loading full model predictions...\n")

data <- read.csv("model_predictions.csv")
cat(sprintf("   Loaded %d total predictions\n", nrow(data)))

# Filter for RSF + GAIN + full/real mechanism (not simulation)
rsf_gain <- data %>%
    filter(Model == "RSF", Imputation == "GAIN")

cat(sprintf("   RSF-GAIN total: %d rows\n", nrow(rsf_gain)))

# Check mechanisms available
mechanisms <- unique(rsf_gain$Mechanism)
cat(sprintf("   Available mechanisms: %s\n", paste(mechanisms, collapse = ", ")))

# Select the "real" data (not simulated)
if ("full" %in% mechanisms) {
    rsf_gain <- rsf_gain %>% filter(Mechanism == "full")
    cat("   Using mechanism: full\n")
} else if ("real" %in% mechanisms) {
    rsf_gain <- rsf_gain %>% filter(Mechanism == "real")
    cat("   Using mechanism: real\n")
} else {
    rsf_gain <- rsf_gain %>% filter(Mechanism == mechanisms[1])
    cat(sprintf("   Using mechanism: %s\n", mechanisms[1]))
}

cat(sprintf("   Final dataset: n=%d\n", nrow(rsf_gain)))

# Convert status to numeric FIRST (before any calculations)
rsf_gain$Observed_Status <- ifelse(rsf_gain$Observed_Status == "True" | rsf_gain$Observed_Status == TRUE, 1, 0)

cat(sprintf(
    "   Events: %d (%.1f%%)\n",
    sum(rsf_gain$Observed_Status),
    100 * mean(rsf_gain$Observed_Status)
))

# Create risk groups (median split)
median_risk <- median(rsf_gain$Predicted_Risk)
rsf_gain$Risk_Group <- ifelse(rsf_gain$Predicted_Risk >= median_risk, "High", "Low")

# ============================================================================
# 2. CALIBRATION STATISTICS
# ============================================================================
cat("\n2. Calculating calibration statistics...\n")

rsf_gain$risk_decile <- cut(
    rsf_gain$Predicted_Risk,
    breaks = quantile(rsf_gain$Predicted_Risk, probs = seq(0, 1, 0.1)),
    labels = FALSE,
    include.lowest = TRUE
)

calib <- rsf_gain %>%
    group_by(risk_decile) %>%
    summarise(
        Mean_Predicted_Risk = mean(Predicted_Risk),
        Observed_Event_Rate = mean(Observed_Status)
    )

write.csv(calib, "full_test_calibration.csv", row.names = FALSE)
cat(sprintf(
    "   Predicted Risk Range: %.4f - %.4f\n",
    min(calib$Mean_Predicted_Risk), max(calib$Mean_Predicted_Risk)
))
cat(sprintf(
    "   Observed Rate Range: %.4f - %.4f\n",
    min(calib$Observed_Event_Rate), max(calib$Observed_Event_Rate)
))
cat("   Saved: full_test_calibration.csv\n")

# ============================================================================
# 3. SURVIVAL PROBABILITIES
# ============================================================================
cat("\n3. Calculating survival probabilities...\n")

km_fit <- survfit(Surv(Observed_Time, Observed_Status) ~ Risk_Group, data = rsf_gain)

results_surv <- data.frame()

for (group in c("High", "Low")) {
    sub <- rsf_gain[rsf_gain$Risk_Group == group, ]
    fit <- survfit(Surv(Observed_Time, Observed_Status) ~ 1, data = sub)
    summ <- summary(fit, times = c(30, 60), extend = TRUE)

    s30 <- if (length(summ$surv) >= 1) summ$surv[1] else NA
    l30 <- if (length(summ$lower) >= 1) summ$lower[1] else NA
    u30 <- if (length(summ$upper) >= 1) summ$upper[1] else NA

    s60 <- if (length(summ$surv) >= 2) summ$surv[2] else NA
    l60 <- if (length(summ$lower) >= 2) summ$lower[2] else NA
    u60 <- if (length(summ$upper) >= 2) summ$upper[2] else NA

    row <- data.frame(
        Group = group,
        N = nrow(sub),
        Events = sum(sub$Observed_Status),
        Surv_30d = s30, CI_30d_Lower = l30, CI_30d_Upper = u30,
        Surv_60d = s60, CI_60d_Lower = l60, CI_60d_Upper = u60
    )
    results_surv <- rbind(results_surv, row)
}

write.csv(results_surv, "full_test_survival_probs.csv", row.names = FALSE)
cat("   Survival Probabilities:\n")
print(results_surv)
cat("   Saved: full_test_survival_probs.csv\n")

# ============================================================================
# 4. HAZARD RATIO
# ============================================================================
cat("\n4. Calculating hazard ratio...\n")

rsf_gain$is_high_risk <- ifelse(rsf_gain$Risk_Group == "High", 1, 0)

cox_fit <- coxph(Surv(Observed_Time, Observed_Status) ~ is_high_risk, data = rsf_gain)
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

write.csv(hr_result, "full_test_hazard_ratio.csv", row.names = FALSE)
cat(sprintf("   HR: %.2f (95%% CI: %.2f-%.2f), p=%.4f\n", hr, ci[1], ci[2], p))
cat(sprintf("   Statistically significant: %s\n", hr_result$Significant))
cat("   Saved: full_test_hazard_ratio.csv\n")

# ============================================================================
# 5. SUMMARY
# ============================================================================
cat("\n================================================================================\n")
cat("EXTRACTION COMPLETE\n")
cat("================================================================================\n")
cat("\nGenerated files:\n")
cat("  1. full_test_calibration.csv\n")
cat("  2. full_test_survival_probs.csv\n")
cat("  3. full_test_hazard_ratio.csv\n")
cat("\nNext steps:\n")
if (hr_result$Significant == "YES") {
    cat("  ✓ P-value is significant - safe to use in manuscript\n")
    cat("  → Update Section 3.1.3 with these values\n")
} else {
    cat("  ✗ P-value is NOT significant - investigate further\n")
    cat("  → Check sample size, event rate, and model performance\n")
}
cat("================================================================================\n")