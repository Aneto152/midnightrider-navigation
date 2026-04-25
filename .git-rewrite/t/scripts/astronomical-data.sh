#!/bin/bash
#
# Astronomical Data to InfluxDB
# Updates sun/moon/tide data once per day
#
# Usage: ./astronomical-data.sh
# Or: crontab -e
#   0 0 * * * /home/aneto/docker/signalk/scripts/astronomical-data.sh >> /tmp/astronomical-data.log 2>&1
#

set -e

# Configuration
INFLUX_URL="http://localhost:8086"
INFLUX_TOKEN="REDACTED_TOKEN_REMOVED"
INFLUX_ORG="MidnightRider"
INFLUX_BUCKET="signalk"

# Default coordinates (Stamford Harbor, CT - Long Island Sound)
LAT=${LAT:-41.0534}
LON=${LON:--73.5387}

# NOAA tides station (Stamford Harbor, CT)
NOAA_STATION=${NOAA_STATION:-8467150}
NOAA_API="https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

echo "[$(date)] Starting astronomical data update..."

# Ensure we're in the script directory for node_modules
cd "$(dirname "$0")"

# Create node script inline
ASTRO_SCRIPT=$(cat << 'NEOF'
const SunCalc = require('./node_modules/suncalc');

const lat = parseFloat(process.env.LAT || 41.0534);
const lon = parseFloat(process.env.LON || -73.5387);
const now = new Date();

try {
  const sunTimes = SunCalc.getTimes(now, lat, lon);
  const moonTimes = SunCalc.getMoonTimes(now, lat, lon);
  const moonIll = SunCalc.getMoonIllumination(now);

  // Function to get moon phase name
  function getMoonPhase(phase) {
    const p = (phase / (2 * Math.PI)) * 100;
    if (p < 6.25) return 'new_moon';
    if (p < 18.75) return 'waxing_crescent';
    if (p < 31.25) return 'first_quarter';
    if (p < 43.75) return 'waxing_gibbous';
    if (p < 56.25) return 'full_moon';
    if (p < 68.75) return 'waning_gibbous';
    if (p < 81.25) return 'last_quarter';
    if (p < 93.75) return 'waning_crescent';
    return 'new_moon';
  }

  const result = {
    sunriseTime: sunTimes.sunrise?.toISOString() || null,
    sunsetTime: sunTimes.sunset?.toISOString() || null,
    moonriseTime: moonTimes.rise?.toISOString() || null,
    moonsetTime: moonTimes.set?.toISOString() || null,
    moonIllumination: moonIll.fraction,
    moonPhase: getMoonPhase(moonIll.phase)
  };

  console.log(JSON.stringify(result));
} catch (err) {
  console.error('ERROR calculating astro data:', err.message);
  process.exit(1);
}
NEOF
)

# Calculate sun/moon data
echo "[$(date)] Calculating sun/moon data..."
ASTRO=$(node -e "$ASTRO_SCRIPT" 2>&1) || {
  echo "ERROR: Failed to calculate astro data: $ASTRO"
  exit 1
}
echo "[$(date)] Astro data: $ASTRO"

# Fetch tides
echo "[$(date)] Fetching tides from NOAA..."
BEGIN_DATE=$(date +%Y%m%d)
# Use compatible date syntax (works on both GNU and BusyBox)
END_DATE=$(date -v+1d +%Y%m%d 2>/dev/null || date -d "+1 day" +%Y%m%d 2>/dev/null || date +%Y%m%d)

TIDES_JSON=$(curl -s "${NOAA_API}?station=${NOAA_STATION}&begin_date=${BEGIN_DATE}&end_date=${END_DATE}&product=predictions&datum=MLLW&time_zone=lst_ldt&units=metric&format=json")

# Parse tides
TIDE_SCRIPT=$(cat << 'NEOF'
const data = JSON.parse(process.argv[1]);

if (!data.predictions || data.predictions.length === 0) {
  console.log(JSON.stringify({}));
  process.exit(0);
}

const highs = data.predictions.filter(p => p.type === 'H');
const lows = data.predictions.filter(p => p.type === 'L');

const result = {};
if (highs.length > 0) {
  result.tideHighTime = highs[0].t;
  result.tideHighLevel = parseFloat(highs[0].v);
}
if (lows.length > 0) {
  result.tideLowTime = lows[0].t;
  result.tideLowLevel = parseFloat(lows[0].v);
}

console.log(JSON.stringify(result));
NEOF
)

TIDES=$(node -e "$TIDE_SCRIPT" "$TIDES_JSON" 2>&1) || TIDES="{}"
echo "[$(date)] Tides data: $TIDES"

# Build InfluxDB line protocol
TS=$(date +%s%N)
LINES=""

# Parse JSON and build line protocol
echo "[$(date)] Building line protocol..."

# Sun times
SUNRISE=$(echo "$ASTRO" | grep -o '"sunriseTime":"[^"]*"' | head -1 | cut -d'"' -f4)
SUNSET=$(echo "$ASTRO" | grep -o '"sunsetTime":"[^"]*"' | head -1 | cut -d'"' -f4)

[ -n "$SUNRISE" ] && [ "$SUNRISE" != "null" ] && LINES+="environment.sun.sunriseTime,source=astronomical value=\"${SUNRISE}\" ${TS}"$'\n'
[ -n "$SUNSET" ] && [ "$SUNSET" != "null" ] && LINES+="environment.sun.sunsetTime,source=astronomical value=\"${SUNSET}\" ${TS}"$'\n'

# Moon times
MOONRISE=$(echo "$ASTRO" | grep -o '"moonriseTime":"[^"]*"' | head -1 | cut -d'"' -f4)
MOONSET=$(echo "$ASTRO" | grep -o '"moonsetTime":"[^"]*"' | head -1 | cut -d'"' -f4)
MOONILL=$(echo "$ASTRO" | grep -o '"moonIllumination":[0-9.]*' | head -1 | cut -d':' -f2)
MOONPHASE=$(echo "$ASTRO" | grep -o '"moonPhase":"[^"]*"' | head -1 | cut -d'"' -f4)

[ -n "$MOONRISE" ] && [ "$MOONRISE" != "null" ] && LINES+="environment.moon.moonriseTime,source=astronomical value=\"${MOONRISE}\" ${TS}"$'\n'
[ -n "$MOONSET" ] && [ "$MOONSET" != "null" ] && LINES+="environment.moon.moonsetTime,source=astronomical value=\"${MOONSET}\" ${TS}"$'\n'
[ -n "$MOONILL" ] && LINES+="environment.moon.illumination,source=astronomical value=${MOONILL} ${TS}"$'\n'
[ -n "$MOONPHASE" ] && LINES+="environment.moon.phase,source=astronomical value=\"${MOONPHASE}\" ${TS}"$'\n'

# Tides
TIDEHTIME=$(echo "$TIDES" | grep -o '"tideHighTime":"[^"]*"' | cut -d'"' -f4)
TIDEHLEVEL=$(echo "$TIDES" | grep -o '"tideHighLevel":[0-9.]*' | cut -d':' -f2)
TIDELTIME=$(echo "$TIDES" | grep -o '"tideLowTime":"[^"]*"' | cut -d'"' -f4)
TIDELLEVEL=$(echo "$TIDES" | grep -o '"tideLowLevel":[0-9.]*' | cut -d':' -f2)

[ -n "$TIDEHTIME" ] && LINES+="environment.tide.tideHighTime,source=astronomical value=\"${TIDEHTIME}\" ${TS}"$'\n'
[ -n "$TIDEHLEVEL" ] && LINES+="environment.tide.tideHighLevel,source=astronomical value=${TIDEHLEVEL} ${TS}"$'\n'
[ -n "$TIDELTIME" ] && LINES+="environment.tide.tideLowTime,source=astronomical value=\"${TIDELTIME}\" ${TS}"$'\n'
[ -n "$TIDELLEVEL" ] && LINES+="environment.tide.tideLowLevel,source=astronomical value=${TIDELLEVEL} ${TS}"$'\n'

# Send to InfluxDB
if [ -n "$LINES" ]; then
  echo "[$(date)] Sending data to InfluxDB ($(echo -e "$LINES" | wc -l) lines)..."
  
  RESPONSE=$(curl -s -X POST \
    "${INFLUX_URL}/api/v2/write?org=${INFLUX_ORG}&bucket=${INFLUX_BUCKET}&precision=ns" \
    -H "Authorization: Token ${INFLUX_TOKEN}" \
    -H "Content-Type: text/plain" \
    -d "$(echo -e "$LINES" | sed '$ d')" \
    -w "\n%{http_code}")
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  
  if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "[$(date)] ✅ Data sent successfully (HTTP $HTTP_CODE)"
  else
    echo "[$(date)] ❌ Failed to send data (HTTP $HTTP_CODE)"
    echo "Response: $RESPONSE"
    exit 1
  fi
else
  echo "[$(date)] ⚠️ No data to send"
fi

echo "[$(date)] Done!"
