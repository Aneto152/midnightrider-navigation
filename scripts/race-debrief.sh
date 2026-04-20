#!/bin/bash
#
# Race Debrief — Upload race data to cloud
#
# After returning to dock with WiFi, run this to upload today's race
#
# Usage:
#   ./race-debrief.sh                    # Upload last 4 hours
#   ./race-debrief.sh 14:00 18:00        # Upload specific time range (HH:MM)
#   ./race-debrief.sh 2026-04-20T14:00   # Upload specific ISO timestamp
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RACES_DIR="$SCRIPT_DIR/../races"
mkdir -p "$RACES_DIR"

# Load environment
if [ -f "$SCRIPT_DIR/../.env" ]; then
  set -a
  source "$SCRIPT_DIR/../.env"
  set +a
fi

# Parse arguments
if [ -n "$1" ] && [ -n "$2" ]; then
  # Specific time range
  START_DATE=$(date +%Y-%m-%d)
  START_TIME="$1"
  END_TIME="$2"
  START_ISO="${START_DATE}T${START_TIME}:00Z"
  END_ISO="${START_DATE}T${END_TIME}:00Z"
elif [ -n "$1" ]; then
  # ISO timestamp
  START_ISO="$1"
  END_ISO=$(date +%Y-%m-%dT%H:%M:%SZ)
else
  # Default: last 4 hours
  START_ISO=$(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%SZ)
  END_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fi

# Generate race filename
RACE_NAME="race-$(date +%Y-%m-%d-%H%M%S)"
EXPORT_FILE="/tmp/$RACE_NAME.csv"
ARCHIVE_FILE="$RACES_DIR/$RACE_NAME.csv"

echo "🏁 Race Debrief — Export & Upload"
echo ""
echo "Time range: $START_ISO → $END_ISO"
echo "Race name:  $RACE_NAME"
echo ""

# 1. Check local InfluxDB
echo "1️⃣  Checking local InfluxDB..."
if ! curl -s http://localhost:8086/health > /dev/null 2>&1; then
  echo "❌ Local InfluxDB not responding!"
  echo "   Start: docker compose up -d influxdb"
  exit 1
fi
echo "   ✅ Local InfluxDB ready"

# 2. Export from local
echo ""
echo "2️⃣  Exporting race data from local..."
QUERY='from(bucket:"'"$INFLUX_BUCKET"'")
  |> range(start: '"$START_ISO"', stop: '"$END_ISO"')'

if ! influx query \
  --org "$INFLUX_ORG" \
  "$QUERY" > "$EXPORT_FILE" 2>/dev/null; then
  echo "❌ Failed to export from local InfluxDB"
  exit 1
fi

LINE_COUNT=$(wc -l < "$EXPORT_FILE")
echo "   ✅ Exported: $LINE_COUNT lines"

# 3. Check file size
SIZE=$(du -h "$EXPORT_FILE" | cut -f1)
echo "   📊 File size: $SIZE"

# 4. Archive locally
echo ""
echo "3️⃣  Archiving locally..."
cp "$EXPORT_FILE" "$ARCHIVE_FILE"
echo "   ✅ Saved: $ARCHIVE_FILE"

# 5. Check cloud token
echo ""
echo "4️⃣  Checking cloud configuration..."
if [ -z "$INFLUX_CLOUD_TOKEN" ]; then
  echo "   ⚠️  Cloud token not set"
  echo "   💡 To enable cloud upload:"
  echo "      1. Edit .env"
  echo "      2. Add INFLUX_CLOUD_TOKEN=<your-token>"
  echo "      3. Re-run: ./race-debrief.sh"
  echo ""
  echo "   ✅ Race archived locally: $ARCHIVE_FILE"
  exit 0
fi

# 6. Upload to cloud
echo "   ✅ Cloud token found"
echo ""
echo "5️⃣  Uploading to cloud InfluxDB..."

if ! influx write \
  --url "$INFLUX_CLOUD_URL" \
  --token "$INFLUX_CLOUD_TOKEN" \
  --org "$INFLUX_CLOUD_ORG" \
  --bucket "$INFLUX_CLOUD_BUCKET" \
  "$EXPORT_FILE" 2>/dev/null; then
  echo "   ❌ Failed to upload to cloud"
  echo "   💡 Check:"
  echo "      - Internet connection"
  echo "      - Cloud token validity"
  echo "      - Cloud URL and bucket"
  exit 1
fi
echo "   ✅ Uploaded to cloud!"

# 7. Commit to git
echo ""
echo "6️⃣  Committing to git..."
cd "$RACES_DIR"

if [ -d ".git" ]; then
  git add "$RACE_NAME.csv"
  git commit -m "Race debrief: $RACE_NAME" || true
  echo "   ✅ Committed to git"
else
  git init
  git add "$RACE_NAME.csv"
  git commit -m "Race debrief: $RACE_NAME"
  echo "   ✅ Initialized git repo and committed"
fi

# 8. Summary
echo ""
echo "════════════════════════════════════════"
echo "🏁 RACE DEBRIEF COMPLETE! 🏁"
echo "════════════════════════════════════════"
echo ""
echo "Race Data:"
echo "  Local:  $ARCHIVE_FILE"
echo "  Cloud:  $INFLUX_CLOUD_BUCKET bucket"
echo "  Git:    races/$RACE_NAME.csv"
echo ""
echo "Time Range: $START_ISO → $END_ISO"
echo "Data Points: $LINE_COUNT"
echo "File Size:   $SIZE"
echo ""
echo "Next Steps:"
echo "  1. Open Cloud Grafana for analysis:"
echo "     https://cloud2.influxdata.com/orgs/$INFLUX_CLOUD_ORG"
echo ""
echo "  2. Create dashboard with:"
echo "     - Heading timeline (4h)"
echo "     - Speed profile"
echo "     - Wind evolution"
echo "     - Tactic markers"
echo ""
echo "  3. Export race report:"
echo "     - PDF for crew debrief"
echo "     - PNG for social media"
echo ""
echo "════════════════════════════════════════"
