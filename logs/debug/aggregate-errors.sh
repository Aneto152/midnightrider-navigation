#!/bin/bash
# Midnight Rider — Aggregate errors from all service logs
REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
echo "=== ERROR SUMMARY — $(date -Iseconds) ===" > "$REPO_DIR/logs/debug/error-summary.log"
for logfile in "$REPO_DIR/logs/services/"*.log; do
    [ -f "$logfile" ] || continue
    service=$(basename "$logfile" .log)
    count=$(grep -c "\[ERROR\]" "$logfile" 2>/dev/null || echo 0)
    last_error=$(grep "\[ERROR\]" "$logfile" 2>/dev/null | tail -1)
    echo "[$service] Errors: $count | Last: ${last_error:-none}" >> "$REPO_DIR/logs/debug/error-summary.log"
done
cat "$REPO_DIR/logs/debug/error-summary.log"
