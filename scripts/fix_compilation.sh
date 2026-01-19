#!/bin/bash
FILE="Survival Analysis of Sepsis After Laparoscopic Surgery Using Random Survival Forests A MIMIC-IV Database Study with Methodological Validation"

echo "Cleaning auxiliary files..."
rm -f *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot

echo "Pass 1: pdflatex (generate .aux)"
pdflatex -interaction=nonstopmode "$FILE" || true

echo "Pass 2: bibtex (generate .bbl)"
bibtex "$FILE" || true

echo "Pass 3: pdflatex (integrate citations)"
pdflatex -interaction=nonstopmode "$FILE" || true

echo "Pass 4: pdflatex (resolve references)"
pdflatex -interaction=nonstopmode "$FILE" || true

echo "Compilation complete."
