#!/bin/bash
# commit-logs.sh — Commits runtime logs to GitHub every 15 min
# Enables Dust (MidnightRider Coordinator) to read live logs via GitHub API
# Called by midnight-logs-commit.timer

set -e
cd /home/aneto/midnightrider-navigation

git add logs/services/ logs/debug/ logs/latest.json logs/oc-actions.log 2>/dev/null || true

if git diff --cached --quiet; then
 echo "[$( date -Iseconds)] No log changes to commit"
 exit 0
fi

CHANGED=$(git diff --cached --stat | tail -1)
git commit -m "logs: auto-update — $CHANGED" --no-verify

if git push origin main --no-verify 2>/dev/null; then
 echo "[$( date -Iseconds)] Logs pushed: $CHANGED"
else
 echo "[$( date -Iseconds)] Push failed — undoing commit"
 git reset HEAD~1
fi
