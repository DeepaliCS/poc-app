#!/bin/bash
# ── save.sh ── saves a snapshot to git + pushes to GitHub ─────
# Usage: ./save.sh "what you changed"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

MSG="${1:-update}"

echo ""
git add .
git commit -m "$MSG"
git push origin main
echo ""
echo "  ✓ Saved and pushed: \"$MSG\""
echo "  ✓ View at: $(git remote get-url origin | sed 's/\.git$//')"
echo ""
