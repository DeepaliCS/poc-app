#!/bin/bash
# ── history.sh ── shows all saved versions ────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ── Saved versions ──────────────────────────"
echo ""
git log --oneline --decorate
echo ""
echo "  To jump to a specific version:"
echo "  git checkout <ID>     e.g. git checkout a3f92c1"
echo ""
echo "  To come back to latest:"
echo "  git checkout main"
echo ""
