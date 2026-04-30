#!/bin/bash
# ============================================
# influxdb-gdrive-backup.sh
# Export InfluxDB bucket → Google Drive via rclone
# 
# Usage: 
#   ./influxdb-gdrive-backup.sh [--full|--race]
#   --full : export all data (pre-race, maintenance)
#   --race : export only last 30 hours (default, post-race)
#
# Prerequisites:
#   - rclone installed & configured with Google Drive remote "gdrive"
#   - influx CLI available
#   - .env with INFLUX_TOKEN, INFLUX_ORG
#
# Author: OC + Denis Lafarge — Midnight Rider Navigation
# ============================================

set -e

MODE="${1:---race}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/tmp/influx_backup_${TIMESTAMP}"
GDRIVE_REMOTE="gdrive"
GDRIVE_PATH="MidnightRider/InfluxDB-backups"

# Load environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

if [ -f "${PROJECT_DIR}/.env" ]; then
  set -a
  source "${PROJECT_DIR}/.env"
  set +a
fi

INFLUX_TOKEN="${INFLUX_TOKEN}"
INFLUX_ORG="${INFLUX_ORG:-MidnightRider}"
INFLUX_BUCKET="${INFLUX_BUCKET:-midnight_rider}"
INFLUX_URL="${INFLUX_URL:-http://localhost:8086}"

# ─── Functions ───────────────────────────────────────────────────────────────

error() {
  echo "❌ ERROR: $*" >&2
  exit 1
}

warn() {
  echo "⚠️  WARNING: $*" >&2
}

info() {
  echo "ℹ️  $*"
}

# ─── Prerequisites Check ──────────────────────────────────────────────────────

echo "════════════════════════════════════════════════════════════"
echo "📦 InfluxDB → Google Drive Backup"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Mode: ${MODE} | Timestamp: ${TIMESTAMP}"
echo ""

# Check rclone
if ! command -v rclone &> /dev/null; then
  error "rclone not installed. Install: curl https://rclone.org/install.sh | sudo bash"
fi
info "rclone: $(rclone version | head -1)"

# Check influx CLI
if ! command -v influx &> /dev/null; then
  error "influx CLI not found"
fi
info "influx CLI: $(influx version | head -1)"

# Check rclone Google Drive remote
if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:"; then
  warn "rclone remote '${GDRIVE_REMOTE}' not configured"
  info "Configure: rclone config"
  info "Then create remote named: ${GDRIVE_REMOTE}"
  exit 1
fi
info "rclone remote: ${GDRIVE_REMOTE}"

# Check local InfluxDB
if ! curl -s "${INFLUX_URL}/health" > /dev/null 2>&1; then
  error "Local InfluxDB not responding at ${INFLUX_URL}"
fi
info "InfluxDB: ${INFLUX_URL}"

# ─── Backup Execution ─────────────────────────────────────────────────────────

echo ""
mkdir -p "${BACKUP_DIR}"

if [ "${MODE}" = "--race" ]; then
  # Export last 30 hours (post-race mode)
  echo "📊 Exporting last 30 hours of race data..."
  
  QUERY='from(bucket:"'"${INFLUX_BUCKET}"'") 
    |> range(start: -30h) 
    |> group(columns: ["_measurement", "_field"]) 
    |> sort()'
  
  if ! influx query \
    --org "${INFLUX_ORG}" \
    --token "${INFLUX_TOKEN}" \
    --format csv \
    "${QUERY}" > "${BACKUP_DIR}/race_data_${TIMESTAMP}.csv" 2>/dev/null; then
    error "Failed to export from InfluxDB"
  fi
  
  EXPORT_FILE="${BACKUP_DIR}/race_data_${TIMESTAMP}.csv"
  
else
  # Full backup (pre-race maintenance)
  echo "💾 Full InfluxDB backup..."
  
  if ! influx backup \
    --org "${INFLUX_ORG}" \
    --token "${INFLUX_TOKEN}" \
    --host "${INFLUX_URL}" \
    --bucket "${INFLUX_BUCKET}" \
    "${BACKUP_DIR}/full_backup" 2>/dev/null; then
    error "Failed to backup InfluxDB"
  fi
  
  EXPORT_FILE="${BACKUP_DIR}/full_backup"
fi

# Verify export
if [ ! -f "${EXPORT_FILE}" ] && [ ! -d "${EXPORT_FILE}" ]; then
  error "Export file/directory not found: ${EXPORT_FILE}"
fi

SIZE=$(du -sh "${EXPORT_FILE}" | cut -f1)
echo "✅ Exported: ${SIZE}"

# ─── Compression ──────────────────────────────────────────────────────────────

echo ""
echo "🗜️  Compressing..."
ARCHIVE_NAME="midnight_rider_${MODE:2}_${TIMESTAMP}.tar.gz"
ARCHIVE="/tmp/${ARCHIVE_NAME}"

if ! tar -czf "${ARCHIVE}" -C /tmp "influx_backup_${TIMESTAMP}"; then
  error "Failed to compress backup"
fi

ARCHIVE_SIZE=$(du -sh "${ARCHIVE}" | cut -f1)
echo "✅ Compressed: ${ARCHIVE_SIZE} → ${ARCHIVE_NAME}"

# ─── Upload to Google Drive ───────────────────────────────────────────────────

echo ""
echo "☁️  Uploading to Google Drive (${GDRIVE_REMOTE}:${GDRIVE_PATH})..."

if rclone copy "${ARCHIVE}" "${GDRIVE_REMOTE}:${GDRIVE_PATH}/" \
  --progress \
  --fast-list \
  2>/dev/null; then
  echo "✅ Upload successful!"
  echo ""
  echo "📍 Remote path: ${GDRIVE_REMOTE}:${GDRIVE_PATH}/${ARCHIVE_NAME}"
  
  # Verify upload
  if rclone ls "${GDRIVE_REMOTE}:${GDRIVE_PATH}/${ARCHIVE_NAME}" > /dev/null 2>&1; then
    echo "✅ Verified on Google Drive"
  else
    warn "Could not verify file on Google Drive"
  fi
else
  error "Upload to Google Drive failed"
fi

# ─── Cleanup ──────────────────────────────────────────────────────────────────

echo ""
echo "🧹 Cleaning up local files..."
rm -rf "${BACKUP_DIR}" "${ARCHIVE}"
echo "✅ Cleanup complete"

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ BACKUP COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "Summary:"
echo "  Mode:         ${MODE}"
echo "  Size:         ${ARCHIVE_SIZE}"
echo "  Destination:  ${GDRIVE_REMOTE}:${GDRIVE_PATH}/"
echo "  Filename:     ${ARCHIVE_NAME}"
echo "  Timestamp:    ${TIMESTAMP}"
echo ""
echo "Access on Google Drive:"
echo "  https://drive.google.com (search: ${ARCHIVE_NAME})"
echo ""
echo "════════════════════════════════════════════════════════════"
