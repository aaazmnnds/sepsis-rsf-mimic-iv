# GitHub Upload Guide

## Step-by-Step Instructions for Uploading Your Sepsis RSF Project

### Prerequisites
- Git installed on your computer
- GitHub account (can use any email)
- Terminal/Command Prompt access

---

## Part 1: Configure Git with Your Email

### Option A: Configure Globally (affects all repositories)
```bash
git config --global user.name "Your Name"
git config --global user.email "azmannads@msutawi-tawi.edu.ph"
```

### Option B: Configure for This Repository Only
```bash
cd "/Users/azmannads/Downloads/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"

git config user.name "Your Name"
git config user.email "azmannads@msutawi-tawi.edu.ph"
```

**Note:** The email doesn't have to match your GitHub account email. You can use any email you want to appear in the commit history.

---

## Part 2: Create GitHub Repository

1. Go to https://github.com
2. Click the **"+"** icon (top right) → **"New repository"**
3. Fill in:
   - **Repository name:** `sepsis-rsf-mimic-iv` (or your preferred name)
   - **Description:** "Survival analysis of postoperative sepsis using Random Survival Forests and deep learning imputation (MIMIC-IV)"
   - **Visibility:** Public or Private (your choice)
   - **DO NOT** initialize with README (we already have one)
4. Click **"Create repository"**

GitHub will show you a page with commands. **Keep this page open.**

---

## Part 3: Organize Your Files (Already Done!)

I've created the following structure for you:

```
✅ README.md          - Project documentation
✅ requirements.txt   - Python dependencies
✅ .gitignore         - Files to exclude from Git
✅ LICENSE            - MIT License

Your existing files:
✅ All R scripts (*.R)
✅ All Python scripts (*.py)
✅ All CSV data files (*.csv)
✅ All output files
```

---

## Part 4: Initialize Git and Upload

### Step 1: Navigate to your project directory
```bash
cd "/Users/azmannads/Downloads/Dr. Zhang/Content/Application of Random Survival Forests for the Analysis of Sepsis After Laparoscopic Surgery/Revised paper/Revised 1"
```

### Step 2: Initialize Git repository
```bash
git init
```

### Step 3: Add all files
```bash
git add .
```

**Check what will be committed:**
```bash
git status
```

### Step 4: Create first commit
```bash
git commit -m "Initial commit: Complete sepsis RSF analysis with MIMIC-IV data"
```

### Step 5: Link to GitHub (replace with YOUR repository URL)
```bash
git remote add origin https://github.com/YOUR_USERNAME/sepsis-rsf-mimic-iv.git
```

**Example:**
```bash
git remote add origin https://github.com/azmannads/sepsis-rsf-mimic-iv.git
```

### Step 6: Push to GitHub
```bash
git branch -M main
git push -u origin main
```

**If prompted for credentials:**
- Username: Your GitHub username
- Password: Use a **Personal Access Token** (not your GitHub password)

---

## Part 5: Create Personal Access Token (if needed)

If GitHub asks for a password, you need a Personal Access Token:

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: "Sepsis RSF Upload"
4. Select scopes: Check **"repo"** (full control of private repositories)
5. Click **"Generate token"**
6. **COPY THE TOKEN** (you won't see it again!)
7. Use this token as your password when pushing

---

## Part 6: Verify Upload

1. Go to your GitHub repository URL
2. You should see:
   - ✅ README.md displayed on the main page
   - ✅ All your scripts in the file list
   - ✅ All CSV files
   - ✅ LICENSE and .gitignore

---

## Troubleshooting

### Problem: "Large files detected"
If GitHub rejects files >100MB:

```bash
# Remove large files from tracking
git rm --cached path/to/large/file.csv

# Add to .gitignore
echo "path/to/large/file.csv" >> .gitignore

# Commit and push again
git commit -m "Remove large files"
git push
```

**Alternative:** Use Git LFS (Large File Storage)
```bash
git lfs install
git lfs track "*.csv"
git add .gitattributes
git commit -m "Track CSV files with Git LFS"
git push
```

### Problem: "Permission denied"
- Make sure you're using a Personal Access Token, not your password
- Check that the token has "repo" permissions

### Problem: "Repository not found"
- Double-check the repository URL
- Make sure the repository exists on GitHub
- Verify you have access to the repository

---

## Optional: Create Organized Folder Structure

If you want to organize files into folders before uploading:

```bash
# Create directories
mkdir -p data/primary data/imputed data/outputs
mkdir -p scripts/utils
mkdir -p results/figures results/tables

# Move files (examples)
mv mimic_sepsis_cohort_full.csv data/primary/
mv imputed_*.csv data/imputed/
mv *_predictions.csv data/outputs/
mv *.png results/figures/

# Commit changes
git add .
git commit -m "Organize files into directories"
git push
```

---

## Quick Reference Commands

```bash
# Check status
git status

# Add specific file
git add filename.py

# Add all files
git add .

# Commit changes
git commit -m "Your commit message"

# Push to GitHub
git push

# Pull latest changes
git pull

# View commit history
git log --oneline
```

---

## Next Steps After Upload

1. **Add badges** to README (DOI, license, etc.)
2. **Create releases** for published versions
3. **Add documentation** in `docs/` folder
4. **Enable GitHub Pages** for project website (optional)
5. **Add collaborators** if working with others

---

## Need Help?

- GitHub Docs: https://docs.github.com/en/get-started
- Git Tutorial: https://git-scm.com/docs/gittutorial
- Contact me if you encounter issues!
