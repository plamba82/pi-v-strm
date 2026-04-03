#!/usr/bin/env bash
# prints candidate Chrome for Testing binary paths under $HOME/Library/Caches
set -e
echo "Searching common cache dirs..."
find "$HOME/Library/Caches" -type f -name "Google Chrome for Testing" -print 2>/dev/null || true
# also try ms-playwright cache
echo "Playwright cache path (if installed):"
ls -d "$HOME/Library/Caches/ms-playwright" 2>/dev/null || true