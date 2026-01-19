#!/bin/bash

# Define the main filename without extension
FILENAME="Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests A MIMIC-IV Database Study with Methodological Validation"

echo "Compiling LaTeX..."
pdflatex "$FILENAME.tex"

echo "Processing Bibliography..."
bibtex "$FILENAME"

echo "Compiling LaTeX (Pass 2)..."
pdflatex "$FILENAME.tex"

echo "Compiling LaTeX (Pass 3)..."
pdflatex "$FILENAME.tex"

echo "Done! Output: $FILENAME.pdf"
