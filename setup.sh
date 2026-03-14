#!/bin/bash
# ── setup.sh ──────────────────────────────────────────────────
# Run this ONCE to:
#   1. Create the conda environment
#   2. Install Python packages
#   3. Initialise git
#   4. Walk you through pushing to GitHub
# ──────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

ENV_NAME="poc_app"

echo ""
echo "  ╔════════════════════════════════════════╗"
echo "  ║   POC App — First-time Setup           ║"
echo "  ╚════════════════════════════════════════╝"
echo ""

# ── 1. Find conda ─────────────────────────────────────────────
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
    echo "  ✗ Conda not found."
    exit 1
fi
source "$CONDA_SH"
echo "  ✓ Conda found"

# ── 2. Create conda env ───────────────────────────────────────
if ! conda env list | grep -q "^${ENV_NAME} "; then
    echo "  → Creating conda env '${ENV_NAME}'..."
    conda create -y -n "$ENV_NAME" python=3.11 -q
    echo "  ✓ Env created"
else
    echo "  ✓ Conda env '${ENV_NAME}' already exists"
fi

conda activate "$ENV_NAME"

# ── 3. Install packages ───────────────────────────────────────
echo "  → Installing packages..."
pip install -r requirements.txt -q
echo "  ✓ Packages installed"
echo ""

# ── 4. Git setup ──────────────────────────────────────────────
echo "  ── Git setup ──────────────────────────────"
echo ""

if ! command -v git &>/dev/null; then
    echo "  ✗ Git not found. Installing..."
    sudo apt-get install -y git -q
    echo "  ✓ Git installed"
else
    echo "  ✓ Git found: $(git --version)"
fi

# Init repo if not already
if [ ! -d ".git" ]; then
    git init
    echo "  ✓ Git repository initialised"
else
    echo "  ✓ Git repository already exists"
fi

# Set up git identity if not set
GIT_NAME=$(git config --global user.name 2>/dev/null || echo "")
GIT_EMAIL=$(git config --global user.email 2>/dev/null || echo "")

if [ -z "$GIT_NAME" ]; then
    echo ""
    read -p "  Enter your name for git commits: " GIT_NAME
    git config --global user.name "$GIT_NAME"
fi
if [ -z "$GIT_EMAIL" ]; then
    read -p "  Enter your email for git commits: " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
fi
echo "  ✓ Git identity: $GIT_NAME <$GIT_EMAIL>"

# First commit
if [ -z "$(git log --oneline 2>/dev/null)" ]; then
    git add .
    git commit -m "initial commit — POC app v1.0.0"
    echo "  ✓ First commit made"
else
    echo "  ✓ Git history already exists"
fi
echo ""

# ── 5. GitHub setup ───────────────────────────────────────────
echo "  ── GitHub setup ────────────────────────────"
echo ""
echo "  Now let's push this to GitHub so you have a remote backup"
echo "  and can share code with me."
echo ""
echo "  STEP A: Create a new repo on GitHub"
echo "  ─────────────────────────────────────────────"
echo "  1. Open https://github.com/new in your browser"
echo "  2. Repository name: poc-app"
echo "  3. Set to Private (recommended)"
echo "  4. Do NOT tick 'Add README' or any other options"
echo "  5. Click 'Create repository'"
echo ""
read -p "  Press Enter once you've created the repo..."
echo ""
echo "  STEP B: Enter your GitHub details"
echo "  ─────────────────────────────────────────────"
read -p "  Your GitHub username: " GH_USER
echo ""
echo "  STEP C: Connect and push"
echo "  ─────────────────────────────────────────────"

REMOTE_URL="https://github.com/${GH_USER}/poc-app.git"

if git remote get-url origin &>/dev/null; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

echo ""
echo "  → Pushing to GitHub..."
echo "     (Your browser may ask you to log in, or git will"
echo "      prompt for your GitHub username + Personal Access Token)"
echo ""
echo "  If you don't have a token yet:"
echo "  → https://github.com/settings/tokens/new"
echo "     Tick: repo  (full control)"
echo "     Click 'Generate token' and copy it — use it as your password"
echo ""

git branch -M main
git push -u origin main

echo ""
echo "  ══════════════════════════════════════════"
echo "  ✅  All done!"
echo ""
echo "  Your repo: https://github.com/${GH_USER}/poc-app"
echo ""
echo "  To run the app anytime:  ./run.sh"
echo "  To save a version:       ./save.sh 'what you changed'"
echo "  To undo last changes:    ./undo.sh"
echo "  ══════════════════════════════════════════"
echo ""
