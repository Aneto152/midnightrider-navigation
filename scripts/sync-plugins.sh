#!/bin/bash
# sync-plugins.sh — Sync repo plugins to Signal K system directory
# USAGE: sudo bash scripts/sync-plugins.sh
# Run after any modification to plugins/signalk-*.js
# Then: sudo systemctl restart signalk
#
# SSOT RULE: Always edit files in plugins/ (repo), never in /usr/lib directly.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)/plugins"
SYS_BASE="/usr/lib/node_modules/signalk-server/node_modules"

echo "=== MidnightRider Plugin Sync: repo → system ==="
echo "Source : $REPO_DIR"
echo "Target : $SYS_BASE"
echo ""

SYNCED=0
SKIPPED=0
ERRORS=0

for repo_file in "$REPO_DIR"/signalk-*.js; do
    [ -f "$repo_file" ] || continue
    plugin_name="$(basename "$repo_file" .js)"

    # Try to find the system destination file
    sys_file=""
    for candidate in \
        "$SYS_BASE/${plugin_name}/${plugin_name}.js" \
        "$SYS_BASE/${plugin_name}/index.js"
    do
        if [ -f "$candidate" ]; then
            sys_file="$candidate"
            break
        fi
    done

    if [ -z "$sys_file" ]; then
        echo "⚠️ ${plugin_name}: system path not found — skipping"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Get versions for display
    repo_ver=$(grep -oP "@version\s+\K[\d.]+" "$repo_file" 2>/dev/null || echo "?")
    sys_ver=$(grep -oP "@version\s+\K[\d.]+" "$sys_file" 2>/dev/null || echo "?")

    cp "$repo_file" "$sys_file"
    echo "✅ ${plugin_name}: v${sys_ver} → v${repo_ver}"
    echo " ${sys_file}"
    SYNCED=$((SYNCED + 1))
done

echo ""
echo "=== Summary ==="
echo " Synced : $SYNCED"
echo " Skipped : $SKIPPED"
echo " Errors : $ERRORS"
echo ""
echo "Next step: sudo systemctl restart signalk"
