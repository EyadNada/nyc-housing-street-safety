#!/usr/bin/env bash
# Assemble the notebook from its source parts and run it from top to bottom.
set -e
cd "$(dirname "$0")"
cat notebook_src/part*.py > notebook_src/_combined.py
jupytext --quiet --to ipynb --output Milestone1_Housing_x_StreetSafety.ipynb notebook_src/_combined.py
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 Milestone1_Housing_x_StreetSafety.ipynb
rm notebook_src/_combined.py
echo "Notebook built and executed."
