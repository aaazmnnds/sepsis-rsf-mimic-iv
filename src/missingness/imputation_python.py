import os
import glob
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from tqdm import tqdm
import argparse

# Set seeds for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# ==============================================================================
# MIDA Implementation (Denoising Autoencoder)
# ==============================================================================
class MIDA(nn.Module):
    def __init__(self, input_dim, latent_dim=10, theta=7):
        super(MIDA, self).__init__()
        self.input_dim = input_dim
        self.theta = theta

        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim + input_dim, latent_dim * 2), # Input + Mask
            nn.Tanh(),
            nn.Linear(latent_dim * 2, latent_dim * 2),
            nn.Tanh(),
            nn.Linear(latent_dim * 2, latent_dim)
        )

        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, latent_dim * 2),
            nn.Tanh(),
            nn.Linear(latent_dim * 2, latent_dim * 2),
            nn.Tanh(),
            nn.Linear(latent_dim * 2, input_dim),
            nn.Sigmoid() # Assuming normalized data [0, 1]
        )

    def forward(self, x, m):
        # Concatenate Input and Mask
        inputs = torch.cat([x, m], dim=1)
        z = self.encoder(inputs)
        reconstruction = self.decoder(z)
        return reconstruction

def run_mida(data, epochs=500, batch_size=64):
    print("Running MIDA imputation...")

    # 1. Normalization (Min-Max)
    min_val = np.nanmin(data, axis=0)
    max_val = np.nanmax(data, axis=0)
    # Avoid division by zero
    denom = max_val - min_val
    denom[denom == 0] = 1e-6

    norm_data = (data - min_val) / denom

    # Fill NaN with 0 for initial input
    filled_data = np.nan_to_num(norm_data, nan=0.0)

    # Mask: 1 if observed, 0 if missing
    mask = (~np.isnan(data)).astype(float)

    # Convert to Tensor
    tensor_data = torch.FloatTensor(filled_data)
    tensor_mask = torch.FloatTensor(mask)

    dataset = TensorDataset(tensor_data, tensor_mask)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = MIDA(input_dim=data.shape[1])
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    model.train()
    for epoch in tqdm(range(epochs), desc="MIDA Training"):
        for batch_x, batch_m in dataloader:
            optimizer.zero_grad()
            recon = model(batch_x, batch_m)
            # Loss only on observed data
            loss = criterion(recon * batch_m, batch_x * batch_m)
            loss.backward()
            optimizer.step()

    # Imputation
    model.eval()
    with torch.no_grad():
        imputed_norm = model(tensor_data, tensor_mask).numpy()

    # Restore scale
    imputed_data_norm = filled_data * mask + imputed_norm * (1 - mask)
    imputed_data = imputed_data_norm * denom + min_val

    return imputed_data

# ==============================================================================
# GAIN Implementation (Generative Adversarial Imputation Nets)
# ==============================================================================
class Generator(nn.Module):
    def __init__(self, dim):
        super(Generator, self).__init__()
        self.main = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.Sigmoid()
        )
    def forward(self, x, m):
        inputs = torch.cat([x, m], dim=1)
        return self.main(inputs)

class Discriminator(nn.Module):
    def __init__(self, dim):
        super(Discriminator, self).__init__()
        self.main = nn.Sequential(
            nn.Linear(dim * 2, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.ReLU(),
            nn.Linear(dim, dim),
            nn.Sigmoid()
        )
    def forward(self, x, h):
        inputs = torch.cat([x, h], dim=1)
        return self.main(inputs)

def run_gain(data, alpha=100, epochs=500, batch_size=64):
    print("Running GAIN imputation...")

    dim = data.shape[1]

    # 1. Normalization
    min_val = np.nanmin(data, axis=0)
    max_val = np.nanmax(data, axis=0)
    denom = max_val - min_val
    denom[denom == 0] = 1e-6

    norm_data = (data - min_val) / denom
    filled_data = np.nan_to_num(norm_data, nan=0.0)
    mask = (~np.isnan(data)).astype(float)

    tensor_data = torch.FloatTensor(filled_data)
    tensor_mask = torch.FloatTensor(mask)

    dataset = TensorDataset(tensor_data, tensor_mask)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    G = Generator(dim)
    D = Discriminator(dim)

    G_optim = optim.Adam(G.parameters())
    D_optim = optim.Adam(D.parameters())

    # Training
    for epoch in tqdm(range(epochs), desc="GAIN Training"):
        for batch_x, batch_m in dataloader:

            # Sample Random Noise & Hint
            Z_mb = torch.rand_like(batch_x)
            H_mb = 1.0 * (torch.rand_like(batch_m) < 0.9) # Hint vector

            # Combine random noise with observed data
            X_mb = batch_m * batch_x + (1 - batch_m) * Z_mb

            # --- Train Discriminator ---
            D_optim.zero_grad()
            G_sample = G(X_mb, batch_m)
            X_hat = batch_x * batch_m + G_sample * (1 - batch_m)
            D_prob = D(X_hat, H_mb)

            D_loss = -torch.mean(batch_m * torch.log(D_prob + 1e-8) + (1 - batch_m) * torch.log(1 - D_prob + 1e-8))
            D_loss.backward()
            D_optim.step()

            # --- Train Generator ---
            G_optim.zero_grad()
            G_sample = G(X_mb, batch_m)
            X_hat = batch_x * batch_m + G_sample * (1 - batch_m)
            D_prob = D(X_hat, H_mb)

            # MSE Loss for observed components
            MSE_loss = torch.mean((batch_m * batch_x - batch_m * G_sample)**2) / torch.mean(batch_m)

            # Adversarial Loss
            G_loss_temp = -torch.mean((1 - batch_m) * torch.log(D_prob + 1e-8))

            G_loss = G_loss_temp + alpha * MSE_loss
            G_loss.backward()
            G_optim.step()

    # Imputation
    with torch.no_grad():
        Z_final = torch.rand_like(tensor_data)
        X_final = tensor_mask * tensor_data + (1 - tensor_mask) * Z_final
        G_final = G(X_final, tensor_mask)
        imputed_norm = tensor_mask * tensor_data + (1 - tensor_mask) * G_final
        imputed_norm = imputed_norm.numpy()

    # Restore scale
    imputed_data = imputed_norm * denom + min_val
    return imputed_data

# ==============================================================================
# Workflow
# ==============================================================================

def main():
    # Absolute Path Configuration
    ROOT_DIR = "/Users/nazu.ds/Documents/Research Collections/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
    DATA_DIR = os.path.join(ROOT_DIR, "Results sensitivity")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run GAIN/MIDA imputation on synthetic datasets.')
    parser.add_argument('--rates', nargs='+', help='Specific missingness rates to process (e.g., 10 40 55)')
    args = parser.parse_args()

    files = glob.glob(os.path.join(DATA_DIR, "synthetic_*.csv"))
    files = [f for f in files if "complete" not in f]

    # Filter by rates if specified
    if args.rates:
        print(f"Filtering for specific rates: {args.rates}")
        filtered_files = []
        for f in files:
            # Check if any of the target rates are in the filename (e.g., _10.csv)
            if any(f"_{rate}.csv" in f for rate in args.rates):
                filtered_files.append(f)
        files = filtered_files
        print(f"Files remaining after filtering: {len(files)}")

    if not files:
        print("No matching synthetic data files found.")
        return

    # Create output directory
    output_dir = os.path.join(ROOT_DIR, "Results sensitivity")
    os.makedirs(output_dir, exist_ok=True)

    for file in files:
        mechanism = os.path.basename(file).replace("synthetic_", "").replace(".csv", "")
        print(f"\nProcessing mechanism: {mechanism}")

        # Determine separability of non-numeric data if any, but simulation script usually produces numeric
        # Assuming only numeric features for DL models here.
        df = pd.read_csv(file)

        # Store non-numeric columns to append later if needed, assume all numeric for now based on simulation
        # If ID or non-numeric exists, drop for imputation
        data_numeric = df.select_dtypes(include=[np.number]).values

        # 1. Run MIDA
        filename_mida = os.path.join(output_dir, f"MIDA_{mechanism}.csv")
        if os.path.exists(filename_mida):
            print(f"Skipping MIDA for {mechanism} - already exists at {filename_mida}")
        else:
            try:
                mida_imputed = run_mida(data_numeric)
                mida_df = pd.DataFrame(mida_imputed, columns=df.select_dtypes(include=[np.number]).columns)
                mida_df.to_csv(filename_mida, index=False)
                print(f"Saved: {filename_mida}")
            except Exception as e:
                print(f"Error in MIDA for {mechanism}: {e}")

        # 2. Run GAIN
        filename_gain = os.path.join(output_dir, f"GAIN_{mechanism}.csv")
        if os.path.exists(filename_gain):
            print(f"Skipping GAIN for {mechanism} - already exists at {filename_gain}")
        else:
            try:
                gain_imputed = run_gain(data_numeric)
                gain_df = pd.DataFrame(gain_imputed, columns=df.select_dtypes(include=[np.number]).columns)
                gain_df.to_csv(filename_gain, index=False)
                print(f"Saved: {filename_gain}")
            except Exception as e:
                print(f"Error in GAIN for {mechanism}: {e}")

    # ==============================================================================
    # Process Real MIMIC Data
    # ==============================================================================

    mimic_file = os.path.join(ROOT_DIR, "mimic_sepsis_cohort_full.csv")

    if os.path.exists(mimic_file):
        print(f"\nProcessing real MIMIC data: {mimic_file}")

        # Read real MIMIC data
        df_full = pd.read_csv(mimic_file)

        # Extract numeric columns only
        data_numeric_full = df_full.select_dtypes(include=[np.number]).values

        # 1. Run MIDA
        filename_mida_full = os.path.join(output_dir, "MIDA_mimic_sepsis_cohort_full.csv")
        if os.path.exists(filename_mida_full):
            print(f"Skipping MIDA for real MIMIC data - already exists")
        else:
            try:
                mida_imputed_full = run_mida(data_numeric_full)
                mida_df_full = pd.DataFrame(mida_imputed_full, columns=df_full.select_dtypes(include=[np.number]).columns)
                mida_df_full.to_csv(filename_mida_full, index=False)
                print(f"Saved: {filename_mida_full}")
            except Exception as e:
                print(f"Error in MIDA for real MIMIC data: {e}")

        # 2. Run GAIN
        filename_gain_full = os.path.join(output_dir, "GAIN_mimic_sepsis_cohort_full.csv")
        if os.path.exists(filename_gain_full):
            print(f"Skipping GAIN for real MIMIC data - already exists")
        else:
            try:
                gain_imputed_full = run_gain(data_numeric_full)
                gain_df_full = pd.DataFrame(gain_imputed_full, columns=df_full.select_dtypes(include=[np.number]).columns)
                gain_df_full.to_csv(filename_gain_full, index=False)
                print(f"Saved: {filename_gain_full}")
            except Exception as e:
                print(f"Error in GAIN for real MIMIC data: {e}")
    else:
        print(f"\nWarning: Real MIMIC data file not found: {mimic_file}")

if __name__ == "__main__":
    main()