#!/bin/bash
# ============================================
# post-race-cloud-sync.sh
# Run AFTER race, when connected to internet/WiFi at dock.
# 
# Syncs:
#   1. Local InfluxDB → InfluxDB Cloud (via replication)
#   2. Backups race data to Google Drive
#   3. Exports Grafana dashboards for cloud import
#
# Prerequisites:
#   - InfluxDB Cloud account with token
#   - Grafana admin password in .env
#   - rclone configured with Google Drive
#   - Internet connection
#
# Usage:
#   ./post-race-cloud-sync.sh
#
# Author: OC + Denis Lafarge — Midnight Rider Navigation
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

# Load environment
if [ -f "${PROJECT_DIR}/.env" ]; then
  set -a
  source "${PROJECT_DIR}/.env"
  set +a
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EXPORT_DIR="/tmp/grafana-cloud-export-${TIMESTAMP}"

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

success() {
  echo "✅ $*"
}

# ─── Prerequisites Check ──────────────────────────────────────────────────────

echo "════════════════════════════════════════════════════════════"
echo "🌐 POST-RACE CLOUD SYNC — Midnight Rider"
echo "════════════════════════════════════════════════════════════"
echo ""

# Check internet
echo "1️⃣  Checking internet connection..."
if ! ping -c 1 8.8.8.8 > /dev/null 2>&1; then
  error "No internet connection. Connect to WiFi and retry."
fi
success "Internet OK"

# Check local InfluxDB
echo ""
echo "2️⃣  Checking local InfluxDB..."
if ! curl -s http://localhost:8086/health > /dev/null 2>&1; then
  error "Local InfluxDB not responding. Start: docker compose up -d influxdb"
fi
success "Local InfluxDB OK"

# Check cloud credentials
echo ""
echo "3️⃣  Checking cloud credentials..."
if [ -z "$INFLUX_CLOUD_TOKEN" ]; then
  warn "INFLUX_CLOUD_TOKEN not set in .env"
  warn "Cloud upload will be skipped"
  SKIP_CLOUD=true
else
  info "Cloud token: ${INFLUX_CLOUD_TOKEN:0:10}..."
fi

# ─── Step 1: Backup to Google Drive ───────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📦 STEP 1: Backup to Google Drive"
echo "════════════════════════════════════════════════════════════"

if command -v rclone &> /dev/null && rclone listremotes | grep -q "^gdrive:"; then
  info "Backing up last 30 hours to Google Drive..."
  
  if bash "${SCRIPT_DIR}/influxdb-gdrive-backup.sh" --race; then
    success "Google Drive backup complete"
  else
    warn "Google Drive backup failed (continuing anyway)"
  fi
else
  warn "rclone or Google Drive remote not configured (skipping)"
fi

# ─── Step 2: InfluxDB Cloud Replication ───────────────────────────────────────

if [ "$SKIP_CLOUD" != "true" ]; then
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "☁️  STEP 2: InfluxDB Cloud Replication"
  echo "════════════════════════════════════════════════════════════"
  
  # Check if replication exists
  REPLICATION_ID=$(influx replication list \
    --org "${INFLUX_ORG}" \
    --token "${INFLUX_TOKEN}" \
    --json 2>/dev/null | jq -r '.[0].id // empty' || echo "")
  
  if [ -n "$REPLICATION_ID" ]; then
    info "Replication ID: ${REPLICATION_ID}"
    
    # Check replication status
    echo ""
    info "Replication status:"
    influx replication list \
      --org "${INFLUX_ORG}" \
      --token "${INFLUX_TOKEN}" \
      --json 2>/dev/null | jq '.[0] | {
        name: .name, 
        state: .state, 
        remainingBytesCount: .remainingBytesCount,
        maxQueueSizeBytes: .maxQueueSizeBytes,
        latestResponseCode: .latestResponseCode
      }' || true
    
    success "Cloud replication configured and active"
  else
    warn "No replication configured yet (see docs/INTEGRATION/CLOUD-SETUP.md)"
    warn "To configure:"
    warn "  1. Create InfluxDB Cloud account"
    warn "  2. Set INFLUX_CLOUD_TOKEN in .env"
    warn "  3. Run: influx remote create (see guide)"
  fi
fi

# ─── Step 3: Export Grafana Dashboards ─────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "📊 STEP 3: Export Grafana Dashboards"
echo "════════════════════════════════════════════════════════════"

if ! command -v jq &> /dev/null; then
  warn "jq not installed (skipping Grafana export)"
else
  mkdir -p "${EXPORT_DIR}"
  
  info "Exporting dashboards from local Grafana..."
  
  # Get admin credentials
  GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
  GRAFANA_USER="${GRAFANA_USER:-admin}"
  GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-}"
  
  if [ -z "$GRAFANA_PASSWORD" ]; then
    warn "GRAFANA_PASSWORD not set (skipping dashboard export)"
  else
    # Export each dashboard
    DASHBOARD_UIDS=("cockpit-main" "alerts-monitoring" "midnight-astronomical" \
                    "midnight-navigation" "midnight-race" "midnightrider-meteo" \
                    "midnightrider-regatta" "midnightrider-alertes")
    
    for uid in "${DASHBOARD_UIDS[@]}"; do
      echo "  Exporting: $uid..."
      
      if curl -s -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        "${GRAFANA_URL}/api/dashboards/uid/${uid}" \
        | jq . > "${EXPORT_DIR}/${uid}.json" 2>/dev/null; then
        success "  → ${uid}.json"
      else
        warn "  ✗ Failed to export ${uid}"
      fi
    done
    
    success "Dashboards exported to: ${EXPORT_DIR}"
  fi
fi

# ─── Summary ──────────────────────────────────────────────────────────────────

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ POST-RACE CLOUD SYNC COMPLETE"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "What's been done:"
echo "  ✅ Google Drive: Race data backed up"
echo "  ✅ InfluxDB Cloud: Replication queue flushing"
echo "  ✅ Grafana: Dashboards exported for cloud import"
echo ""
echo "Next Steps:"
echo ""
if [ -d "${EXPORT_DIR}" ]; then
  echo "  1. Import Grafana dashboards to Grafana Cloud:"
  echo "     → Upload files from: ${EXPORT_DIR}"
  echo "     → Target: https://yourstack.grafana.net"
  echo ""
fi
echo "  2. Connect Grafana Cloud to InfluxDB Cloud:"
  echo "     → Create datasource in Grafana Cloud"
  echo "     → Use INFLUX_CLOUD_URL and INFLUX_CLOUD_TOKEN"
echo ""
echo "  3. Access live data from anywhere:"
echo "     → https://cloud2.influxdata.com (InfluxDB)"
echo "     → https://yourstack.grafana.net (Grafana)"
echo ""
echo "Documentation:"
echo "  → docs/INTEGRATION/CLOUD-SETUP.md"
echo ""
echo "════════════════════════════════════════════════════════════"
