#!/bin/bash
# ── save.sh ── commit and push to GitHub ──────────────────────
# Usage: bash scripts/save.sh "describe your change"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MSG="${1:-update}"

echo ""
git add .
git commit -m "$MSG"
git push origin main
echo ""
echo "  ✓ Saved and pushed: \"$MSG\""
echo "  ✓ View at: https://github.com/DeepaliCS/poc-app"
echo ""
