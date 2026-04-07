#!/bin/bash
cd /home/aneto/docker/signalk
git add -A
git diff --cached --quiet || git commit -m "Auto-backup $(date '+%Y-%m-%d %H:%M')"
git push origin main
