#!/bin/bash
# commit-logs.sh — Commits runtime logs to GitHub every 15 min
# Enables Dust (MidnightRider Coordinator) to read live logs via GitHub API
# Called by midnight-logs-commit.timer
#
# SECURITY BARRIER added 2026-09-15 by H3b, incident SEC-2026-09-14-01.
# This script, in its previous form, staged logs/debug/ in bulk with no check
# and published an InfluxDB token in a public repository. It now refuses to
# commit anything that scripts/check-staged-secrets.py flags as a credential.
# The refusal report is written OUTSIDE logs/ on purpose: writing it into
# logs/ would make the next run try to commit the report of the previous
# refusal, secret excerpt included.

set -e
cd /home/aneto/midnightrider-navigation

LOG_PATHS="logs/services/ logs/debug/ logs/latest.json logs/oc-actions.log"
BLOCK_REPORT="/tmp/commit-logs-blocked.log"

git add $LOG_PATHS 2>/dev/null || true

if git diff --cached --quiet; then
 echo "[$( date -Iseconds)] No log changes to commit"
 exit 0
fi

# --- the barrier -------------------------------------------------------------
if ! python3 scripts/check-staged-secrets.py > "$BLOCK_REPORT" 2>&1; then
 echo "[$( date -Iseconds)] BLOCKED by the secret barrier - nothing committed"
 echo "  report: $BLOCK_REPORT"
 git reset --quiet HEAD -- $LOG_PATHS 2>/dev/null || true
 exit 1
fi
cat "$BLOCK_REPORT"
# -----------------------------------------------------------------------------

CHANGED=$(git diff --cached --stat | tail -1)
git commit -m "logs: auto-update — $CHANGED" --no-verify

if git push origin main --no-verify 2>/dev/null; then
 echo "[$( date -Iseconds)] Logs pushed: $CHANGED"
else
 echo "[$( date -Iseconds)] Push failed — undoing commit"
 git reset HEAD~1
fi
