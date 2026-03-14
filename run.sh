#!/bin/bash
# ── run.sh ── launches the app ────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
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

source "$CONDA_SH"
conda activate "$ENV_NAME"

echo ""
echo "  POC App  →  http://127.0.0.1:8050"
echo "  Ctrl+C to stop"
echo ""
python app.py
