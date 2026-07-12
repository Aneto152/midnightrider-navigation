#!/bin/bash
# sync-plugins.sh — Sync repo plugins to Signal K system directory
# Run after any modification to plugins/signalk-*.js
# Usage: sudo bash scripts/sync-plugins.sh

set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)/plugins"
SYS_BASE="/usr/lib/node_modules/signalk-server/node_modules"

echo "=== Plugin Sync: repo → /usr/lib ==="
for repo_file in "$REPO_DIR"/signalk-*.js; do
    plugin_name="$(basename "$repo_file" .js)"
    # Find system destination
    sys_file=$(find "$SYS_BASE/${plugin_name}" -name "${plugin_name}.js" 2>/dev/null | head -1)
    if [ -z "$sys_file" ]; then
        sys_file=$(find "$SYS_BASE/${plugin_name}" -name "index.js" 2>/dev/null | head -1)
    fi
    if [ -z "$sys_file" ]; then
        echo "⚠️ ${plugin_name}: system path not found — skipping"
        continue
    fi
    cp "$repo_file" "$sys_file"
    echo "✅ ${plugin_name} → ${sys_file}"
done
echo ""
echo "Restart Signal K to apply:"
echo " sudo systemctl restart signalk"
