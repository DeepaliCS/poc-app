#!/bin/bash
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

# Install/update packages
pip install -r requirements.txt -q

# Check .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "  ✗ No .env file found!"
    echo "    cp .env.example .env"
    echo "    Then fill in your cTrader credentials."
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

echo ""
echo "  → Fetching latest trades from cTrader..."
python fetch_data.py

echo ""
echo "  ▶  Dashboard → http://127.0.0.1:8050"
echo "  Ctrl+C to stop"
echo ""
python app.py
