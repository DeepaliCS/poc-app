#!/bin/bash
# ── undo.sh ── revert all uncommitted changes ─────────────────
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ""
echo "  ⚠  This will undo ALL changes since your last save."
read -p "  Are you sure? (y/N): " CONFIRM

if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    git checkout .
    echo "  ✓ Restored to last saved version"
    echo ""
    git log --oneline -5
else
    echo "  Cancelled — no changes made."
fi
echo ""
