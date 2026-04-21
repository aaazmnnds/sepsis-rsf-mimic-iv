# Load necessary libraries
packages <- c("tidyverse", "naniar", "ggplot2", "patchwork")

for (pkg in packages) {
  if (!require(pkg, character.only = TRUE)) {
    message(paste("Installing", pkg, "..."))
    install.packages(pkg)
    library(pkg, character.only = TRUE)
  }
}

# -----------------------------------------------------------------------------
# 1. Load Data
# -----------------------------------------------------------------------------

# Get synthetic datasets (MCAR, MAR, MNAR) - EXCLUDE complete data
files <- list.files(pattern = "synthetic_.*\\.csv")
files <- files[!grepl("complete", files)] # Exclude synthetic_complete.csv

# Add real MIMIC data if it exists
if (file.exists("mimic_sepsis_cohort_full.csv")) {
  files <- c(files, "mimic_sepsis_cohort_full.csv")
}

message("Files to process: ", paste(files, collapse = ", "))

# Function to read and label data
read_and_label <- function(filename) {
  df <- read.csv(filename)

  # Rename columns if needed (Time -> Survival_Time, Event -> Status)
  if ("Time" %in% names(df)) {
    names(df)[names(df) == "Time"] <- "Survival_Time"
  }
  if ("Event" %in% names(df)) {
    names(df)[names(df) == "Event"] <- "Status"
  }

  # Label the dataset
  if (filename == "mimic_sepsis_cohort_full.csv") {
    df$Dataset <- "Real Data (MIMIC)"
  } else {
    # Extract mechanism from filename: synthetic_mcar.csv -> MCAR
    mechanism <- gsub("synthetic_", "", gsub("\\.csv", "", filename))
    df$Dataset <- toupper(mechanism) # Convert to uppercase (MCAR, MAR, MNAR)
  }

  # Ensure Sex is character to avoid type mismatch (M/F vs 0/1)
  if ("Sex" %in% names(df)) {
    df$Sex <- as.character(df$Sex)
  }

  return(df)
}

# Load all data
data_list <- lapply(files, read_and_label)
all_data <- bind_rows(data_list)

# Factorize 'Dataset' with proper order
all_data$Dataset <- factor(all_data$Dataset,
  levels = c("MCAR", "MAR", "MNAR", "Real Data (MIMIC)")
)

message("Loaded datasets: ", paste(unique(all_data$Dataset), collapse = ", "))
message("Total rows: ", nrow(all_data))
message("Columns: ", paste(names(all_data), collapse = ", "))

# Check for missing data
message("\nMissing data summary:")
missing_summary <- all_data %>%
  group_by(Dataset) %>%
  summarise(across(everything(), ~ sum(is.na(.)))) %>%
  pivot_longer(-Dataset, names_to = "Variable", values_to = "Missing_Count")

print(missing_summary %>% filter(Missing_Count > 0))

# -----------------------------------------------------------------------------
# 2. Distribution Plots (Continuous Variables)
# -----------------------------------------------------------------------------

# Plot distributions of OBSERVED data (ignoring missing values)
plot_distribution <- function(var_name, title) {
  # Check if variable exists
  if (!var_name %in% names(all_data)) {
    message(paste("Warning: Variable", var_name, "not found in data"))
    return(NULL)
  }

  p <- ggplot(all_data, aes(x = .data[[var_name]], fill = Dataset, color = Dataset)) +
    geom_density(alpha = 0.3, na.rm = TRUE) +
    labs(title = title, x = var_name, y = "Density") +
    theme_minimal() +
    theme(
      legend.position = "bottom",
      legend.title = element_text(size = 10),
      legend.text = element_text(size = 9)
    )
  return(p)
}

# Create plots for key variables
p1 <- plot_distribution("Age", "Distribution of Age")
p2 <- plot_distribution("HR", "Distribution of Heart Rate")
p3 <- plot_distribution("Lac", "Distribution of Lactate")
p4 <- plot_distribution("Plt", "Distribution of Platelets")

# Combine plots
combined_plot <- (p1 + p2) / (p3 + p4) +
  plot_annotation(
    title = "Feature Distributions Across Missing Data Mechanisms",
    subtitle = "Based on observed (non-missing) values"
  )

ggsave("data_distribution_plots.png", combined_plot,
  width = 12, height = 10, dpi = 300
)
message("Saved 'data_distribution_plots.png'")

# -----------------------------------------------------------------------------
# 3. Missingness Maps for Synthetic Data
# -----------------------------------------------------------------------------

# Create missingness maps for each mechanism (MCAR, MAR, MNAR)
mechanisms <- c("MCAR", "MAR", "MNAR")

for (mech in mechanisms) {
  mech_data <- all_data %>%
    filter(Dataset == mech) %>%
    select(-Dataset, -Survival_Time, -Status) # Exclude outcome vars and label

  if (nrow(mech_data) > 0) {
    filename <- paste0("missingness_map_", tolower(mech), ".png")

    png(filename, width = 1200, height = 800, res = 150)
    print(
      vis_miss(mech_data) +
        labs(title = paste("Missingness Map (", mech, "Mechanism)", sep = "")) +
        theme(axis.text.x = element_text(angle = 45, hjust = 1))
    )
    dev.off()

    message(paste("Saved", filename))
  }
}

# Create UpSet plot for MAR (representative example)
mar_data <- all_data %>%
  filter(Dataset == "MAR") %>%
  select(-Dataset, -Survival_Time, -Status)

if (nrow(mar_data) > 0) {
  png("missingness_upset_mar.png", width = 1200, height = 800, res = 150)
  print(gg_miss_upset(mar_data, nsets = 10, nintersects = 20))
  dev.off()
  message("Saved 'missingness_upset_mar.png'")
}

# -----------------------------------------------------------------------------
# 4. Real Data Missingness (MIMIC)
# -----------------------------------------------------------------------------

real_data <- all_data %>%
  filter(Dataset == "Real Data (MIMIC)") %>%
  select(-Dataset, -Survival_Time, -Status)

if (nrow(real_data) > 0) {
  png("missingness_map_real.png", width = 1200, height = 800, res = 150)
  print(
    vis_miss(real_data) +
      labs(title = "Missingness Map (Real MIMIC-IV Data)") +
      theme(axis.text.x = element_text(angle = 45, hjust = 1))
  )
  dev.off()
  message("Saved 'missingness_map_real.png'")

  # UpSet plot for real data
  png("missingness_upset_real.png", width = 1200, height = 800, res = 150)
  print(gg_miss_upset(real_data, nsets = 10, nintersects = 20))
  dev.off()
  message("Saved 'missingness_upset_real.png'")
} else {
  message("No real MIMIC data found")
}

# -----------------------------------------------------------------------------
# 5. Missingness Summary Table
# -----------------------------------------------------------------------------

# Create summary statistics for missingness
miss_summary <- all_data %>%
  group_by(Dataset) %>%
  summarise(
    N = n(),
    across(
      where(is.numeric),
      list(
        Missing_N = ~ sum(is.na(.)),
        Missing_Pct = ~ round(100 * sum(is.na(.)) / n(), 1)
      ),
      .names = "{.col}_{.fn}"
    )
  )

# Save to CSV
write.csv(miss_summary, "missingness_summary.csv", row.names = FALSE)
message("Saved 'missingness_summary.csv'")

# -----------------------------------------------------------------------------
# 6. Comparison Plot: Complete vs. Missing Mechanisms
# -----------------------------------------------------------------------------

# If you want to compare with complete data, load it separately
if (file.exists("synthetic_complete.csv")) {
  complete_data <- read.csv("synthetic_complete.csv")
  complete_data$Dataset <- "Complete"

  # Combine with existing data for comparison
  comparison_data <- bind_rows(
    complete_data,
    all_data
  )

  comparison_data$Dataset <- factor(
    comparison_data$Dataset,
    levels = c("Complete", "MCAR", "MAR", "MNAR", "Real Data (MIMIC)"),
    labels = c("Complete", "MCAR", "MAR", "MNAR", "MIMIC-IV")
  )

  # Create comparison plot
  p_compare <- ggplot(
    comparison_data,
    aes(x = Lac, fill = Dataset, color = Dataset)
  ) +
    geom_density(alpha = 0.3, na.rm = TRUE) +
    labs(
      title = "Lactate Distribution: Complete vs. Missing Data Mechanisms",
      x = "Lactate", y = "Density"
    ) +
    theme_minimal() +
    theme(legend.position = "bottom")

  ggsave("distribution_comparison_complete_vs_missing.png",
    p_compare,
    width = 10, height = 6, dpi = 300
  )
  message("Saved 'distribution_comparison_complete_vs_missing.png'")
}

message("\n", paste(rep("=", 70), collapse = ""))
message("Data visualization completed successfully!")
message(paste(rep("=", 70), collapse = ""))