#!/bin/bash
# ── history.sh ── show all saved versions ─────────────────────
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "  ── Saved versions ──────────────────────────────────────"
echo ""
git log --oneline --decorate
echo ""
echo "  To jump to a version:  git checkout <ID>"
echo "  To return to latest:   git checkout main"
echo ""
