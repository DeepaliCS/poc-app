#!/bin/bash
# ── setup.sh ── first-time environment setup ──────────────────
# Run this once after cloning the repo.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_NAME="poc_app"
CONDA_SH=""
for p in \
    "$HOME/anaconda3/etc/profile.d/conda.sh" \
    "$HOME/miniconda3/etc/profile.d/conda.sh" \
    "/opt/anaconda3/etc/profile.d/conda.sh" \
    "/opt/miniconda3/etc/profile.d/conda.sh" \
    "/opt/conda/etc/profile.d/conda.sh"
do
    [ -f "$p" ] && CONDA_SH="$p" && break
done

if [ -z "$CONDA_SH" ]; then
    echo "  ✗ Conda not found. Please install Miniconda:"
    echo "    https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

source "$CONDA_SH"

echo ""
echo "  → Creating conda environment: $ENV_NAME (Python 3.11)"
conda create -n "$ENV_NAME" python=3.11 -y
conda activate "$ENV_NAME"

echo "  → Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "  ✓ Created .env from template."
    echo "  ✗ Open .env and fill in your cTrader credentials before running."
else
    echo "  ✓ .env already exists."
fi

echo ""
echo "  ✓ Setup complete."
echo "  → To start the app: bash scripts/run.sh"
echo ""
