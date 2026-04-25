#!/bin/bash
#
# Weather Logger — Fetch weather data and log to InfluxDB
#
# Updates every 5 minutes with:
# - Current conditions (temp, humidity, pressure, wind)
# - Forecast (next 6, 12, 24 hours)
# - Alerts (severe weather)
#
# Usage:
#   ./weather-logger.sh              # Fetch now
#   ./weather-logger.sh --daemon     # Run as daemon (5 min intervals)
#
# Configuration:
#   LAT, LON: Boat coordinates (default: Stamford Harbor, CT)
#   INFLUX_*: InfluxDB settings
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Configuration
LAT=${LAT:-41.0534}
LON=${LON:--73.5387}
INFLUX_URL=${INFLUX_URL:-http://localhost:8086}
INFLUX_TOKEN=${INFLUX_TOKEN:-}
INFLUX_ORG=${INFLUX_ORG:-MidnightRider}
INFLUX_BUCKET=${INFLUX_BUCKET:-signalk}
WEATHER_API=${WEATHER_API:-open-meteo}  # open-meteo or weatherapi

LOG_FILE="/tmp/weather-logger.log"

# Logging function
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Fetch weather from Open-Meteo (free, no API key)
fetch_open_meteo() {
  local url="https://api.open-meteo.com/v1/forecast"
  url+="?latitude=$LAT&longitude=$LON"
  url+="&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl"
  url+="&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m"
  url+="&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code,wind_speed_10m_max,wind_gusts_10m_max"
  url+="&timezone=America/New_York"
  url+="&forecast_days=3"

  curl -s "$url"
}

# Convert weather code to description (WMO codes)
weather_code_to_desc() {
  local code=$1
  case $code in
    0) echo "Clear" ;;
    1|2) echo "Partly cloudy" ;;
    3) echo "Overcast" ;;
    45|48) echo "Foggy" ;;
    51|53|55) echo "Drizzle" ;;
    61|63|65) echo "Rain" ;;
    71|73|75|77) echo "Snow" ;;
    80|81|82) echo "Rain showers" ;;
    85|86) echo "Snow showers" ;;
    95|96|99) echo "Thunderstorm" ;;
    *) echo "Unknown ($code)" ;;
  esac
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
    log "✅ Data sent to InfluxDB"
    return 0
  else
    log "❌ InfluxDB write failed (HTTP $http_code)"
    return 1
  fi
}

# Parse and log weather data
process_weather() {
  local json="$1"
  
  # Extract current conditions
  local temp=$(echo "$json" | grep -o '"temperature_2m":[0-9.-]*' | head -1 | cut -d':' -f2)
  local humidity=$(echo "$json" | grep -o '"relative_humidity_2m":[0-9.-]*' | head -1 | cut -d':' -f2)
  local pressure=$(echo "$json" | grep -o '"pressure_msl":[0-9.-]*' | head -1 | cut -d':' -f2)
  local wind_speed=$(echo "$json" | grep -o '"wind_speed_10m":[0-9.-]*' | head -1 | cut -d':' -f2)
  local wind_dir=$(echo "$json" | grep -o '"wind_direction_10m":[0-9.-]*' | head -1 | cut -d':' -f2)
  local wind_gust=$(echo "$json" | grep -o '"wind_gusts_10m":[0-9.-]*' | head -1 | cut -d':' -f2)
  local weather_code=$(echo "$json" | grep -o '"weather_code":[0-9]*' | head -1 | cut -d':' -f2)
  local precip=$(echo "$json" | grep -o '"precipitation":[0-9.-]*' | head -1 | cut -d':' -f2)

  local TS=$(date +%s%N)
  local lines=""

  # Current conditions
  [ -n "$temp" ] && lines+="weather.temperature,location=stamford,unit=celsius value=${temp} ${TS}\n"
  [ -n "$humidity" ] && lines+="weather.humidity,location=stamford,unit=percent value=${humidity} ${TS}\n"
  [ -n "$pressure" ] && lines+="weather.pressure,location=stamford,unit=hpa value=${pressure} ${TS}\n"
  [ -n "$wind_speed" ] && lines+="weather.wind_speed,location=stamford,unit=kmh value=${wind_speed} ${TS}\n"
  [ -n "$wind_dir" ] && lines+="weather.wind_direction,location=stamford,unit=degrees value=${wind_dir} ${TS}\n"
  [ -n "$wind_gust" ] && lines+="weather.wind_gust,location=stamford,unit=kmh value=${wind_gust} ${TS}\n"
  [ -n "$precip" ] && lines+="weather.precipitation,location=stamford,unit=mm value=${precip} ${TS}\n"
  
  if [ -n "$weather_code" ]; then
    local desc=$(weather_code_to_desc "$weather_code")
    lines+="weather.condition,location=stamford,code=${weather_code} value=\"${desc}\" ${TS}\n"
  fi

  if [ -n "$lines" ]; then
    log "Logged $(echo -e "$lines" | wc -l) weather measurements"
    send_to_influxdb "$(echo -e "$lines" | sed '$ d')"
  fi
}

# Main
main() {
  log "========== WEATHER LOGGER START =========="
  log "Location: ${LAT},${LON}"
  log "API: $WEATHER_API"
  log "Update interval: 5 minutes"
  
  if [ "$1" = "--daemon" ]; then
    # Run as daemon (5 min intervals)
    log "Running as daemon..."
    while true; do
      log "Fetching weather data..."
      
      if [ "$WEATHER_API" = "open-meteo" ]; then
        weather_json=$(fetch_open_meteo)
        process_weather "$weather_json"
      fi
      
      log "Next update in 5 minutes..."
      sleep 300
    done
  else
    # Single run
    log "Fetching weather data..."
    
    if [ "$WEATHER_API" = "open-meteo" ]; then
      weather_json=$(fetch_open_meteo)
      process_weather "$weather_json"
    fi
  fi
}

main "$@"
