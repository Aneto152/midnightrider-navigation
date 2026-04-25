#!/bin/bash
#
# NOAA Buoy Data Logger — Fetch wind data from LIS buoys
#
# Logs real-time wind measurements from NOAA buoys:
# - NOAA 44065 (Stamford/Western LIS) — 41.063°N, 73.591°W
# - NOAA 44025 (Central LIS) — 40.876°N, 73.100°W  
# - NOAA 44008 (Eastern LIS/Block Island) — 40.502°N, 71.029°W
#
# Updates every 5-10 minutes with actual observations
#
# Usage:
#   ./buoy-logger.sh              # Fetch now
#   ./buoy-logger.sh --daemon     # Run as daemon (5 min intervals)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
INFLUX_URL=${INFLUX_URL:-http://localhost:8086}
INFLUX_TOKEN=${INFLUX_TOKEN:-}
INFLUX_ORG=${INFLUX_ORG:-MidnightRider}
INFLUX_BUCKET=${INFLUX_BUCKET:-signalk}

LOG_FILE="/tmp/buoy-logger.log"

# NOAA Buoys in Long Island Sound
declare -A BUOYS=(
  ["44065"]="Stamford (Western LIS);41.063;-73.591"
  ["44025"]="Central LIS;40.876;-73.100"
  ["44008"]="Block Island (Eastern LIS);40.502;-71.029"
)

# Logging function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Fetch buoy data from NOAA
fetch_buoy() {
  local station=$1
  local url="https://www.ndbc.noaa.gov/data/realtime2/${station}.txt"
  
  curl -s "$url" 2>/dev/null || echo ""
}

# Parse buoy data (fixed format NOAA)
parse_buoy() {
  local data="$1"
  local station="$2"
  
  if [ -z "$data" ]; then
    return 1
  fi
  
  # Skip header lines (start with # or /)
  local content=$(echo "$data" | tail -n +3)
  
  if [ -z "$content" ]; then
    return 1
  fi
  
  # Get first (most recent) data line
  local line=$(echo "$content" | head -1)
  
  # Parse fixed format (whitespace separated)
  # YY MM DD hh mm WDIR WSPD GUST WVHT DPTH WTMP SALINITY DEWP VIS PTDY TIDE
  local arr=($line)
  
  # Check if we have enough fields
  if [ ${#arr[@]} -lt 6 ]; then
    return 1
  fi
  
  local year=${arr[0]}
  local month=${arr[1]}
  local day=${arr[2]}
  local hour=${arr[3]}
  local minute=${arr[4]}
  local wdir=${arr[5]}      # Wind direction (degrees)
  local wspd=${arr[6]}      # Wind speed (m/s)
  local gust=${arr[7]}      # Gust (m/s)
  local wvht=${arr[8]}      # Wave height (m)
  local wtmp=${arr[9]}      # Water temp (°C)
  
  # Convert to InfluxDB format
  # Full year: NOAA uses 2-digit year, assume 20XX
  local full_year="20${year}"
  local timestamp="${full_year}-${month}-${day}T${hour}:${minute}:00Z"
  
  # Convert m/s to knots
  local wspd_knots=$(echo "scale=2; $wspd * 1.94384" | bc 2>/dev/null || echo "$wspd")
  local gust_knots=$(echo "scale=2; $gust * 1.94384" | bc 2>/dev/null || echo "$gust")
  
  echo "$timestamp|$wdir|$wspd_knots|$gust_knots|$wvht|$wtmp"
}

# Send data to InfluxDB
send_to_influxdb() {
  local data="$1"
  
  if [ -z "$INFLUX_TOKEN" ]; then
    log "ERROR: INFLUX_TOKEN not set"
    return 1
  fi

  local response=$(curl -s -w "\n%{http_code}" -X POST \
    "${INFLUX_URL}/api/v2/write?org=${INFLUX_ORG}&bucket=${INFLUX_BUCKET}&precision=ns" \
    -H "Authorization: Token ${INFLUX_TOKEN}" \
    -H "Content-Type: text/plain" \
    -d "$data")
  
  local http_code=$(echo "$response" | tail -1)
  
  if [ "$http_code" = "204" ]; then
    return 0
  else
    log "❌ InfluxDB write failed (HTTP $http_code)"
    return 1
  fi
}

# Main
main() {
  log "========== BUOY LOGGER START =========="
  log "Monitoring ${#BUOYS[@]} NOAA buoys in LIS"
  
  if [ "$1" = "--daemon" ]; then
    log "Running as daemon (5 min intervals)..."
    while true; do
      process_all_buoys
      log "Next update in 5 minutes..."
      sleep 300
    done
  else
    process_all_buoys
  fi
}

process_all_buoys() {
  log "Fetching buoy data..."
  
  local lines=""
  local count=0
  
  for station in "${!BUOYS[@]}"; do
    IFS=';' read -r name lat lon <<< "${BUOYS[$station]}"
    
    # Fetch data
    local raw=$(fetch_buoy "$station")
    
    if [ -n "$raw" ]; then
      # Parse data
      local parsed=$(parse_buoy "$raw" "$station")
      
      if [ -n "$parsed" ]; then
        IFS='|' read -r timestamp wdir wspd gust wvht wtmp <<< "$parsed"
        
        # Check for missing values (NOAA uses 999 or similar)
        [ "$wdir" = "999" ] && wdir=""
        [ "$wspd" = "99.0" ] && wspd=""
        [ "$gust" = "99.0" ] && gust=""
        [ "$wvht" = "99.0" ] && wvht=""
        [ "$wtmp" = "99.0" ] && wtmp=""
        
        if [ -n "$wspd" ]; then
          local ts=$(date -d "$timestamp" +%s%N 2>/dev/null || date +%s%N)
          
          [ -n "$wdir" ] && lines+="buoy.wind_direction,station=${station},location=\"${name}\",lat=${lat},lon=${lon} value=${wdir} ${ts}\n"
          [ -n "$wspd" ] && lines+="buoy.wind_speed_knots,station=${station},location=\"${name}\",lat=${lat},lon=${lon} value=${wspd} ${ts}\n"
          [ -n "$gust" ] && lines+="buoy.wind_gust_knots,station=${station},location=\"${name}\",lat=${lat},lon=${lon} value=${gust} ${ts}\n"
          [ -n "$wvht" ] && lines+="buoy.wave_height,station=${station},location=\"${name}\",lat=${lat},lon=${lon} value=${wvht} ${ts}\n"
          [ -n "$wtmp" ] && lines+="buoy.water_temperature,station=${station},location=\"${name}\",lat=${lat},lon=${lon} value=${wtmp} ${ts}\n"
          
          count=$((count + 1))
          log "✅ $station ($name): ${wspd}kt wind, ${gust}kt gust"
        else
          log "⚠️ $station: No valid wind data"
        fi
      else
        log "⚠️ $station: Failed to parse data"
      fi
    else
      log "⚠️ $station: Failed to fetch data"
    fi
  done
  
  if [ -n "$lines" ]; then
    log "Sending $count buoy measurements to InfluxDB..."
    if send_to_influxdb "$(echo -e "$lines" | sed '$ d')"; then
      log "✅ Data sent"
    fi
  fi
}

main "$@"
