#!/bin/bash
# ── undo.sh ── reverts ALL unsaved changes back to last commit ─
# Use this when new code breaks something and you want to go back.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  This will undo ALL changes since your last save."
read -p "  Are you sure? (y/N): " CONFIRM

if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
    git checkout .
    echo "  ✓ Restored to last saved version"
    echo ""
    git log --oneline -5
    echo ""
else
    echo "  Cancelled."
fi
echo ""
